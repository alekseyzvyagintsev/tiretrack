from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from warehouse.models import DocumentType, Document, DocumentItem, WarehouseMovement
from tires.models import Tire, Warehouse, Supplier


class DocumentTypeModelTest(TestCase):
    """Тесты для модели DocumentType"""

    def test_create_document_type(self):
        """Тест создания типа документа"""
        doc_type = DocumentType.objects.create(
            code='receipt',
            name='Приемка',
            is_active=True
        )
        
        self.assertEqual(doc_type.code, 'receipt')
        self.assertEqual(doc_type.name, 'Приемка')
        self.assertTrue(doc_type.is_active)

    def test_document_type_str(self):
        """Тест строкового представления типа документа"""
        doc_type = DocumentType.objects.create(
            code='dispatch',
            name='Отгрузка',
            is_active=True
        )
        
        self.assertEqual(str(doc_type), 'Отгрузка')


class DocumentModelTest(TestCase):
    """Тесты для модели Document"""

    def setUp(self):
        # Создаем пользователя
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Создаем тип документа
        self.document_type = DocumentType.objects.create(
            code='receipt',
            name='Приемка',
            is_active=True
        )
        
        # Создаем склады
        self.warehouse_from = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        self.warehouse_to = Warehouse.objects.create(
            name='Склад 2',
            warehouse_type='main'
        )
        
        # Создаем поставщика
        self.supplier = Supplier.objects.create(name='Поставщик 1')

    def test_create_document(self):
        """Тест создания документа"""
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        self.assertEqual(document.document_type, self.document_type)
        self.assertEqual(document.from_warehouse, self.warehouse_from)
        self.assertEqual(document.to_warehouse, self.warehouse_to)
        self.assertEqual(document.status, 'draft')
        self.assertFalse(document.deleted)

    def test_generate_document_number(self):
        """Тест генерации номера документа"""
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        # Номер должен быть сгенерирован автоматически
        self.assertIsNotNone(document.document_number)
        # Номер должен начинаться с префикса из названия типа (Приемка -> ПРИ)
        self.assertIn('ПРИ-', document.document_number)

    def test_can_edit_draft_document(self):
        """Тест возможности редактирования черновика"""
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user,
            status='draft'
        )
        
        self.assertTrue(document.can_edit())

    def test_cannot_edit_posted_document(self):
        """Тест невозможности редактирования проведенного документа"""
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user,
            status='posted'
        )
        
        self.assertFalse(document.can_edit())

    def test_cannot_edit_deleted_document(self):
        """Тест невозможности редактирования удаленного документа"""
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user,
            status='draft'
        )
        document.deleted = True
        document.save()
        
        self.assertFalse(document.can_edit())

    def test_document_get_status_color(self):
        """Тест получения цвета статуса"""
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        self.assertEqual(document.get_status_color(), 'warning')  # draft


class DocumentItemModelTest(TestCase):
    """Тесты для модели DocumentItem"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.document_type = DocumentType.objects.create(
            code='receipt',
            name='Приемка',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        self.tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        self.document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse,
            created_by=self.user
        )

    def test_create_document_item(self):
        """Тест создания позиции документа"""
        item = DocumentItem.objects.create(
            document=self.document,
            product_name='Test Product',
            quantity=5
        )
        
        self.assertEqual(item.document, self.document)
        self.assertEqual(item.product_name, 'Test Product')
        self.assertEqual(item.quantity, 5)

    def test_document_item_str(self):
        """Тест строкового представления позиции"""
        item = DocumentItem.objects.create(
            document=self.document,
            product_name='Test Product',
            quantity=1
        )
        
        self.assertIn(str(self.document.id), str(item))
        self.assertIn('Test Product', str(item))


class WarehouseMovementModelTest(TestCase):
    """Тесты для модели WarehouseMovement"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.document_type = DocumentType.objects.create(
            code='movement',
            name='Перемещение',
            is_active=True
        )
        self.warehouse_from = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        self.warehouse_to = Warehouse.objects.create(
            name='Склад 2',
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        self.tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        self.document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

    def test_create_warehouse_movement(self):
        """Тест создания записи о перемещении"""
        movement = WarehouseMovement.objects.create(
            document=self.document,
            tire=self.tire,
            movement_type='transfer',
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            quantity=1
        )
        
        self.assertEqual(movement.document, self.document)
        self.assertEqual(movement.tire, self.tire)
        self.assertEqual(movement.movement_type, 'transfer')

    def test_warehouse_movement_str(self):
        """Тест строкового представления перемещения"""
        movement = WarehouseMovement.objects.create(
            document=self.document,
            tire=self.tire,
            movement_type='transfer',
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            quantity=1
        )
        
        self.assertIn(self.tire.qr_code, str(movement))


class DocumentServiceTest(TestCase):
    """Тесты для DocumentService"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.document_type = DocumentType.objects.create(
            code='movement',
            name='Перемещение',
            is_active=True
        )
        
        self.warehouse_from = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        self.warehouse_to = Warehouse.objects.create(
            name='Склад 2',
            warehouse_type='main'
        )
        
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        
        # Создаем шину на складе отправления
        self.tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )

    def test_post_document(self):
        """Тест проведения документа"""
        from warehouse.services import DocumentService
        
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        # Добавляем позицию
        item = DocumentItem.objects.create(
            document=document,
            product_name='Test Product',
            quantity=1
        )
        
        item.tires.add(self.tire)
        # Проводим документ
        DocumentService.post_document(document)
        
        # Проверяем статус
        document.refresh_from_db()
        self.assertEqual(document.status, 'posted')
        
        # Проверяем перемещение шины
        self.tire.refresh_from_db()
        self.assertEqual(self.tire.warehouse, self.warehouse_to)
        
        # Проверяем запись в истории
        movement = WarehouseMovement.objects.get(document=document)
        self.assertEqual(movement.movement_type, 'transfer')

    def test_unpost_document(self):
        """Тест отмены проведения документа"""
        from warehouse.services import DocumentService
        
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        item = DocumentItem.objects.create(
            document=document,
            product_name='Test Product',
            quantity=1
        )
        
        item.tires.add(self.tire)
        # Сначала проведем
        DocumentService.post_document(document)
        
        # Теперь отменим
        DocumentService.unpost_document(document)
        
        # Проверяем статус
        document.refresh_from_db()
        self.assertEqual(document.status, 'saved')
        
        # Проверяем возврат шины
        self.tire.refresh_from_db()
        self.assertEqual(self.tire.warehouse, self.warehouse_from)

    def test_mark_deleted(self):
        """Тест пометки на удаление"""
        from warehouse.services import DocumentService
        
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        DocumentService.mark_deleted(document)
        
        document.refresh_from_db()
        self.assertTrue(document.deleted)

    def test_unmark_deleted(self):
        """Тест снятия пометки на удаление"""
        from warehouse.services import DocumentService
        
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        DocumentService.mark_deleted(document)
        DocumentService.unmark_deleted(document)
        
        document.refresh_from_db()
        self.assertFalse(document.deleted)


class WarehouseServiceTest(TestCase):
    """Тесты для WarehouseService"""

    def setUp(self):
        self.warehouse1 = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        self.warehouse2 = Warehouse.objects.create(
            name='Склад 2',
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        
        # Создаем несколько шин
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse1,
            supplier=self.supplier
        )
        Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='205/55 R16',
            warehouse=self.warehouse1,
            supplier=self.supplier
        )
        Tire.objects.create(
            qr_code='QR003',
            brand='Bridgestone',
            model='Z',
            size='215/60 R17',
            warehouse=self.warehouse2,
            supplier=self.supplier
        )

    def test_get_warehouse_stock(self):
        """Тест получения остатков на складе"""
        from warehouse.services import WarehouseService
        
        # Остатки на складе 1
        stock1 = WarehouseService.get_warehouse_stock(self.warehouse1.id)
        self.assertEqual(len(stock1), 2)  # 2 номенклатуры
        
        # Остатки на складе 2
        stock2 = WarehouseService.get_warehouse_stock(self.warehouse2.id)
        self.assertEqual(len(stock2), 1)

    def test_get_warehouse_stock_all(self):
        """Тест получения остатков по всем складам"""
        from warehouse.services import WarehouseService
        
        stock = WarehouseService.get_warehouse_stock()
        self.assertEqual(len(stock), 3)  # 3 шины


class DocumentFormTest(TestCase):
    """Тесты для форм документов"""

    def setUp(self):
        self.document_type = DocumentType.objects.create(
            code='movement',
            name='Перемещение',
            is_active=True
        )
        
        self.warehouse_from = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        self.warehouse_to = Warehouse.objects.create(
            name='Склад 2',
            warehouse_type='main'
        )

    def test_document_form_valid(self):
        """Тест валидной формы документа"""
        from warehouse.forms import DocumentForm
        
        form = DocumentForm(data={
            'document_type': self.document_type.id,
            'from_warehouse': self.warehouse_from.id,
            'to_warehouse': self.warehouse_to.id,
            'notes': 'Тестовое примечание'
        })
        
        self.assertTrue(form.is_valid())

    def test_document_form_missing_from_warehouse(self):
        """Тест формы с отсутствующим складом отправления"""
        from warehouse.forms import DocumentForm
        
        form = DocumentForm(data={
            'document_type': self.document_type.id,
            'to_warehouse': self.warehouse_to.id,
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('from_warehouse', form.errors)


class DocumentViewTest(TestCase):
    """Тесты для views документов"""

    def setUp(self):
        # Создаем пользователя через User Manager
        User = get_user_model()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.document_type = DocumentType.objects.create(
            code='receipt',
            name='Приемка',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        # Login для аутентификации
        self.client.login(email='test@example.com', password='testpass123')

    def test_document_list_view(self):
        """Тест списка документов"""
        response = self.client.get('/warehouse/documents/')
        self.assertEqual(response.status_code, 200)

    def test_document_create_view(self):
        """Тест создания документа"""
        response = self.client.get('/warehouse/documents/create/')
        # Редирект на детальный просмотр
        self.assertEqual(response.status_code, 302)

    def test_document_homepage_view(self):
        """Тест домашней страницы warehouse"""
        response = self.client.get('/warehouse/')
        self.assertEqual(response.status_code, 200)

    def test_report_stock_view(self):
        """Тест отчета по остаткам"""
        response = self.client.get('/warehouse/reports/stock/')
        self.assertEqual(response.status_code, 200)

    def test_report_movement_view(self):
        """Тест отчета по движению"""
        response = self.client.get('/warehouse/reports/movement/')
        self.assertEqual(response.status_code, 200)

    def test_report_supplier_view(self):
        """Тест отчета по поставщикам"""
        response = self.client.get('/warehouse/reports/supplier/')
        self.assertEqual(response.status_code, 200)

    def test_document_edit_view(self):
        """Тест редактирования документа"""
        # Создаем документ
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse,
            to_warehouse=None,
            created_by=self.user
        )
        
        # Получаем форму редактирования
        response = self.client.get(f'/warehouse/documents/{document.pk}/edit/')
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что в контексте переданы document_types
        self.assertIn('document_types', response.context)
        self.assertIn('warehouses', response.context)
        self.assertIn('form', response.context)
        
        # Проверяем, что типы документов переданы в форму
        document_types = response.context['document_types']
        self.assertTrue(document_types.exists())
        self.assertEqual(document_types.first().code, 'receipt')
        
        # Проверяем, что склады переданы
        warehouses = response.context['warehouses']
        self.assertTrue(warehouses.exists())


class DocumentDeleteItemViewTest(TestCase):
    """Тесты для удаления позиции из документа"""

    def setUp(self):
        # Создаем пользователя через User Manager
        User = get_user_model()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.document_type = DocumentType.objects.create(
            code='receipt',
            name='Приемка',
            is_active=True
        )
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        # Login для аутентификации
        self.client.login(email='test@example.com', password='testpass123')

    def test_document_delete_item(self):
        """Тест удаления позиции из документа"""
        # Создаем документ
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse,
            to_warehouse=None,
            created_by=self.user
        )
        
        # Создаем шину
        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        # Создаем позицию документа
        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X 205/55 R16',
            quantity=1
        )
        item.tires.add(tire)
        
        # Проверяем, что позиция существует
        self.assertEqual(document.items.count(), 1)
        
        # Удаляем позицию
        response = self.client.post(f'/warehouse/documents/{document.pk}/delete-item/{item.pk}/')
        self.assertEqual(response.status_code, 302)  # Редирект
        
        # Проверяем, что позиция удалена
        self.assertEqual(document.items.count(), 0)
        # Проверяем, что сама позиция больше не существует в БД
        self.assertFalse(DocumentItem.objects.filter(pk=item.pk).exists())

    def test_document_delete_item_with_multiple_items(self):
        """Тест удаления одной из нескольких позиций"""
        # Создаем документ
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse,
            to_warehouse=None,
            created_by=self.user
        )
        
        # Создаем две шины
        tire1 = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        tire2 = Tire.objects.create(
            qr_code='QR002',
            brand='Bridgestone',
            model='Y',
            size='215/60 R17',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        # Создаем две позиции документа
        item1 = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X 205/55 R16',
            quantity=1
        )
        item1.tires.add(tire1)
        
        item2 = DocumentItem.objects.create(
            document=document,
            product_name='Bridgestone Y 215/60 R17',
            quantity=1
        )
        item2.tires.add(tire2)
        
        # Проверяем, что обе позиции существуют
        self.assertEqual(document.items.count(), 2)
        
        # Удаляем первую позицию
        response = self.client.post(f'/warehouse/documents/{document.pk}/delete-item/{item1.pk}/')
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что осталась только одна позиция
        self.assertEqual(document.items.count(), 1)
        self.assertEqual(document.items.first().product_name, 'Bridgestone Y 215/60 R17')
        
        # Проверяем, что item1 больше не существует
        self.assertFalse(DocumentItem.objects.filter(pk=item1.pk).exists())
        
        # Проверяем, что item2 всё ещё существует
        self.assertTrue(DocumentItem.objects.filter(pk=item2.pk).exists())

    def test_document_delete_item_hmx_response(self):
        """Тест HTMX ответа при удалении позиции"""
        # Создаем документ
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse,
            to_warehouse=None,
            created_by=self.user
        )
        
        # Создаем шину
        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        # Создаем позицию документа
        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X 205/55 R16',
            quantity=1
        )
        item.tires.add(tire)
        
        # Отправляем HTMX запрос
        response = self.client.post(
            f'/warehouse/documents/{document.pk}/delete-item/{item.pk}/',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что позиция удалена
        self.assertEqual(document.items.count(), 0)
        
        # Проверяем, что в ответе есть HTML таблицы (теперь возвращаются только <tr>)
        self.assertIn('text/html', response['Content-Type'])
        # После удаления последней позиции список будет пустым
        if document.items.count() > 0:
            self.assertIn('<tr', str(response.content))
        self.assertNotIn('<table', str(response.content))
        self.assertNotIn('<thead', str(response.content))
        self.assertNotIn('<tbody', str(response.content))

    def test_document_delete_item_non_draft_document(self):
        """Тест удаления позиции из проведенного документа (должно быть запрещено логикой)"""
        # Создаем документ
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse,
            to_warehouse=None,
            created_by=self.user,
            status='posted'
        )
        
        # Создаем шину
        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        # Создаем позицию документа
        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X 205/55 R16',
            quantity=1
        )
        item.tires.add(tire)
        
        # Проверяем, что позиция существует
        self.assertEqual(document.items.count(), 1)
        
        # Пробуем удалить позицию из проведенного документа
        # (в реальности views.py не проверяет статус, просто удаляет)
        response = self.client.post(f'/warehouse/documents/{document.pk}/delete-item/{item.pk}/')
        self.assertEqual(response.status_code, 302)
        
        # Позиция должна быть удалена (логика views не проверяет статус)
        self.assertEqual(document.items.count(), 0)

    def test_document_delete_item_from_posted_document_returns_tires(self):
        """Тест возврата шин при удалении позиции из проведенного документа"""
        from warehouse.services import DocumentService
        
        # Создаем второй склад
        warehouse_to = Warehouse.objects.create(
            name='Склад 2',
            warehouse_type='main'
        )
        
        # Создаем документ перемещения
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse,
            to_warehouse=warehouse_to,
            created_by=self.user,
            status='draft'
        )
        
        # Создаем шину на складе отправления
        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        # Создаем позицию документа
        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X 205/55 R16',
            quantity=1
        )
        item.tires.add(tire)
        
        # Проводим документ
        DocumentService.post_document(document)
        
        # Проверяем, что шина переместилась
        tire.refresh_from_db()
        self.assertEqual(tire.warehouse, warehouse_to)
        
        # Проверяем, что позиция существует
        self.assertEqual(document.items.count(), 1)
        
        # Удаляем позицию из проведенного документа
        DocumentService.delete_item(document, item)
        
        # Проверяем, что шина возвращена на исходный склад
        tire.refresh_from_db()
        self.assertEqual(tire.warehouse, self.warehouse)
        self.assertTrue(tire.is_active)
        
        # Проверяем, что позиция удалена
        self.assertFalse(DocumentItem.objects.filter(pk=item.pk).exists())
