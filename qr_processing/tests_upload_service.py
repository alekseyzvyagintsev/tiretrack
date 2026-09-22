"""Тесты для UploadService и HonestSignClient."""
from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model

from tires.models import Platform, Warehouse, TireNomenclature, TireCode, Supplier
from tires.services import UploadService, UploadReport
from integrations.honest_sign import HonestSignClient

User = get_user_model()


class HonestSignClientTest(TestCase):
    """Тесты для HonestSignClient."""

    def test_honest_sign_client_mock_mode(self):
        """Тест что клиент работает в мок-режиме"""
        client = HonestSignClient(use_mock=True)
        
        result = client.get_code_info('TEST-QR-001')
        
        self.assertIsNotNone(result)
        self.assertIn('brand', result)
        self.assertIn('model', result)
        self.assertIn('size', result)

    @patch.object(HonestSignClient, '__init__', lambda self, use_mock=None: setattr(self, 'use_mock', False))
    def test_honest_sign_client_real_api_error(self):
        """Тест что клиент обрабатывает ошибку API"""
        with patch('nechestniy_znak.Crpt') as mock_crpt:
            mock_crpt.return_value.infoFromDataMatrix.side_effect = Exception('API Error')
            
            client = HonestSignClient()
            result = client.get_code_info('REAL-QR-001')
            
            self.assertIsNone(result)

    @patch.object(HonestSignClient, '__init__', lambda self, use_mock=None: setattr(self, 'use_mock', False))
    def test_honest_sign_client_empty_response(self):
        """Тест что клиент обрабатывает пустой ответ"""
        with patch('nechestniy_znak.Crpt') as mock_crpt:
            mock_crpt.return_value.infoFromDataMatrix.return_value = None
            
            client = HonestSignClient()
            result = client.get_code_info('EMPTY-QR-001')
            
            self.assertIsNone(result)

    @patch.object(HonestSignClient, '__init__', lambda self, use_mock=None: setattr(self, 'use_mock', False))
    def test_honest_sign_client_parse_response(self):
        """Тест парсинга ответа от Честного знака"""
        with patch('nechestniy_znak.Crpt') as mock_crpt:
            mock_crpt.return_value.infoFromDataMatrix.return_value = {
                'brand': 'Michelin',
                'model': 'X',
                'size': '205/55 R16',
                'product_name': 'Michelin X 205/55 R16'
            }
            
            client = HonestSignClient()
            result = client.get_code_info('PARSE-QR-001')
            
            self.assertIsNotNone(result)
            self.assertEqual(result['brand'], 'Michelin')
            self.assertEqual(result['model'], 'X')
            self.assertEqual(result['size'], '205/55 R16')
            self.assertEqual(result['product_name'], 'Michelin X 205/55 R16')


class UploadServiceTest(TestCase):
    """Тесты для UploadService."""

    def setUp(self):
        self.platform = Platform.objects.create(name='Test Platform')
        self.warehouse = Warehouse.objects.create(
            name='Склад 1',
            warehouse_type='main',
            platform=self.platform
        )
        self.supplier = Supplier.objects.create(name='Поставщик 1')

    @patch.object(HonestSignClient, '__init__', lambda self, use_mock=None: setattr(self, 'use_mock', True))
    def test_upload_service_creates_tire_codes(self):
        """Тест что UploadService создаёт TireCode"""
        service = UploadService(warehouse=self.warehouse, supplier=self.supplier)
        
        lines = ['QR-UPLOAD-001', 'QR-UPLOAD-002', 'QR-UPLOAD-003']
        report = service.upload(lines)
        
        self.assertEqual(report.total_lines, 3)
        self.assertEqual(report.created, 3)
        self.assertEqual(report.duplicates, 0)
        self.assertEqual(TireCode.objects.count(), 3)

    @patch.object(HonestSignClient, '__init__', lambda self, use_mock=None: setattr(self, 'use_mock', True))
    def test_upload_service_detects_duplicates(self):
        """Тест что UploadService обнаруживает дубликаты"""
        # Создаём первый код
        service1 = UploadService(warehouse=self.warehouse, supplier=self.supplier)
        service1.upload(['QR-DUP-001'])
        
        # Пытаемся загрузить тот же код
        service2 = UploadService(warehouse=self.warehouse, supplier=self.supplier)
        report = service2.upload(['QR-DUP-001'])
        
        self.assertEqual(report.duplicates, 1)
        self.assertEqual(report.created, 0)

    @patch.object(HonestSignClient, '__init__', lambda self, use_mock=None: setattr(self, 'use_mock', True))
    def test_upload_service_creates_nomenclature(self):
        """Тест что UploadService создаёт TireNomenclature"""
        service = UploadService(warehouse=self.warehouse, supplier=self.supplier)
        
        service.upload(['QR-NOM-001'])
        
        nomenclature = TireNomenclature.objects.first()
        self.assertIsNotNone(nomenclature)
        self.assertIn('MockBrand', nomenclature.brand)
        self.assertIn('MockModel', nomenclature.model)

    @patch.object(HonestSignClient, '__init__', lambda self, use_mock=None: setattr(self, 'use_mock', True))
    def test_upload_service_skips_empty_lines(self):
        """Тест что UploadService пропускает пустые строки"""
        service = UploadService(warehouse=self.warehouse, supplier=self.supplier)
        
        lines = ['QR-001', '', 'QR-002', '   ', 'QR-003']
        report = service.upload(lines)
        
        self.assertEqual(report.created, 3)

    @patch.object(HonestSignClient, '__init__', lambda self, use_mock=None: setattr(self, 'use_mock', True))
    def test_upload_report_summary(self):
        """Тест что UploadReport возвращает summary"""
        service = UploadService(warehouse=self.warehouse, supplier=self.supplier)
        
        service.upload(['QR-SUM-001', 'QR-SUM-002'])
        
        summary = service.report.summary
        self.assertEqual(summary['total_lines'], 2)
        self.assertEqual(summary['created'], 2)

    @patch('integrations.honest_sign.HonestSignClient')
    def test_upload_service_with_honest_sign_error(self, mock_client_class):
        """Тест что UploadService обрабатывает ошибку Честного знака"""
        mock_client = MagicMock()
        mock_client.get_code_info.side_effect = Exception('API Error')
        mock_client_class.return_value = mock_client
        
        service = UploadService(warehouse=self.warehouse, supplier=self.supplier)
        report = service.upload(['QR-ERR-001'])
        
        self.assertEqual(report.honest_sign_errors, 1)
        self.assertEqual(report.created, 0)

    @patch('integrations.honest_sign.HonestSignClient')
    def test_upload_service_details_in_report(self, mock_client_class):
        """Тест что UploadReport содержит details"""
        mock_client = MagicMock()
        mock_client.get_code_info.return_value = {
            'brand': 'TestBrand',
            'model': 'TestModel',
            'size': '295/80R22.5'
        }
        mock_client_class.return_value = mock_client
        
        service = UploadService(warehouse=self.warehouse, supplier=self.supplier)
        service.upload(['QR-DET-001'])
        
        self.assertTrue(len(service.report.details) > 0)
        self.assertIn('code', service.report.details[0])
        self.assertIn('reason', service.report.details[0])


class UploadReportTest(TestCase):
    """Тесты для UploadReport."""

    def test_upload_report_default_values(self):
        """Тест значения по умолчанию для UploadReport"""
        report = UploadReport()
        
        self.assertEqual(report.total_lines, 0)
        self.assertEqual(report.created, 0)
        self.assertEqual(report.duplicates, 0)
        self.assertEqual(report.unrecognized, 0)
        self.assertEqual(report.honest_sign_errors, 0)

    def test_upload_report_summary(self):
        """Тест что summary возвращает все поля"""
        report = UploadReport(
            total_lines=10,
            created=5,
            duplicates=3,
            unrecognized=1,
            honest_sign_errors=1
        )
        
        summary = report.summary
        
        self.assertEqual(summary['total_lines'], 10)
        self.assertEqual(summary['created'], 5)
        self.assertEqual(summary['duplicates'], 3)
        self.assertEqual(summary['unrecognized'], 1)
        self.assertEqual(summary['honest_sign_errors'], 1)
