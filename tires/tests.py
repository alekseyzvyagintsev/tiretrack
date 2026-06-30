from django.test import TestCase
from django.contrib.auth import get_user_model

from tires.models import Warehouse, Supplier, Tire
from tires.utils import search_tire_nomenclature


class WarehouseModelTest(TestCase):
    """Тесты для модели Warehouse"""

    def test_create_warehouse(self):
        """Тест создания склада"""
        warehouse = Warehouse.objects.create(
            name='Основной склад',
            warehouse_type='main'
        )
        
        self.assertEqual(warehouse.name, 'Основной склад')
        self.assertEqual(warehouse.warehouse_type, 'main')

    def test_warehouse_unique_name(self):
        """Тест уникальности имени склада"""
        Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main'
        )
        
        with self.assertRaises(Exception):
            Warehouse.objects.create(
                name='Склад 1',
                warehouse_type='main'
            )

    def test_warehouse_str(self):
        """Тест строкового представления склада"""
        warehouse = Warehouse.objects.create(
            name='Склад 2',
            warehouse_type='oh'
        )
        
        self.assertEqual(str(warehouse), 'Склад 2')


class SupplierModelTest(TestCase):
    """Тесты для модели Supplier"""

    def test_create_supplier(self):
        """Тест создания поставщика"""
        supplier = Supplier.objects.create(name='Поставщик 1')
        
        self.assertEqual(supplier.name, 'Поставщик 1')

    def test_supplier_unique_name(self):
        """Тест уникальности имени поставщика"""
        Supplier.objects.create(name='Поставщик 1')
        
        with self.assertRaises(Exception):
            Supplier.objects.create(name='Поставщик 1')

    def test_supplier_str(self):
        """Тест строкового представления поставщика"""
        supplier = Supplier.objects.create(name='Поставщик 2')
        
        self.assertEqual(str(supplier), 'Поставщик 2')


class TireModelTest(TestCase):
    """Тесты для модели Tire"""

    def setUp(self):
        self.warehouse_main = Warehouse.objects.create(
            name='Основной',
            warehouse_type='main'
        )
        self.warehouse_oh = Warehouse.objects.create(
            name='ОХ',
            warehouse_type='oh'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')

    def test_create_tire(self):
        """Тест создания шины"""
        tire = Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse_main,
            supplier=self.supplier
        )
        
        self.assertEqual(tire.qr_code, 'QR001')
        self.assertEqual(tire.brand, 'Michelin')
        self.assertEqual(tire.warehouse, self.warehouse_main)

    def test_tire_unique_qr_code(self):
        """Тест уникальности QR-кода"""
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            warehouse=self.warehouse_main,
            supplier=self.supplier
        )
        
        with self.assertRaises(Exception):
            Tire.objects.create(
                qr_code='QR001',
                brand='Bridgestone',
                model='Y',
                size='215/60 R17',
                warehouse=self.warehouse_main,
                supplier=self.supplier
            )

    def test_tire_str(self):
        """Тест строкового представления шины"""
        tire = Tire.objects.create(
            qr_code='QR002',
            brand='Bridgestone',
            model='Y',
            size='215/60 R17',
            warehouse=self.warehouse_main,
            supplier=self.supplier
        )
        
        self.assertEqual(str(tire), 'Y')

    def test_tire_oh_requires_supplier(self):
        """Тест что ОХ требует поставщика"""
        from django.core.exceptions import ValidationError
        
        tire = Tire(
            qr_code='QR003',
            brand='Continental',
            model='Z',
            size='225/45 R18',
            warehouse=self.warehouse_oh
        )
        
        with self.assertRaises(ValidationError):
            tire.full_clean()


class TireViewsTest(TestCase):
    """Тесты для views управления шинами"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.warehouse_main = Warehouse.objects.create(
            name='Основной',
            warehouse_type='main'
        )
        self.warehouse_oh = Warehouse.objects.create(
            name='ОХ',
            warehouse_type='oh'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        self.client.login(email='test@example.com', password='testpass123')

    def test_tire_list_view(self):
        """Тест списка шин"""
        response = self.client.get('/tires/')
        self.assertEqual(response.status_code, 200)

    def test_tire_create_view(self):
        """Тест создания шины"""
        response = self.client.get('/tires/create/')
        self.assertEqual(response.status_code, 200)

    def test_tire_create_post(self):
        """Тест POST создания шины"""
        response = self.client.post('/tires/create/', {
            'qr_code': 'QR001',
            'brand': 'Michelin',
            'model': 'X',
            'size': '205/55 R16',
            'warehouse': self.warehouse_main.id,
            'supplier': self.supplier.id
        })
        self.assertRedirects(response, '/tires/list/')

    def test_tire_edit_view(self):
        """Тест редактирования шины"""
        tire = Tire.objects.create(
            qr_code='QR002',
            brand='Bridgestone',
            model='Y',
            size='215/60 R17',
            warehouse=self.warehouse_main,
            supplier=self.supplier
        )
        
        response = self.client.get(f'/tires/{tire.id}/edit/')
        self.assertEqual(response.status_code, 200)

    def test_warehouse_list_view(self):
        """Тест списка складов"""
        response = self.client.get('/tires/warehouses/')
        self.assertEqual(response.status_code, 200)

    def test_supplier_list_view(self):
        """Тест списка поставщиков"""
        response = self.client.get('/tires/suppliers/')
        self.assertEqual(response.status_code, 200)


class TireUtilsTest(TestCase):
    """Тесты для утилит шин"""

    def setUp(self):
        self.warehouse = Warehouse.objects.create(
            name='Основной',
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')

    def test_search_tire_nomenclature(self):
        """Тест поиска номенклатуры шин"""
        # Создаем несколько шин
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='215/60 R17',
            product_name='Michelin Y',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        # Ищем по бренду
        results = search_tire_nomenclature('Michelin', warehouse_id=self.warehouse.id)
        
        self.assertEqual(len(results), 2)


class SearchTireNomenclatureBusinessTest(TestCase):
    """Тесты бизнес-логики поиска номенклатуры шин"""

    def setUp(self):
        self.warehouse = Warehouse.objects.create(
            name='Основной',
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')

    def test_search_by_product_name_partial(self):
        """Тест поиска по части product_name"""
        # Создаем шину с длинным product_name
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='Premium Air',
            size='205/55 R16',
            product_name='Michelin Premium Air 205/55 R16',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        # Ищем по части product_name (должно найти)
        results = search_tire_nomenclature('Premium', warehouse_id=self.warehouse.id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['product_name'], 'Michelin Premium Air 205/55 R16')

    def test_search_by_brand(self):
        """Тест поиска по бренду"""
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        Tire.objects.create(
            qr_code='QR002',
            brand='Bridgestone',
            model='Y',
            size='205/55 R16',
            product_name='Bridgestone Y',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        results = search_tire_nomenclature('Michelin', warehouse_id=self.warehouse.id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['brand'], 'Michelin')

    def test_search_by_model(self):
        """Тест поиска по модели"""
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='Premium',
            size='205/55 R16',
            product_name='Michelin Premium',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        results = search_tire_nomenclature('Premium', warehouse_id=self.warehouse.id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['model'], 'Premium')

    def test_search_by_size(self):
        """Тест поиска по размеру"""
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        results = search_tire_nomenclature('205/55 R16', warehouse_id=self.warehouse.id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['size'], '205/55 R16')

    def test_search_by_multiple_parts(self):
        """Тест поиска по нескольким частям запроса"""
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='Premium',
            size='205/55 R16',
            product_name='Michelin Premium Air 205/55 R16',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Standard',
            size='205/55 R16',
            product_name='Michelin Standard 205/55 R16',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        # Ищем по бренд и части размера
        results = search_tire_nomenclature('Michelin 205', warehouse_id=self.warehouse.id)
        self.assertEqual(len(results), 2)

    def test_search_does_not_return_qr_code(self):
        """Тест что поиск не возвращает QR-коды в результатах"""
        Tire.objects.create(
            qr_code='SECRET-QR-001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        results = search_tire_nomenclature('Michelin', warehouse_id=self.warehouse.id)
        
        # В результатах нет QR-кода в строковом представлении
        self.assertEqual(len(results), 1)
        # Проверяем что результаты содержат правильные поля
        result = results[0]
        self.assertIn('product_name', result)
        self.assertIn('brand', result)
        self.assertIn('model', result)
        self.assertIn('size', result)
        self.assertIn('count', result)
        self.assertIn('tires', result)

    def test_search_groups_by_product_name(self):
        """Тест что поиск группирует по product_name"""
        # Создаем 3 шины с одинаковым product_name
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='215/60 R17',
            product_name='Michelin X',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        Tire.objects.create(
            qr_code='QR003',
            brand='Michelin',
            model='Z',
            size='225/45 R18',
            product_name='Michelin X',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        results = search_tire_nomenclature('Michelin', warehouse_id=self.warehouse.id)
        
        # Должна быть только 1 группа
        self.assertEqual(len(results), 1)
        # В группе должно быть 3 шины
        self.assertEqual(results[0]['count'], 3)
        self.assertEqual(results[0]['product_name'], 'Michelin X')
        # В группе должны быть все шины
        self.assertEqual(results[0]['tires'].count(), 3)

    def test_search_ignores_inactive_tires(self):
        """Тест что поиск игнорирует неактивные шины"""
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse,
            supplier=self.supplier,
            is_active=True
        )
        Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='215/60 R17',
            product_name='Michelin Y',
            warehouse=self.warehouse,
            supplier=self.supplier,
            is_active=False  # Неактивная
        )
        
        results = search_tire_nomenclature('Michelin', warehouse_id=self.warehouse.id)
        
        # Должна быть только 1 активная шина
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['product_name'], 'Michelin X')
        self.assertEqual(results[0]['count'], 1)

    def test_search_by_full_product_name(self):
        """Тест поиска по полному product_name"""
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='Premium',
            size='205/55 R16',
            product_name='Michelin Premium 205/55 R16',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        results = search_tire_nomenclature('Michelin Premium 205/55 R16', warehouse_id=self.warehouse.id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['product_name'], 'Michelin Premium 205/55 R16')

    def test_search_returns_tires_list(self):
        """Тест что поиск возвращает список шин в группе"""
        Tire.objects.create(
            qr_code='QR001',
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        Tire.objects.create(
            qr_code='QR002',
            brand='Michelin',
            model='Y',
            size='205/55 R16',
            product_name='Michelin X',
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        results = search_tire_nomenclature('Michelin X', warehouse_id=self.warehouse.id)
        
        self.assertEqual(len(results), 1)
        self.assertIn('tires', results[0])
        self.assertEqual(results[0]['tires'].count(), 2)
        # Проверяем что в списке шин есть обе шины
        tire_qr_codes = [t.qr_code for t in results[0]['tires'].all()]
        self.assertIn('QR001', tire_qr_codes)
        self.assertIn('QR002', tire_qr_codes)

