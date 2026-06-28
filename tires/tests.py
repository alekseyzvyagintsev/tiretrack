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
        self.assertRedirects(response, '/tires/')

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
