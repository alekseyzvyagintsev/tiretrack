"""Тесты для новых warehouse views (homepage, document_codes, code_card, counters_api)."""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse

from tires.models import Platform, Warehouse, TireNomenclature, TireCode, Supplier
from warehouse.models import Document, DocumentItem, DocType
from warehouse.services import DocumentService

User = get_user_model()


class UniqueCodeCounter:
    """Генератор уникальных QR-кодов."""
    def __init__(self):
        self.counter = 0
    
    def next(self):
        self.counter += 1
        return f'QR-VIEW-{self.counter:04d}'


class HomepageViewTest(TestCase):
    """Тесты для дашборда (homepage)."""

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
        self.code_counter = UniqueCodeCounter()

    def test_homepage_returns_200(self):
        """Тест что homepage возвращает 200"""
        response = self.client.get(reverse('warehouse:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'warehouse/home.html')

    def test_homepage_context_data(self):
        """Тест что homepage передаёт все необходимые данные"""
        # Создаём TireCode для подсчёта
        nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        TireCode.objects.create(
            qr_code=self.code_counter.next(),
            nomenclature=nomenclature,
            warehouse=self.warehouse
        )

        response = self.client.get(reverse('warehouse:home'))

        self.assertEqual(response.context['total_codes'], 1)
        self.assertEqual(response.context['active_codes'], 1)
        self.assertEqual(response.context['used_codes'], 0)
        self.assertIn('recent_documents', response.context)
        self.assertIn('warehouses', response.context)

    def test_homepage_with_posted_document(self):
        """Тест что homepage считает posted документы"""
        doc_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True
        )
        nomenclature = TireNomenclature.objects.create(
            brand='TestBrand',
            model='TestModel',
            size='295/80R22.5'
        )
        document = Document.objects.create(
            doc_type=doc_type,
            author=self.user,
            source_platform=self.platform,
            source_warehouse=self.warehouse,
            status='saved'
        )
        # Добавляем DocumentItem
        DocumentItem.objects.create(
            document=document,
            nomenclature=nomenclature,
            quantity=1
        )
        # Создаём TireCode и привязываем
        tire_code = TireCode.objects.create(
            qr_code=self.code_counter.next(),
            nomenclature=nomenclature,
            warehouse=self.warehouse
        )
        document.tire_codes.add(tire_code)
        # Проводим документ через сервис
        DocumentService.post_document(document)

        response = self.client.get(reverse('warehouse:home'))

        self.assertEqual(response.context['posted_count'], 1)


class DocumentListViewTest(TestCase):
    """Тесты для списка документов."""

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
        self.code_counter = UniqueCodeCounter()

    def test_document_list_returns_200(self):
        """Тест что document_list возвращает 200"""
        response = self.client.get(reverse('warehouse:document-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'warehouse/document_list.html')

    def test_document_list_context(self):
        """Тест что document_list передаёт статистику"""
        doc_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True
        )
        Document.objects.create(
            doc_type=doc_type,
            author=self.user,
            source_platform=self.platform,
            status='saved'
        )

        response = self.client.get(reverse('warehouse:document-list'))

        self.assertIn('stats', response.context)
        self.assertIn('doc_types', response.context)
        self.assertIn('platforms', response.context)
        self.assertEqual(response.context['stats']['saved'], 1)


class DocumentCodesViewTest(TestCase):
    """Тесты для экрана кодов (document_codes)."""

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
        self.nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        self.doc_type = DocType.objects.create(
            code='writeoff',
            name='Списание',
            prefix='СП',
            is_active=True
        )
        self.code_counter = UniqueCodeCounter()
        self.document = Document.objects.create(
            doc_type=self.doc_type,
            author=self.user,
            source_platform=self.platform,
            source_warehouse=self.warehouse,
            status='saved'
        )
        # Создаём DocumentItem
        DocumentItem.objects.create(
            document=self.document,
            nomenclature=self.nomenclature,
            quantity=1
        )
        # Создаём TireCode и привязываем к документу
        self.tire_code = TireCode.objects.create(
            qr_code=self.code_counter.next(),
            nomenclature=self.nomenclature,
            warehouse=self.warehouse
        )
        self.document.tire_codes.add(self.tire_code)
        # Проводим документ через сервис
        DocumentService.post_document(self.document)

        self.client.login(email='test@example.com', password='testpass123')

    def test_document_codes_returns_200(self):
        """Тест что document_codes возвращает 200 для posted документа"""
        response = self.client.get(
            reverse('warehouse:document-codes', args=[self.document.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'warehouse/document_codes.html')

    def test_document_codes_forbidden_for_non_posted(self):
        """Тест что document_codes запрещён для не-posted документов"""
        draft_doc = Document.objects.create(
            doc_type=self.doc_type,
            author=self.user,
            source_platform=self.platform,
            status='draft'
        )
        response = self.client.get(
            reverse('warehouse:document-codes', args=[draft_doc.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_document_codes_pagination(self):
        """Тест что document_codes поддерживает пагинацию"""
        # Создаём 100 кодов
        for i in range(100):
            code = TireCode.objects.create(
                qr_code=self.code_counter.next(),
                nomenclature=self.nomenclature,
                warehouse=self.warehouse
            )
            self.document.tire_codes.add(code)

        response = self.client.get(
            reverse('warehouse:document-codes', args=[self.document.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        # По 50 кодов на странице
        self.assertEqual(len(response.context['page_obj']), 50)


class CodeCardViewTest(TestCase):
    """Тесты для карточки кода (code_card)."""

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
        self.nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        self.code_counter = UniqueCodeCounter()
        self.tire_code = TireCode.objects.create(
            qr_code=self.code_counter.next(),
            nomenclature=self.nomenclature,
            warehouse=self.warehouse
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_code_card_returns_200(self):
        """Тест что code_card возвращает 200"""
        response = self.client.get(
            reverse('warehouse:code-card', args=[self.tire_code.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'warehouse/code_card.html')

    def test_code_card_context(self):
        """Тест что code_card передаёт code и qr_image_data"""
        response = self.client.get(
            reverse('warehouse:code-card', args=[self.tire_code.pk])
        )

        self.assertEqual(response.context['code'], self.tire_code)
        self.assertIn('qr_image_data', response.context)

    def test_code_card_404_for_non_existent(self):
        """Тест что code_card возвращает 404 для несуществующего кода"""
        response = self.client.get(
            reverse('warehouse:code-card', args=[99999])
        )
        self.assertEqual(response.status_code, 404)


class CountersAPITest(TestCase):
    """Тесты для API счётчиков."""

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
        self.nomenclature = TireNomenclature.objects.create(
            brand='Michelin',
            model='X',
            size='205/55 R16'
        )
        self.code_counter = UniqueCodeCounter()
        self.tire_code = TireCode.objects.create(
            qr_code=self.code_counter.next(),
            nomenclature=self.nomenclature,
            warehouse=self.warehouse
        )
        self.client.login(email='test@example.com', password='testpass123')

    def test_counters_api_returns_active_count(self):
        """Тест что counters_api возвращает количество активных кодов"""
        response = self.client.get(reverse('warehouse:counters-api'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['active'], 1)

    def test_counters_api_with_warehouse_filter(self):
        """Тест что counters_api поддерживает фильтр по складу"""
        response = self.client.get(
            reverse('warehouse:counters-api'),
            {'warehouse': self.warehouse.pk}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['active'], 1)

    def test_counters_api_with_nomenclature_filter(self):
        """Тест что counters_api поддерживает фильтр по номенклатуре"""
        response = self.client.get(
            reverse('warehouse:counters-api'),
            {'nomenclature': self.nomenclature.pk}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['active'], 1)

    def test_counters_api_excludes_used_codes(self):
        """Тест что counters_api не считает использованные коды"""
        self.tire_code.is_active = False
        self.tire_code.is_used = True
        self.tire_code.save()

        response = self.client.get(reverse('warehouse:counters-api'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['active'], 0)
