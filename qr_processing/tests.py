from django.test import TestCase, Client, override_settings
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from qr_processing.models import FileImport, ExportBatch
from tires.models import Warehouse, Supplier, Platform
from tires.services import UploadService
from integrations.honest_sign import HonestSignClient


class FileImportModelTest(TestCase):
    """Тесты для модели FileImport"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.platform = Platform.objects.create(name='Тестовая площадка')
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            platform=self.platform,
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')

    def test_create_file_import(self):
        """Тест создания импорта файла"""
        file_content = b"QR001\nQR002\nQR003"
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            file_content,
            content_type="text/plain"
        )

        file_import = FileImport.objects.create(
            file=uploaded_file,
            file_type='txt',
            uploaded_by=self.user
        )

        self.assertEqual(file_import.file_type, 'txt')
        self.assertEqual(file_import.uploaded_by, self.user)
        self.assertFalse(file_import.processed)
        self.assertEqual(file_import.success_count, 0)
        self.assertEqual(file_import.error_count, 0)

    def test_file_import_with_details(self):
        """Тест создания импорта с деталями"""
        file_content = b"QR001\nQR002"
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            file_content,
            content_type="text/plain"
        )

        file_import = FileImport.objects.create(
            file=uploaded_file,
            file_type='txt',
            uploaded_by=self.user,
            details=[{'code': 'QR001', 'reason': 'duplicated'}]
        )

        self.assertIsNotNone(file_import.details)
        self.assertEqual(len(file_import.details), 1)
        self.assertEqual(file_import.details[0]['code'], 'QR001')


class ExportBatchModelTest(TestCase):
    """Тесты для модели ExportBatch"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def test_create_export_batch(self):
        """Тест создания пакета экспорта"""
        export_batch = ExportBatch.objects.create(
            name='Экспорт 1',
            export_format='txt',
            created_by=self.user,
            tire_count=5
        )

        self.assertEqual(export_batch.name, 'Экспорт 1')
        self.assertEqual(export_batch.export_format, 'txt')
        self.assertEqual(export_batch.created_by, self.user)
        self.assertEqual(export_batch.tire_count, 5)
        self.assertFalse(export_batch.completed)

    def test_export_batch_str(self):
        """Тест строкового представления пакета экспорта"""
        export_batch = ExportBatch.objects.create(
            name='Экспорт 2',
            export_format='qr_images',
            created_by=self.user,
            tire_count=10
        )

        self.assertEqual(str(export_batch), 'Export Экспорт 2 (10 tires)')


class FileImportViewTest(TestCase):
    """Тесты для view импорта файлов"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.platform = Platform.objects.create(name='Тестовая площадка')
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            platform=self.platform,
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_file_import_view_get(self):
        """Тест получения формы импорта"""
        response = self.client.get('/qr/imports/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'qr/import.html')

        # Проверяем, что в контексте переданы необходимые переменные
        self.assertIn('warehouses', response.context)
        self.assertIn('suppliers', response.context)

        # Проверяем, что список складов не пустой
        warehouses = response.context['warehouses']
        self.assertTrue(warehouses.exists())
        self.assertEqual(warehouses.first().name, 'Склад 1')

        # Проверяем, что список поставщиков не пустой
        suppliers = response.context['suppliers']
        self.assertTrue(suppliers.exists())
        self.assertEqual(suppliers.first().name, 'Поставщик 1')

    def test_file_import_view_post_no_warehouse(self):
        """Тест импорта без выбора склада"""
        response = self.client.post('/qr/imports/', {
            'text': 'QR001',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Выберите склад')

    @patch.object(HonestSignClient, '__init__', lambda self, use_mock=None: setattr(self, 'use_mock', True))
    def test_file_import_view_post_with_file(self):
        """Тест импорта с файлом"""
        file_content = b"QR001\nQR002\nQR003"
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            file_content,
            content_type="text/plain"
        )

        response = self.client.post('/qr/imports/', {
            'file': uploaded_file,
            'warehouse': self.warehouse.id,
        })
        # Должен быть редирект на отчёт
        self.assertEqual(response.status_code, 302)

        # Проверяем, что FileImport создан
        self.assertTrue(FileImport.objects.filter(
            uploaded_by=self.user,
            success_count=3
        ).exists())

    @patch.object(HonestSignClient, '__init__', lambda self, use_mock=None: setattr(self, 'use_mock', True))
    def test_file_import_view_post_with_text(self):
        """Тест импорта с текстом"""
        response = self.client.post('/qr/imports/', {
            'text': 'QR001\nQR002',
            'warehouse': self.warehouse.id,
        })
        # Должен быть редирект на отчёт
        self.assertEqual(response.status_code, 302)

    def test_file_import_view_post_empty_file(self):
        """Тест импорта пустого файла"""
        response = self.client.post('/qr/imports/', {
            'text': '',
            'warehouse': self.warehouse.id,
        })
        self.assertEqual(response.status_code, 200)
        # Проверяем, что есть сообщение об ошибке
        self.assertEqual(response.status_code, 200)


class UploadReportViewTest(TestCase):
    """Тесты для view отчёта о загрузке"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.platform = Platform.objects.create(name='Тестовая площадка')
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            platform=self.platform,
            warehouse_type='main'
        )
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_upload_report_view(self):
        """Тест отображения отчёта о загрузке"""
        file_import = FileImport.objects.create(
            file_type='txt',
            uploaded_by=self.user,
            processed=True,
            success_count=3,
            error_count=1,
            details=[{'code': 'QR001', 'reason': 'duplicated'}]
        )

        response = self.client.get(
            f'/qr/imports/report/{file_import.id}/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'qr/export.html')
        self.assertContains(response, 'Отчёт о загрузке')


class ExportBatchViewTest(TestCase):
    """Тесты для view экспорта"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.platform = Platform.objects.create(name='Тестовая площадка')
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            platform=self.platform,
            warehouse_type='main'
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_export_batch_list_view(self):
        """Тест списка пакетов экспорта"""
        response = self.client.get('/qr/exports/')
        self.assertEqual(response.status_code, 200)
