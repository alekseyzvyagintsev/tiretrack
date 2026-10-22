"""Тесты для AJAX endpoints warehouse (nomenclature_search, document_add_item, etc.)."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from tires.models import Platform, Warehouse, TireNomenclature, TireCode
from warehouse.models import Document, DocumentItem, DocType
from warehouse.services import DocumentService

User = get_user_model()


class NomenclatureSearchViewTest(TestCase):
    """Тесты для AJAX nomenclature_search (A1)."""

    def setUp(self):
        self.platform = Platform.objects.create(name='Test Platform')
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main',
            platform=self.platform
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            platform=self.platform,
            role='manager'
        )
        self.client.login(email='test@example.com', password='testpass123')

        # Создаём номенклатуру
        self.nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X'
        )

    def test_nomenclature_search_returns_json(self):
        """Тест что nomenclature_search возвращает JSON"""
        response = self.client.get(
            reverse('warehouse:nomenclature-search'),
            {'q': 'Michelin'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_nomenclature_search_by_brand(self):
        """Тест поиска по бренду"""
        response = self.client.get(
            reverse('warehouse:nomenclature-search'),
            {'q': 'Michelin'}
        )
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['brand'], 'Michelin')

    def test_nomenclature_search_by_model(self):
        """Тест поиска по модели"""
        response = self.client.get(
            reverse('warehouse:nomenclature-search'),
            {'q': 'X'}
        )
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['model'], 'X')

    def test_nomenclature_search_by_size(self):
        """Тест поиска по размеру"""
        response = self.client.get(
            reverse('warehouse:nomenclature-search'),
            {'q': '205/55 R16'}
        )
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['size'], '205/55 R16')

    def test_nomenclature_search_empty_query(self):
        """Тест что пустой запрос возвращает пустой список"""
        response = self.client.get(
            reverse('warehouse:nomenclature-search'),
            {'q': ''}
        )
        data = response.json()
        self.assertEqual(len(data['results']), 0)

    def test_nomenclature_search_limit(self):
        """Тест что работает лимит результатов"""
        response = self.client.get(
            reverse('warehouse:nomenclature-search'),
            {'q': 'Michelin', 'limit': 10}
        )
        data = response.json()
        self.assertLessEqual(len(data['results']), 10)


class DocumentAddItemViewTest(TestCase):
    """Тесты для AJAX document_add_item (A2)."""

    def setUp(self):
        self.platform = Platform.objects.create(name='Test Platform')
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main',
            platform=self.platform
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            platform=self.platform,
            role='manager'
        )
        self.doc_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True
        )
        self.nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        self.document = Document.objects.create(
            doc_type=self.doc_type,
            author=self.user,
            source_platform=self.platform,
            source_warehouse=self.warehouse,
            status='draft'
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_document_add_item_returns_json(self):
        """Тест что document_add_item возвращает JSON"""
        response = self.client.post(
            reverse('warehouse:document-add-item', args=[self.document.pk]),
            {
                'nomenclature_id': self.nomenclature.pk,
                'quantity': 1
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_document_add_item_creates_item(self):
        """Тест создания DocumentItem"""
        response = self.client.post(
            reverse('warehouse:document-add-item', args=[self.document.pk]),
            {
                'nomenclature_id': self.nomenclature.pk,
                'quantity': 2
            }
        )
        data = response.json()
        self.assertEqual(data['quantity'], 2)
        self.assertTrue(DocumentItem.objects.filter(
            document=self.document,
            nomenclature=self.nomenclature
        ).exists())

    def test_document_add_item_duplicate(self):
        """Тест дедупликации при добавлении"""
        # Первый раз
        self.client.post(
            reverse('warehouse:document-add-item', args=[self.document.pk]),
            {
                'nomenclature_id': self.nomenclature.pk,
                'quantity': 1
            }
        )
        # Второй раз
        response = self.client.post(
            reverse('warehouse:document-add-item', args=[self.document.pk]),
            {
                'nomenclature_id': self.nomenclature.pk,
                'quantity': 1
            }
        )
        data = response.json()
        self.assertTrue(data['is_duplicate'])
        # Количество должно обновиться
        self.assertEqual(data['quantity'], 2)

    def test_document_add_item_forbidden_for_posted(self):
        """Тест что нельзя добавлять в проведённый документ"""
        # Добавляем item
        DocumentItem.objects.create(
            document=self.document,
            nomenclature=self.nomenclature,
            quantity=1
        )
        # Создаём TireCode
        TireCode.objects.create(
            qr_code='QR-AJAX-0001',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse
        )
        self.document.tire_codes.add(self.nomenclature.tire_codes.first())
        # Сначала сохраняем
        DocumentService.save_draft(self.document)
        # Проводим документ
        DocumentService.post_document(self.document)

        response = self.client.post(
            reverse('warehouse:document-add-item', args=[self.document.pk]),
            {
                'nomenclature_id': self.nomenclature.pk,
                'quantity': 1
            }
        )
        self.assertEqual(response.status_code, 400)


class DocumentUpdateItemViewTest(TestCase):
    """Тесты для AJAX document_update_item (A3)."""

    def setUp(self):
        self.platform = Platform.objects.create(name='Test Platform')
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main',
            platform=self.platform
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            platform=self.platform,
            role='manager'
        )
        self.doc_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True
        )
        self.nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        self.document = Document.objects.create(
            doc_type=self.doc_type,
            author=self.user,
            source_platform=self.platform,
            source_warehouse=self.warehouse,
            status='draft'
        )
        self.item = DocumentItem.objects.create(
            document=self.document,
            nomenclature=self.nomenclature,
            quantity=1
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_document_update_item_updates_quantity(self):
        """Тест обновления количества"""
        response = self.client.post(
            reverse('warehouse:document-update-item', args=[self.document.pk, self.item.pk]),
            {'quantity': 5}
        )
        data = response.json()
        self.assertEqual(data['quantity'], 5)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 5)

    def test_document_update_item_forbidden_for_posted(self):
        """Тест что нельзя обновить в проведённом документе"""
        TireCode.objects.create(
            qr_code='QR-AJAX-0002',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse
        )
        self.document.tire_codes.add(self.nomenclature.tire_codes.first())
        DocumentService.save_draft(self.document)
        DocumentService.post_document(self.document)

        response = self.client.post(
            reverse('warehouse:document-update-item', args=[self.document.pk, self.item.pk]),
            {'quantity': 10}
        )
        self.assertEqual(response.status_code, 400)


class DocumentDeleteItemViewTest(TestCase):
    """Тесты для AJAX document_delete_item (A4)."""

    def setUp(self):
        self.platform = Platform.objects.create(name='Test Platform')
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main',
            platform=self.platform
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            platform=self.platform,
            role='manager'
        )
        self.doc_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True
        )
        self.nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        self.document = Document.objects.create(
            doc_type=self.doc_type,
            author=self.user,
            source_platform=self.platform,
            source_warehouse=self.warehouse,
            status='draft'
        )
        self.item = DocumentItem.objects.create(
            document=self.document,
            nomenclature=self.nomenclature,
            quantity=1
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_document_delete_item_removes_item(self):
        """Тест удаления DocumentItem"""
        response = self.client.post(
            reverse('warehouse:document-delete-item', args=[self.document.pk, self.item.pk])
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(DocumentItem.objects.filter(
            document=self.document,
            pk=self.item.pk
        ).exists())

    def test_document_delete_item_forbidden_for_posted(self):
        """Тест что нельзя удалить из проведённого документа"""
        TireCode.objects.create(
            qr_code='QR-AJAX-0003',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse
        )
        self.document.tire_codes.add(self.nomenclature.tire_codes.first())
        DocumentService.save_draft(self.document)
        DocumentService.post_document(self.document)

        response = self.client.post(
            reverse('warehouse:document-delete-item', args=[self.document.pk, self.item.pk])
        )
        self.assertEqual(response.status_code, 400)


class DocumentAutosaveViewTest(TestCase):
    """Тесты для AJAX document_autosave (A8)."""

    def setUp(self):
        self.platform = Platform.objects.create(name='Test Platform')
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main',
            platform=self.platform
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            platform=self.platform,
            role='manager'
        )
        self.doc_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True
        )
        self.nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        self.document = Document.objects.create(
            doc_type=self.doc_type,
            author=self.user,
            source_platform=self.platform,
            source_warehouse=self.warehouse,
            status='draft'
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_document_autosave_returns_json(self):
        """Тест что document_autosave возвращает JSON"""
        response = self.client.post(
            reverse('warehouse:document-autosave', args=[self.document.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_document_autosave_success(self):
        """Тест успешного автосохранения"""
        response = self.client.post(
            reverse('warehouse:document-autosave', args=[self.document.pk])
        )
        data = response.json()
        self.assertTrue(data['success'])

    def test_document_autosave_forbidden_for_non_author(self):
        """Тест что чужой пользователь не может автосохранить"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            platform=self.platform,
            role='manager'
        )
        self.client.logout()
        self.client.login(email='other@example.com', password='otherpass123')

        response = self.client.post(
            reverse('warehouse:document-autosave', args=[self.document.pk])
        )
        self.assertEqual(response.status_code, 400)

    def test_document_autosave_forbidden_for_saved(self):
        """Тест что автосохранение только для draft"""
        self.document.status = 'saved'
        self.document.save()

        response = self.client.post(
            reverse('warehouse:document-autosave', args=[self.document.pk])
        )
        self.assertEqual(response.status_code, 400)
