from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from tires.models import Tire, Warehouse, Supplier

# Получаем действующую модель пользователя Django в данном проекте (users.models.User)
User = get_user_model()


class UsersViewsTestCase(TestCase):
    """Набор тестов для Django views приложения users."""

    def setUp(self):
        admin_group, created = Group.objects.get_or_create(name="Администратор")
        # Создаем пользователей для тестов
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="qwer1234", is_superuser=True, is_staff=True, is_active=True
        )
        self.admin_user.groups.add(admin_group)

        self.regular_user = User.objects.create_user(email="user@example.com", password="qwer1234", is_active=True)
        self.other_user = User.objects.create_user(email="other@example.com", password="qwer1234", is_active=True)

    def test_login_view_get(self):
        """Тестирует получение формы логина"""
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')

    def test_login_view_post_success(self):
        """Тестирует успешный логин"""
        response = self.client.post(reverse('users:login'), {
            'email': 'user@example.com',
            'password': 'qwer1234'
        })
        self.assertRedirects(response, reverse('tires:warehouse-list'))
        # Проверяем, что пользователь авторизован
        response = self.client.get(reverse('tires:warehouse-list'))
        self.assertEqual(response.status_code, 200)

    def test_login_view_post_invalid_password(self):
        """Тестирует логин с неверным паролем"""
        response = self.client.post(reverse('users:login'), {
            'email': 'user@example.com',
            'password': 'wrongpassword'
        })
        # Проверяем, что возвращается на форму логина с сообщением об ошибке
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login'))

    def test_login_view_post_user_not_exists(self):
        """Тестирует логин с несуществующим пользователем"""
        response = self.client.post(reverse('users:login'), {
            'email': 'nonexistent@example.com',
            'password': 'qwer1234'
        })
        self.assertRedirects(response, reverse('users:login'))

    def test_logout_view(self):
        """Тестирует выход из системы"""
        # Входим через client.login()
        self.client.login(email='user@example.com', password='qwer1234')
        
        response = self.client.get(reverse('users:logout'))
        # Проверяем, что происходит редирект на логин после логаута
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login'))


class PublicAccessTestCase(TestCase):
    """Набор тестов для проверки доступа без авторизации."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="qwer1234", is_superuser=True, is_staff=True, is_active=True
        )

    def test_homepage_accessible_without_auth(self):
        """Домашняя страница доступна без авторизации"""
        response = self.client.get(reverse('tires:homepage'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tires/home.html')

    def test_warehouse_list_requires_auth(self):
        """Список складов требует авторизации"""
        response = self.client.get(reverse('tires:warehouse-list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/users/login/?next=/tires/warehouses/')

    def test_warehouse_create_requires_auth(self):
        """Создание склада требует авторизации"""
        response = self.client.get(reverse('tires:warehouse-create'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/users/login/?next=/tires/warehouses/create/')

    def test_warehouse_edit_requires_auth(self):
        """Редактирование склада требует авторизации"""
        warehouse = Warehouse.objects.create(name='Тестовый склад', warehouse_type='main')
        response = self.client.get(reverse('tires:warehouse-edit', kwargs={'pk': warehouse.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/users/login/?next=/tires/warehouses/{warehouse.pk}/edit/')

    def test_warehouse_delete_requires_auth(self):
        """Удаление склада требует авторизации"""
        warehouse = Warehouse.objects.create(name='Тестовый склад', warehouse_type='main')
        response = self.client.get(reverse('tires:warehouse-delete', kwargs={'pk': warehouse.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/users/login/?next=/tires/warehouses/{warehouse.pk}/delete/')

    def test_supplier_list_requires_auth(self):
        """Список поставщиков требует авторизации"""
        response = self.client.get(reverse('tires:supplier-list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/users/login/?next=/tires/suppliers/')

    def test_supplier_create_requires_auth(self):
        """Создание поставщика требует авторизации"""
        response = self.client.get(reverse('tires:supplier-create'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/users/login/?next=/tires/suppliers/create/')

    def test_supplier_edit_requires_auth(self):
        """Редактирование поставщика требует авторизации"""
        supplier = Supplier.objects.create(name='Тестовый поставщик')
        response = self.client.get(reverse('tires:supplier-edit', kwargs={'pk': supplier.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/users/login/?next=/tires/suppliers/{supplier.pk}/edit/')

    def test_supplier_delete_requires_auth(self):
        """Удаление поставщика требует авторизации"""
        supplier = Supplier.objects.create(name='Тестовый поставщик')
        response = self.client.get(reverse('tires:supplier-delete', kwargs={'pk': supplier.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/users/login/?next=/tires/suppliers/{supplier.pk}/delete/')

    def test_tire_list_requires_auth(self):
        """Список шин требует авторизации"""
        response = self.client.get(reverse('tires:tire-list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/users/login/?next=/tires/list/')

    def test_tire_create_requires_auth(self):
        """Создание шины требует авторизации"""
        response = self.client.get(reverse('tires:tire-create'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/users/login/?next=/tires/create/')

    def test_tire_edit_requires_auth(self):
        """Редактирование шины требует авторизации"""
        warehouse = Warehouse.objects.create(name='Тестовый склад', warehouse_type='main')
        tire = Tire.objects.create(qr_code='TEST001', brand='Test', model='Model', size='195/65R15', warehouse=warehouse)
        response = self.client.get(reverse('tires:tire-edit', kwargs={'pk': tire.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/users/login/?next=/tires/{tire.pk}/edit/')

    def test_tire_delete_requires_auth(self):
        """Удаление шины требует авторизации"""
        warehouse = Warehouse.objects.create(name='Тестовый склад', warehouse_type='main')
        tire = Tire.objects.create(qr_code='TEST002', brand='Test', model='Model', size='195/65R15', warehouse=warehouse)
        response = self.client.get(reverse('tires:tire-delete', kwargs={'pk': tire.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/users/login/?next=/tires/{tire.pk}/delete/')



