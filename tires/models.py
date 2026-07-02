from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models import User


class WarehouseType(models.TextChoices):
    MAIN = 'main', _('Основной склад')
    OH = 'oh', _('Ответственное хранение')


class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True)
    warehouse_type = models.CharField(max_length=20, choices=WarehouseType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Склад')
        verbose_name_plural = _('Склады')
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Поставщик')
        verbose_name_plural = _('Поставщики')
        ordering = ['name']

    def __str__(self):
        return self.name


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
