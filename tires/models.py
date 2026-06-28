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

    def __str__(self):
        return f"{self.product_name or self.model}"

    def clean(self):
        super().clean()
        # Если склад ОХ, поставщик обязателен
        if self.warehouse and self.warehouse.warehouse_type == 'oh' and not self.supplier:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                'supplier': _('Для склада ОХ (Ответственное хранение) необходимо указать поставщика')
            })
#
#
# class TransferDocument(models.Model):
#     STATUS_CHOICES = [
#         ('draft', 'Черновик'),
#         ('saved', 'Сохранен'),
#         ('posted', 'Проведён'),
#     ]
#
#     STATUS_COLORS = {
#         'draft': 'warning',
#         'saved': 'info',
#         'posted': 'success',
#     }
#
#     TYPE_CHOICES = [
#         ('transfer', 'Перемещение'),
#         ('dispatch', 'Реализация'),
#     ]
#
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
#     document_type = models.CharField(max_length=20, choices=TYPE_CHOICES, blank=True, null=True)
#     from_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='old_outgoing_documents')
#     to_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='old_incoming_documents', null=True, blank=True)
#     document_number = models.CharField(max_length=50, blank=True, null=True)
#     notes = models.TextField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     created_by = models.ForeignKey(User, on_delete=models.CASCADE)
#
#     class Meta:
#         verbose_name = _('Документ движения')
#         verbose_name_plural = _('Документы движения')
#         ordering = ['-created_at']
#
#     def __str__(self):
#         return f"{self.document_number or f'DOC-{self.id}'}"
#
#     def save(self, *args, **kwargs):
#         # Автоматическое определение типа документа
#         if self.from_warehouse_id and self.to_warehouse_id:
#             if self.from_warehouse_id != self.to_warehouse_id:
#                 self.document_type = 'transfer'
#             else:
#                 self.document_type = None
#         elif self.from_warehouse_id:
#             self.document_type = 'dispatch'
#         else:
#             self.document_type = None
#         super().save(*args, **kwargs)
#
#     def get_status_display(self):
#         """Отображение статуса"""
#         status_map = {
#             'draft': 'Черновик',
#             'saved': 'Сохранен',
#             'posted': 'Проведён',
#         }
#         return status_map.get(self.status, self.status)
#
#     def get_document_type_display(self):
#         """Отображение типа документа"""
#         type_map = {
#             'transfer': 'Перемещение',
#             'dispatch': 'Реализация',
#         }
#         if self.document_type:
#             return type_map.get(self.document_type, self.document_type)
#         return '—'
#
#     def get_status_color(self):
#         return self.STATUS_COLORS.get(self.status, 'secondary')
#
#
# class TransferDocumentItem(models.Model):
#     document = models.ForeignKey(TransferDocument, on_delete=models.CASCADE, related_name='items')
#     tires = models.ManyToManyField(Tire, related_name='old_document_items', blank=True)
#     product_name = models.CharField(max_length=100, blank=True, null=True)
#     qr_codes = models.JSONField(blank=True, null=True, help_text='Список QR-кодов для этой позиции')
#     quantity = models.PositiveIntegerField(default=1)
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     class Meta:
#         verbose_name = _('Позиция документа')
#         verbose_name_plural = _('Позиции документа')
#         ordering = ['created_at']
#
#     def __str__(self):
#         return f"{self.document} - {self.product_name} ({self.quantity})"
#
#     def get_qr_codes_list(self):
#         """Получить список QR-кодов для позиции"""
#         if self.qr_codes:
#             return self.qr_codes
#         return [t.qr_code for t in self.tires.all()]
