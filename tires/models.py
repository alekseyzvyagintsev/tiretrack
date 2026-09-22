from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from users.models import User


class Platform(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Название площадки'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))

    class Meta:
        verbose_name = _('Площадка')
        verbose_name_plural = _('Площадки')
        ordering = ['name']

    def __str__(self):
        return self.name


class WarehouseType(models.TextChoices):
    MAIN = 'main', _('Основной склад')
    OH = 'oh', _('Ответственное хранение')


class Warehouse(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Название склада'))
    platform = models.ForeignKey(
        Platform,
        on_delete=models.CASCADE,
        related_name='warehouses',
        verbose_name=_('Площадка'),
        null=True,
        blank=True
    )
    warehouse_type = models.CharField(
        max_length=20,
        choices=WarehouseType.choices,
        default=WarehouseType.MAIN,
        verbose_name=_('Тип склада')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))

    class Meta:
        verbose_name = _('Склад')
        verbose_name_plural = _('Склады')
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'platform'],
                name='unique_warehouse_per_platform'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.platform})" if self.platform else self.name


class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Поставщик')
        verbose_name_plural = _('Поставщики')
        ordering = ['name']

    def __str__(self):
        return self.name


class TireNomenclature(models.Model):
    brand = models.CharField(max_length=100, verbose_name=_('Бренд'))
    model = models.CharField(max_length=100, verbose_name=_('Модель'))
    size = models.CharField(max_length=50, verbose_name=_('Размер'))
    product_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('Наименование')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Активна'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))

    class Meta:
        verbose_name = _('Номенклатура')
        verbose_name_plural = _('Номенклатура')
        ordering = ['brand', 'model', 'size']
        constraints = [
            models.UniqueConstraint(
                fields=['brand', 'model', 'size'],
                name='unique_nomenclature'
            ),
        ]

    def __str__(self):
        return self.display_name

    def display_name(self):
        """Отображаемое имя: product_name или fallback brand+model+size"""
        if self.product_name:
            return self.product_name
        return f"{self.size} {self.brand} {self.model}"
    display_name.short_description = _('Название')


class TireCode(models.Model):
    qr_code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('QR-код (DataMatrix)')
    )
    nomenclature = models.ForeignKey(
        TireNomenclature,
        on_delete=models.PROTECT,
        related_name='tire_codes',
        verbose_name=_('Номенклатура')
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tire_codes',
        verbose_name=_('Склад')
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tire_codes',
        verbose_name=_('Поставщик')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Активен'))
    is_used = models.BooleanField(default=False, verbose_name=_('Использован'))
    honest_sign_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('Данные Честный Знак')
    )
    document = models.ForeignKey(
        'warehouse.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tire_codes',
        verbose_name=_('Документ')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Дата использования')
    )

    class Meta:
        verbose_name = _('Код шины')
        verbose_name_plural = _('Коды шин')
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['warehouse', 'is_active', 'created_at'],
                name='tirecode_wh_active_idx'
            ),
        ]

    def __str__(self):
        return self.qr_code

    def mark_used(self, document):
        """Пометить код как использованный и привязать к документу."""
        self.is_used = True
        self.is_active = False
        self.document = document
        self.used_at = timezone.now()
        self.save()

    def unmark_used(self):
        """Снять пометку использования."""
        self.is_used = False
        self.is_active = True
        self.document = None
        self.used_at = None
        self.save()


class Tire(models.Model):
    qr_code = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    size = models.CharField(max_length=50)
    product_name = models.CharField(max_length=100, blank=True, null=True)
    arrival_date = models.DateTimeField(auto_now_add=True)
    departure_date = models.DateTimeField(blank=True, null=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    honest_sign_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Шина')
        verbose_name_plural = _('Шины')
        ordering = ['-created_at']

    def get_display_name(self):
        """Отображаемое имя для интерфейса (product_name если есть, иначе size+brand+model)"""
        return self.product_name or f"{self.size} {self.brand} {self.model}"

    def get_nomenclature_key(self):
        """Ключ для группировки номенклатуры (только технические характеристики)"""
        return f"{self.size} {self.brand} {self.model}"

    def __str__(self):
        return f"{self.product_name or self.size+' '+self.brand+' '+self.model}"

    def clean(self):
        super().clean()
        # Если склад ОХ, поставщик обязателен
        if self.warehouse and self.warehouse.warehouse_type == 'oh' and not self.supplier:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                'supplier': _('Для склада ОХ (Ответственное хранение) необходимо указать поставщика')
            })
