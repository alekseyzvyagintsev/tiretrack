from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from tires.models import Warehouse, Supplier, TireNomenclature, TireCode, Platform


class WarehouseModelTest(TestCase):
    """Тесты для модели Warehouse"""

    def setUp(self):
        self.platform = Platform.objects.create(name='Test Platform')

    def test_create_warehouse(self):
        """Тест создания склада"""
        warehouse = Warehouse.objects.create(
            name='Основной склад',
            warehouse_type='main',
            platform=self.platform
        )
        
        self.assertEqual(warehouse.name, 'Основной склад')
        self.assertEqual(warehouse.warehouse_type, 'main')
        self.assertEqual(warehouse.platform, self.platform)

    def test_warehouse_unique_name_per_platform(self):
        """Тест уникальности имени склада на площадке"""
        Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main',
            platform=self.platform
        )
        
        with self.assertRaises(Exception):
            Warehouse.objects.create(
                name='Склад 1',
                warehouse_type='main',
                platform=self.platform
            )

    def test_warehouse_str(self):
        """Тест строкового представления склада"""
        warehouse = Warehouse.objects.create(
            name='Склад 2',
            warehouse_type='oh',
            platform=self.platform
        )
        
        self.assertIn('Склад 2', str(warehouse))


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


class TireNomenclatureModelTest(TestCase):
    """Тесты для модели TireNomenclature"""

    def test_create_nomenclature(self):
        """Тест создания номенклатуры"""
        nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X'
        )
        
        self.assertEqual(nomenclature.brand, 'Michelin')
        self.assertEqual(nomenclature.model, 'X')
        self.assertEqual(nomenclature.size, '205/55 R16')
        self.assertEqual(nomenclature.product_name, 'Michelin X')

    def test_nomenclature_unique_constraint(self):
        """Тест уникальности brand+model+size"""
        TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        
        with self.assertRaises(Exception):
            TireNomenclature.objects.create(
                brand='Michelin',
                model='X',
                size='205/55 R16'
            )

    def test_nomenclature_display_name_with_product_name(self):
        """Тест отображаемого имени с product_name"""
        nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X'
        )
        
        self.assertEqual(nomenclature.display_name(), 'Michelin X')

    def test_nomenclature_display_name_fallback(self):
        """Тест отображаемого имени fallback"""
        nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        
        self.assertEqual(nomenclature.display_name(), '205/55 R16 Michelin X')


class TireCodeModelTest(TestCase):
    """Тесты для модели TireCode"""

    def setUp(self):
        self.platform = Platform.objects.create(name='Test Platform')
        self.warehouse = Warehouse.objects.create(
            name='Основной',
            warehouse_type='main',
            platform=self.platform
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        self.nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X'
        )

    def test_create_tire_code(self):
        """Тест создания TireCode"""
        tire_code = TireCode.objects.create(
            qr_code='QR001',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        self.assertEqual(tire_code.qr_code, 'QR001')
        self.assertEqual(tire_code.nomenclature, self.nomenclature)
        self.assertTrue(tire_code.is_active)
        self.assertFalse(tire_code.is_used)

    def test_tire_code_unique_qr_code(self):
        """Тест уникальности QR-кода"""
        TireCode.objects.create(
            qr_code='QR001',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse
        )
        
        with self.assertRaises(Exception):
            TireCode.objects.create(
                qr_code='QR001',
                nomenclature=self.nomenclature,
                warehouse=self.warehouse
            )

    def test_tire_code_str(self):
        """Тест строкового представления"""
        tire_code = TireCode.objects.create(
            qr_code='QR002',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse
        )
        
        self.assertEqual(str(tire_code), 'QR002')

    def test_mark_used(self):
        """Тест пометки как использованный"""
        tire_code = TireCode.objects.create(
            qr_code='QR003',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse
        )
        
        tire_code.mark_used(None)
        
        self.assertTrue(tire_code.is_used)
        self.assertFalse(tire_code.is_active)
        self.assertIsNotNone(tire_code.used_at)

    def test_unmark_used(self):
        """Тест снятия пометки использования"""
        tire_code = TireCode.objects.create(
            qr_code='QR004',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse
        )
        tire_code.mark_used(None)
        tire_code.unmark_used()
        
        self.assertFalse(tire_code.is_used)
        self.assertTrue(tire_code.is_active)
        self.assertIsNone(tire_code.used_at)
        self.assertIsNone(tire_code.document)


class TireCodeViewsTest(TestCase):
    """Тесты для views TireCode"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.platform = Platform.objects.create(name='Test Platform')
        self.warehouse = Warehouse.objects.create(
            name='Основной',
            warehouse_type='main',
            platform=self.platform
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        self.nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        self.tire_code = TireCode.objects.create(
            qr_code='QR001',
            nomenclature=self.nomenclature,
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_tire_code_list_view(self):
        """Тест списка TireCode"""
        response = self.client.get('/tires/')
        self.assertEqual(response.status_code, 200)

    def test_tire_code_search_view(self):
        """Тест поиска TireCode"""
        response = self.client.get('/tires/search/')
        self.assertEqual(response.status_code, 200)

    def test_warehouse_list_view(self):
        """Тест списка складов"""
        response = self.client.get('/tires/warehouses/')
        self.assertEqual(response.status_code, 200)

    def test_supplier_list_view(self):
        """Тест списка поставщиков"""
        response = self.client.get('/tires/suppliers/')
        self.assertEqual(response.status_code, 200)


class TireCodeUtilsTest(TestCase):
    """Тесты для утилит TireCode"""

    def setUp(self):
        self.platform = Platform.objects.create(name='Test Platform')
        self.warehouse = Warehouse.objects.create(
            name='Основной',
            warehouse_type='main',
            platform=self.platform
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')

    def test_create_nomenclature_and_tire_code(self):
        """Тест создания номенклатуры и TireCode"""
        nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16',
            product_name='Michelin X'
        )
        
        tire_code = TireCode.objects.create(
            qr_code='QR001',
            nomenclature=nomenclature,
            warehouse=self.warehouse,
            supplier=self.supplier
        )
        
        self.assertEqual(tire_code.nomenclature.brand, 'Michelin')
        self.assertTrue(tire_code.is_active)
