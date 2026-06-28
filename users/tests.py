from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

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
