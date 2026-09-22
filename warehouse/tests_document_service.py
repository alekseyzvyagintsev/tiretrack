"""Тесты для DocumentService."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from tires.models import TireNomenclature, TireCode, Warehouse, Platform, Supplier
from users.models import UserRoles
from .models import Document, DocumentItem, DocType
from .services import DocumentService


class DocumentServiceTest(TestCase):
    """Тесты для DocumentService."""

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

    def test_create_document(self):
        """Тест создания документа."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )

        self.assertEqual(document.status, 'draft')
        self.assertEqual(document.author, self.user)
        self.assertEqual(document.source_platform, self.platform)
        self.assertEqual(document.source_warehouse, self.warehouse)
        self.assertIsNone(document.number)

    def test_save_draft(self):
        """Тест сохранения черновика."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )

        # Добавляем строку
        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=1,
        )

        # Сохраняем
        document = DocumentService.save_draft(document)

        self.assertEqual(document.status, 'saved')
        self.assertIsNotNone(document.number)
        self.assertTrue(document.number.startswith('СП-'))

    def test_save_draft_empty_document(self):
        """Тест сохранения пустого черновика — ошибка."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )

        with self.assertRaises(ValidationError):
            DocumentService.save_draft(document)

    def test_add_item(self):
        """Тест добавления строки."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )

        item, is_duplicate = DocumentService.add_item(
            document, self.nomenclature, quantity=2
        )

        self.assertEqual(item.quantity, 2)
        self.assertFalse(is_duplicate)

    def test_add_item_duplicate(self):
        """Тест добавления дубликата строки."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )

        DocumentService.add_item(document, self.nomenclature, quantity=2)
        item, is_duplicate = DocumentService.add_item(
            document, self.nomenclature, quantity=3
        )

        self.assertEqual(item.quantity, 5)
        self.assertTrue(is_duplicate)

    def test_post_document_success(self):
        """Тест проведения документа."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )

        # Создаём TireCode
        code = TireCode.objects.create(
            qr_code='TESTCODE001',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            is_active=True,
            is_used=False,
        )

        # Добавляем строку и сохраняем
        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentService.save_draft(document)

        # Проводим
        document = DocumentService.post_document(document)

        self.assertEqual(document.status, 'posted')
        self.assertIsNotNone(document.posted_at)

        # Проверяем, что код помечен
        code.refresh_from_db()
        self.assertTrue(code.is_used)
        self.assertFalse(code.is_active)
        self.assertEqual(code.document, document)

    def test_post_document_insufficient_codes(self):
        """Тест проведения при нехватке кодов — ошибка."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )

        # Добавляем строку с quantity=5, но создаём только 2 кода
        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=5,
        )
        TireCode.objects.create(
            qr_code='TESTCODE001',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            is_active=True,
            is_used=False,
        )
        TireCode.objects.create(
            qr_code='TESTCODE002',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            is_active=True,
            is_used=False,
        )

        DocumentService.save_draft(document)

        with self.assertRaises(ValidationError):
            DocumentService.post_document(document)

        # Документ остаётся saved
        document.refresh_from_db()
        self.assertEqual(document.status, 'saved')

    def test_unpost_document(self):
        """Тест распроведения документа."""
        # Создаём проведённый документ
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
            is_used=True,
            document=document,
        )

        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentService.save_draft(document)
        DocumentService.post_document(document)

        # Распроведём
        document = DocumentService.unpost_document(document)

        self.assertEqual(document.status, 'saved')
        self.assertIsNone(document.posted_at)

        # Проверяем, что код возвращён
        code.refresh_from_db()
        self.assertFalse(code.is_used)
        self.assertTrue(code.is_active)
        self.assertIsNone(code.document)

    def test_mark_deleted(self):
        """Тест пометки на удаление."""
        document = DocumentService.create(
            user=self.user,
            doc_type=self.doc_type,
            source_warehouse=self.warehouse,
        )

        DocumentItem.objects.create(
            document=document,
            nomenclature=self.nomenclature,
            quantity=1,
        )
        DocumentService.save_draft(document)

        document = DocumentService.mark_deleted(document)

        self.assertTrue(document.is_deleted)
        self.assertEqual(document.status, 'marked_deleted')
