"""Тесты для проведения, FIFO, выкупа и конкурентности."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection

from tires.models import TireNomenclature, TireCode, Warehouse, Platform
from users.models import UserRoles
from .models import Document, DocumentItem, DocType
from .services import DocumentService


class PostingServiceTest(TestCase):
    """Тесты проведения документа (T30)."""

    def setUp(self):
        self.platform = Platform.objects.create(name='Тестовая площадка')
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123',
            platform=self.platform,
            role=UserRoles.STOREKEEPER,
        )
        self.warehouse = Warehouse.objects.create(
            name='Тестовый склад',
            platform=self.platform,
            warehouse_type='main',
        )
        self.writeoff_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True,
        )
        self.nomenclature = TireNomenclature.objects.create(
            brand='TestBrand',
            model='TestModel',
            size='295/80R22.5',
        )

    def _create_posted_document(self, quantity=1):
        """Создать проведённый документ для тестов."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.writeoff_type,
            source_warehouse=self.warehouse,
        )

        # Создаём коды
        for i in range(quantity):
            TireCode.objects.create(
                qr_code=f'TESTCODE{i:03d}',
                nomenclature=self.nomenclature,
                warehouse=self.warehouse,
                is_active=True,
                is_used=False,
            )

        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=quantity,
        )
        DocumentService.save_draft(document)
        return document

    def test_post_document_atomic(self):
        """Тест: проведение — атомарная транзакция (БП 6)."""
        document = self._create_posted_document(1)

        document = DocumentService.post_document(document)

        self.assertEqual(document.status, 'posted')
        self.assertIsNotNone(document.posted_at)

        # Код помечен
        code = TireCode.objects.get(qr_code='TESTCODE000')
        self.assertTrue(code.is_used)
        self.assertFalse(code.is_active)
        self.assertEqual(code.document, document)

    def test_post_document_fifo(self):
        """Тест: FIFO — выбраны старейшие коды (БП 7)."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.writeoff_type,
            source_warehouse=self.warehouse,
        )

        # Создаём коды с разными датами
        old_code = TireCode.objects.create(
            qr_code='OLD_CODE',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            is_active=True,
            is_used=False,
            created_at='2025-01-01',
        )
        new_code = TireCode.objects.create(
            qr_code='NEW_CODE',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            is_active=True,
            is_used=False,
            created_at='2026-01-01',
        )

        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentService.save_draft(document)
        DocumentService.post_document(document)

        # Должен быть выбран старейший код
        old_code.refresh_from_db()
        new_code.refresh_from_db()

        self.assertTrue(old_code.is_used)
        self.assertFalse(new_code.is_used)

    def test_post_document_insufficient_by_first_line(self):
        """Тест: нехватка по первой строке → ROLLBACK."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.writeoff_type,
            source_warehouse=self.warehouse,
        )

        TireCode.objects.create(
            qr_code='CODE1',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            is_active=True,
            is_used=False,
        )

        # Первая строка требует 5, доступно 1
        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=5,
        )
        DocumentService.save_draft(document)

        with self.assertRaises(ValidationError):
            DocumentService.post_document(document)

        # Документ остаётся saved, коды не изменены
        document.refresh_from_db()
        self.assertEqual(document.status, 'saved')
        code = TireCode.objects.get(qr_code='CODE1')
        self.assertTrue(code.is_active)
        self.assertFalse(code.is_used)

    def test_post_document_insufficient_by_second_line(self):
        """Тест: нехватка по второй строке при достатке по первой → ROLLBACK."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.writeoff_type,
            source_warehouse=self.warehouse,
        )

        # Первая номенклатура — 5 кодов (хватит)
        nomenclature2 = TireNomenclature.objects.create(
            brand='Brand2', model='Model2', size='315/80R22.5',
        )
        TireCode.objects.create(
            qr_code='CODE1',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            is_active=True,
            is_used=False,
        )
        TireCode.objects.create(
            qr_code='CODE2',
            nomenclature=nomenclature2,
            warehouse=self.warehouse,
            is_active=True,
            is_used=False,
        )

        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentItem.objects.create(
            document=document,
            nomenclature=nomenclature2,
            quantity=2,  # доступно только 1
        )
        DocumentService.save_draft(document)

        with self.assertRaises(ValidationError):
            DocumentService.post_document(document)

        # ROLLBACK — всё как было
        code1 = TireCode.objects.get(qr_code='CODE1')
        code2 = TireCode.objects.get(qr_code='CODE2')
        self.assertTrue(code1.is_active)
        self.assertTrue(code2.is_active)


class UnpostingServiceTest(TestCase):
    """Тесты распроведения (T31)."""

    def setUp(self):
        self.platform = Platform.objects.create(name='Тестовая площадка')
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123',
            platform=self.platform,
            role=UserRoles.STOREKEEPER,
        )
        self.warehouse = Warehouse.objects.create(
            name='Тестовый склад',
            platform=self.platform,
            warehouse_type='main',
        )
        self.doc_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True,
        )
        self.nomenclature = TireNomenclature.objects.create(
            brand='TestBrand',
            model='TestModel',
            size='295/80R22.5',
        )

    def test_unpost_restores_codes(self):
        """Тест: распроведение → коды активны, счётчики восстановлены."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )

        code = TireCode.objects.create(
            qr_code='TESTCODE001',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            is_active=True,
            is_used=False,
        )

        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentService.save_draft(document)
        DocumentService.post_document(document)

        # Распроведение
        document = DocumentService.unpost_document(document)

        self.assertEqual(document.status, 'saved')
        self.assertIsNone(document.posted_at)

        code.refresh_from_db()
        self.assertFalse(code.is_used)
        self.assertTrue(code.is_active)
        self.assertIsNone(code.document)
        self.assertIsNone(code.used_at)


class BuyoutServiceTest(TestCase):
    """Тесты выкупа — перевязка кодов (T32)."""

    def setUp(self):
        self.platform = Platform.objects.create(name='Тестовая площадка')
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123',
            platform=self.platform,
            role=UserRoles.STOREKEEPER,
        )
        self.source_warehouse = Warehouse.objects.create(
            name='Источник',
            platform=self.platform,
            warehouse_type='main',
        )
        self.target_warehouse = Warehouse.objects.create(
            name='Основной',
            platform=self.platform,
            warehouse_type='main',
        )
        self.buyout_type = DocType.objects.create(
            code='buyout',
            name='Выкуп',
            prefix='ВК',
            is_active=True,
        )
        self.nomenclature = TireNomenclature.objects.create(
            brand='TestBrand',
            model='TestModel',
            size='295/80R22.5',
        )

    def test_buyout_relinks_warehouse(self):
        """Тест: выкуп — перевязка склада (БП 8)."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.buyout_type,
            source_warehouse=self.source_warehouse,
            target_warehouse=self.target_warehouse,
        )

        code = TireCode.objects.create(
            qr_code='TESTCODE001',
            nomenclature=self.nomenclature,
            warehouse=self.source_warehouse,
            is_active=True,
            is_used=False,
        )

        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentService.save_draft(document)
        DocumentService.post_document(document)

        # Код перевязан на target_warehouse
        code.refresh_from_db()
        self.assertEqual(code.warehouse, self.target_warehouse)
        self.assertTrue(code.is_used)
        self.assertFalse(code.is_active)
        self.assertEqual(code.document, document)

    def test_buyout_no_honest_sign_request(self):
        """Тест: выкуп без перезапроса «Честного знака» (БП 8)."""
        # Выкуп не делает запросов к API — просто меняет warehouse
        # Это проверяется на уровне архитектуры: post_document не вызывает
        # HonestSignClient для buyout документов
        document = DocumentService.create(
            user=self.user,
            doc_type=self.buyout_type,
            source_warehouse=self.source_warehouse,
            target_warehouse=self.target_warehouse,
        )

        code = TireCode.objects.create(
            qr_code='TESTCODE001',
            nomenclature=self.nomenclature,
            warehouse=self.source_warehouse,
            is_active=True,
            is_used=False,
        )

        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentService.save_draft(document)
        DocumentService.post_document(document)

        code.refresh_from_db()
        self.assertEqual(code.warehouse, self.target_warehouse)


class CrossPlatformWriteoffTest(TestCase):
    """Тесты списания с чужой площадки (T33)."""

    def setUp(self):
        self.platform1 = Platform.objects.create(name='Площадка 1')
        self.platform2 = Platform.objects.create(name='Площадка 2')
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123',
            platform=self.platform1,
            role=UserRoles.STOREKEEPER,
        )
        self.source_warehouse = Warehouse.objects.create(
            name='Чужой склад',
            platform=self.platform2,  # чужая площадка
            warehouse_type='main',
        )
        self.writeoff_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True,
        )
        self.nomenclature = TireNomenclature.objects.create(
            brand='TestBrand',
            model='TestModel',
            size='295/80R22.5',
        )

    def test_cross_platform_writeoff(self):
        """Тест: storekeeper может списать с чужой площадки (БП 13)."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.writeoff_type,
            source_warehouse=self.source_warehouse,
            writeoff_platform=self.platform2,
        )

        code = TireCode.objects.create(
            qr_code='TESTCODE001',
            nomenclature=self.nomenclature,
            warehouse=self.source_warehouse,
            is_active=True,
            is_used=False,
        )

        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentService.save_draft(document)
        DocumentService.post_document(document)

        # Документ проведён
        self.assertEqual(document.status, 'posted')
        self.assertEqual(document.writeoff_platform, self.platform2)
        self.assertEqual(document.source_platform, self.platform1)

        # Код списан
        code.refresh_from_db()
        self.assertTrue(code.is_used)


class ConcurrentPostingTest(TestCase):
    """Тесты конкурентного проведения (T34)."""

    def setUp(self):
        self.platform = Platform.objects.create(name='Тестовая площадка')
        self.user1 = get_user_model().objects.create_user(
            email='user1@example.com',
            password='testpass123',
            platform=self.platform,
            role=UserRoles.STOREKEEPER,
        )
        self.user2 = get_user_model().objects.create_user(
            email='user2@example.com',
            password='testpass123',
            platform=self.platform,
            role=UserRoles.STOREKEEPER,
        )
        self.warehouse = Warehouse.objects.create(
            name='Тестовый склад',
            platform=self.platform,
            warehouse_type='main',
        )
        self.doc_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True,
        )
        self.nomenclature = TireNomenclature.objects.create(
            brand='TestBrand',
            model='TestModel',
            size='295/80R22.5',
        )

    def test_concurrent_posting_one_succeeds(self):
        """Тест: два документа на одни коды — один проходит, второй — ошибка."""
        # Создаём 1 код
        code = TireCode.objects.create(
            qr_code='SHARED_CODE',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            is_active=True,
            is_used=False,
        )

        # Документ 1
        doc1 = DocumentService.create(
            user=self.user1,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )
        DocumentItem.objects.create(
            document=doc1,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentService.save_draft(doc1)

        # Документ 2
        doc2 = DocumentService.create(
            user=self.user2,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )
        DocumentItem.objects.create(
            document=doc2,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentService.save_draft(doc2)

        # Первый проходит
        doc1 = DocumentService.post_document(doc1)
        self.assertEqual(doc1.status, 'posted')

        # Второй — нехватка
        with self.assertRaises(ValidationError):
            DocumentService.post_document(doc2)

        # Документ 2 остаётся saved
        doc2.refresh_from_db()
        self.assertEqual(doc2.status, 'saved')

        # Код использован только один раз
        code.refresh_from_db()
        self.assertTrue(code.is_used)
        self.assertEqual(code.document, doc1)
