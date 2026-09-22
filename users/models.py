#############################################################################################
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Кастомный менеджер для создания пользователей с email как основным идентификатором.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.is_active = extra_fields.get('is_active', True)  # По умолчанию активен
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class UserRoles(models.TextChoices):
    MANAGER = 'manager', _('Начальник склада')
    STOREKEEPER = 'storekeeper', _('Кладовщик')


class User(AbstractUser):
    """
    Расширенная модель пользователя.
    Поле username удалено. Используется email как основной идентификатор.
    """

    username = None
    email = models.EmailField("email address", unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=False)

    # Новые поля для ролей и площадок
    platform = models.ForeignKey(
        'tires.Platform',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('Площадка')
    )
    role = models.CharField(
        max_length=20,
        choices=UserRoles.choices,
        default=UserRoles.STOREKEEPER,
        verbose_name=_('Роль')
    )

    objects = UserManager()  # подключаем кастомный менеджер

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_manager(self):
        return self.role == UserRoles.MANAGER

    @property
    def is_storekeeper(self):
        return self.role == UserRoles.STOREKEEPER

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["email"]
        db_table = "user"


#############################################################################################
