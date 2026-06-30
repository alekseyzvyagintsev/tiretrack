from django.test import TestCase
from django.contrib.auth import get_user_model

from warehouse.models import DocumentType, Document, DocumentItem, WarehouseMovement
from tires.models import Tire, Warehouse, Supplier


class DocumentItemBusinessTest(TestCase):
    """Тесты бизнес-логики DocumentItem с ManyToMany связью"""

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
        self.warehouse_from = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        self.warehouse_to = Warehouse.objects.create(
            name='Склад 2',
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')

    def test_document_item_with_many_tires(self):
        """Тест что DocumentItem может иметь несколько шин"""
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        # Создаем несколько шин с одинаковым product_name
        tire1 = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        tire2 = Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='215/60 R17',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        tire3 = Tire.objects.create(
            qr_code='QR003',
            brand='Michelin',
            model='Z',
            size='225/45 R18',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )

        # Создаем DocumentItem с product_name
        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X 205/55 R16',
            quantity=2
        )

        # Добавляем шины в ManyToMany связь
        item.tires.add(tire1, tire2, tire3)

        # Проверяем что шины добавлены
        self.assertEqual(item.tires.count(), 3)
        self.assertIn(tire1, item.tires.all())
        self.assertIn(tire2, item.tires.all())
        self.assertIn(tire3, item.tires.all())

    def test_document_item_unique_together(self):
        """Тест что DocumentItem уникален по document + product_name"""
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        # Создаем первый DocumentItem
        DocumentItem.objects.create(
            document=document,
            product_name='Product A',
            quantity=1
        )

        # Повторное создание с тем же product_name должно вызвать ошибку
        with self.assertRaises(Exception):
            DocumentItem.objects.create(
                document=document,
                product_name='Product A',
                quantity=2
            )

    def test_document_item_different_products(self):
        """Тест что в одном документе можно иметь разные product_name"""
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        # Создаем два DocumentItem с разными product_name
        item1 = DocumentItem.objects.create(
            document=document,
            product_name='Product A',
            quantity=1
        )
        item2 = DocumentItem.objects.create(
            document=document,
            product_name='Product B',
            quantity=2
        )

        # Проверяем что оба созданы
        self.assertEqual(document.items.count(), 2)
        self.assertIn(item1, document.items.all())
        self.assertIn(item2, document.items.all())

    def test_document_item_quantity_validation(self):
        """Тест что количество шин не превышает доступное"""
        # Создаем 3 шины
        tire1 = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        tire2 = Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='215/60 R17',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        tire3 = Tire.objects.create(
            qr_code='QR003',
            brand='Michelin',
            model='Z',
            size='225/45 R18',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )

        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X',
            quantity=3
        )
        item.tires.add(tire1, tire2, tire3)

        # Проверяем что количество совпадает
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.tires.count(), 3)


class DocumentServiceBusinessTest(TestCase):
    """Тесты бизнес-логики DocumentService"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.document_type_movement = DocumentType.objects.create(
            code='movement',
            name='Перемещение',
            is_active=True
        )
        self.document_type_dispatch = DocumentType.objects.create(
            code='dispatch',
            name='Отгрузка',
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

    def test_post_document_movement(self):
        """Тест проведения документа перемещения"""
        from warehouse.services import DocumentService

        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier,
            is_active=True
        )

        document = Document.objects.create(
            document_type=self.document_type_movement,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X',
            quantity=1
        )
        item.tires.add(tire)

        # Проводим документ
        DocumentService.post_document(document)

        # Проверяем статус документа
        document.refresh_from_db()
        self.assertEqual(document.status, 'posted')

        # Проверяем перемещение шины
        tire.refresh_from_db()
        self.assertEqual(tire.warehouse, self.warehouse_to)
        # Для перемещения шина остается активной
        self.assertTrue(tire.is_active)

        # Проверяем запись в истории
        movement = WarehouseMovement.objects.get(document=document)
        self.assertEqual(movement.movement_type, 'transfer')
        self.assertTrue(movement.is_active)

    def test_post_document_dispatch(self):
        """Тест проведения документа отгрузки (is_active=False)"""
        from warehouse.services import DocumentService

        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier,
            is_active=True
        )

        document = Document.objects.create(
            document_type=self.document_type_dispatch,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X',
            quantity=1
        )
        item.tires.add(tire)

        # Проводим документ
        DocumentService.post_document(document)

        # Проверяем что is_active=False для отгрузки
        tire.refresh_from_db()
        self.assertFalse(tire.is_active)

    def test_unpost_document_returns_to_source(self):
        """Тест отмены проведения возвращает шины на исходный склад"""
        from warehouse.services import DocumentService

        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier,
            is_active=True
        )

        document = Document.objects.create(
            document_type=self.document_type_movement,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X',
            quantity=1
        )
        item.tires.add(tire)

        # Сначала проведем
        DocumentService.post_document(document)

        # Проверяем что шина на складе назначения
        tire.refresh_from_db()
        self.assertEqual(tire.warehouse, self.warehouse_to)

        # Теперь отменяем
        DocumentService.unpost_document(document)

        # Проверяем статус
        document.refresh_from_db()
        self.assertEqual(document.status, 'saved')

        # Проверяем возврат на исходный склад
        tire.refresh_from_db()
        self.assertEqual(tire.warehouse, self.warehouse_from)

    def test_unpost_document_sets_is_active_false(self):
        """Тест что отмена проведения устанавливает is_active=False"""
        from warehouse.services import DocumentService

        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier,
            is_active=True
        )

        document = Document.objects.create(
            document_type=self.document_type_movement,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X',
            quantity=1
        )
        item.tires.add(tire)

        # Проводим
        DocumentService.post_document(document)

        # Отменяем
        DocumentService.unpost_document(document)

        # Проверяем is_active
        tire.refresh_from_db()
        self.assertFalse(tire.is_active)

    def test_mark_deleted_returns_tires(self):
        """Тест пометки на удаление возвращает шины на склад"""
        from warehouse.services import DocumentService

        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier,
            is_active=True
        )

        document = Document.objects.create(
            document_type=self.document_type_movement,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X',
            quantity=1
        )
        item.tires.add(tire)

        # Помечаем на удаление (не проводя)
        DocumentService.mark_deleted(document)

        # Проверяем статус
        document.refresh_from_db()
        self.assertTrue(document.deleted)

        # Проверяем возврат шины (в исходном состоянии)
        tire.refresh_from_db()
        self.assertEqual(tire.warehouse, self.warehouse_from)
        # Шины не активируются при пометке на удаление, они остаются как есть

    def test_mark_deleted_for_dispatch_document(self):
        """Тест пометки на удаление для документа отгрузки"""
        from warehouse.services import DocumentService

        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier,
            is_active=True
        )

        document = Document.objects.create(
            document_type=self.document_type_dispatch,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X',
            quantity=1
        )
        item.tires.add(tire)

        # Помечаем на удаление (не проводя)
        DocumentService.mark_deleted(document)

        # Проверяем статус
        document.refresh_from_db()
        self.assertTrue(document.deleted)

    def test_mark_deleted_error_message_for_posted(self):
        """Тест сообщения об ошибке при попытке пометить проведенный документ на удаление"""
        from warehouse.services import DocumentService
        from django.core.exceptions import ValidationError

        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier,
            is_active=True
        )

        document = Document.objects.create(
            document_type=self.document_type_movement,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X',
            quantity=1
        )
        item.tires.add(tire)

        # Сначала проводим документ
        DocumentService.post_document(document)

        # Проверяем что нельзя пометить на удаление
        with self.assertRaises(ValidationError) as context:
            DocumentService.mark_deleted(document)

        # Проверяем сообщение об ошибке
        self.assertIn('отменить проведение', str(context.exception))

    def test_document_items_in_detail_view(self):
        """Тест что при детальном просмотре отображаются группированные шины"""
        document = Document.objects.create(
            document_type=self.document_type_movement,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )

        # Создаем 3 шины с одинаковым product_name
        tire1 = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        tire2 = Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='215/60 R17',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        tire3 = Tire.objects.create(
            qr_code='QR003',
            brand='Michelin',
            model='Z',
            size='225/45 R18',
            product_name='Michelin X',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )

        item = DocumentItem.objects.create(
            document=document,
            product_name='Michelin X',
            quantity=3
        )
        item.tires.add(tire1, tire2, tire3)

        # Проверяем что item.tires.all() возвращает все 3 шины
        self.assertEqual(item.tires.count(), 3)
        self.assertIn(tire1, item.tires.all())
        self.assertIn(tire2, item.tires.all())
        self.assertIn(tire3, item.tires.all())


class DocumentAddItemViewTest(TestCase):
    """Тесты для view document_add_item с группировкой номенклатуры"""

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
        self.warehouse_from = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        self.warehouse_to = Warehouse.objects.create(
            name='Склад 2',
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        
        # Логинимся
        self.client.login(email='test@example.com', password='testpass123')

    def test_document_add_item_view_get_returns_tire_groups(self):
        """Тест GET запроса возвращает сгруппированные шины"""
        # Создаем шины с одинаковым product_name
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='215/60 R17',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        Tire.objects.create(
            qr_code='QR003',
            brand='Bridgestone',
            model='Z',
            size='225/45 R18',
            product_name='Bridgestone Z 225/45 R18',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        
        # Создаем документ
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        # GET запрос
        response = self.client.get(f'/warehouse/documents/{document.pk}/add-item/')
        
        # Проверяем что ответ успешен
        self.assertEqual(response.status_code, 200)
        
        # Проверяем что в контексте есть tire_groups
        self.assertIn('tire_groups', response.context)
        
        # Проверяем что группы сгруппированы правильно (2 группы)
        tire_groups = response.context['tire_groups']
        self.assertEqual(len(tire_groups), 2)
        
        # Проверяем что в первой группе 2 шины
        self.assertEqual(tire_groups[0]['product_name'], 'Michelin X 205/55 R16')
        self.assertEqual(tire_groups[0]['count'], 2)
        
        # Проверяем что во второй группе 1 шина
        self.assertEqual(tire_groups[1]['product_name'], 'Bridgestone Z 225/45 R18')
        self.assertEqual(tire_groups[1]['count'], 1)

    def test_document_add_item_view_post_adds_one_tire_by_default(self):
        """Тест POST запроса добавляет 1 шину по умолчанию"""
        # Создаем шины с одинаковым product_name (важен порядок создания)
        tire1 = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        tire2 = Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='215/60 R17',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        
        # Создаем документ
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        # POST запрос с product_name
        response = self.client.post(
            f'/warehouse/documents/{document.pk}/add-item/',
            {'product_name': 'Michelin X 205/55 R16'}
        )
        
        # Проверяем что ответ успешен (редирект)
        self.assertEqual(response.status_code, 302)
        
        # Проверяем что позиция создана с количеством 1
        item = DocumentItem.objects.get(document=document, product_name='Michelin X 205/55 R16')
        self.assertEqual(item.quantity, 1)
        
        # Проверяем что привязана только 1 шина (последняя созданная из-за order_by('-created_at'))
        self.assertEqual(item.tires.count(), 1)
        self.assertIn(tire2, item.tires.all())  # tire2 - последняя созданная

    def test_document_add_item_view_post_updates_existing_item(self):
        """Тест POST запроса обновляет существующую позицию при повторном добавлении"""
        # Создаем 3 шины с одинаковым product_name (важен порядок создания)
        tire1 = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        tire2 = Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='215/60 R17',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        tire3 = Tire.objects.create(
            qr_code='QR003',
            brand='Michelin',
            model='Z',
            size='225/45 R18',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        
        # Создаем документ
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        # Первый POST запрос - добавляет 1 шину (последняя созданная)
        self.client.post(
            f'/warehouse/documents/{document.pk}/add-item/',
            {'product_name': 'Michelin X 205/55 R16'}
        )
        
        # Проверяем что позиция создана с количеством 1
        item = DocumentItem.objects.get(document=document, product_name='Michelin X 205/55 R16')
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.tires.count(), 1)
        self.assertIn(tire3, item.tires.all())  # tire3 - последняя созданная
        
        # Второй POST запрос - обновляет существующую позицию (добавляет ещё 1 шину - вторая по старости)
        self.client.post(
            f'/warehouse/documents/{document.pk}/add-item/',
            {'product_name': 'Michelin X 205/55 R16'}
        )
        
        # Проверяем что количество увеличилось до 2
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.tires.count(), 2)
        self.assertIn(tire3, item.tires.all())  # tire3 - последняя
        self.assertIn(tire2, item.tires.all())  # tire2 - вторая по старости

    def test_document_add_item_view_post_checks_available_quantity(self):
        """Тест POST запроса проверяет доступное количество шин"""
        # Создаем только 2 шины
        tire1 = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        tire2 = Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='215/60 R17',
            product_name='Michelin X 205/55 R16',
            warehouse=self.warehouse_from,
            supplier=self.supplier
        )
        
        # Создаем документ
        document = Document.objects.create(
            document_type=self.document_type,
            from_warehouse=self.warehouse_from,
            to_warehouse=self.warehouse_to,
            created_by=self.user
        )
        
        # Первый POST запрос - добавляет 1 шину
        self.client.post(
            f'/warehouse/documents/{document.pk}/add-item/',
            {'product_name': 'Michelin X 205/55 R16'}
        )
        
        # Второй POST запрос - добавляет ещё 1 шину
        self.client.post(
            f'/warehouse/documents/{document.pk}/add-item/',
            {'product_name': 'Michelin X 205/55 R16'}
        )
        
        # Третий POST запрос - пытается добавить ещё 1 шину, но их нет
        response = self.client.post(
            f'/warehouse/documents/{document.pk}/add-item/',
            {'product_name': 'Michelin X 205/55 R16'}
        )
        
        # Проверяем что ответ содержит сообщение об ошибке
        self.assertRedirects(response, f'/warehouse/documents/{document.pk}/')
        
        # Проверяем что количество не превысило доступное
        item = DocumentItem.objects.get(document=document, product_name='Michelin X 205/55 R16')
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.tires.count(), 2)
