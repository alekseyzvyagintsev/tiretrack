from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

from users.models import User
from tires.models import Tire, Warehouse, Supplier


class DocumentType(models.Model):
    """Тип документа движения товара"""
    CODES = [
        ('receipt', 'Приемка'),
        ('movement', 'Перемещение'),
        ('dispatch', 'Отгрузка'),
        ('return', 'Возврат'),
    ]
    
    code = models.CharField(max_length=20, unique=True, choices=CODES, verbose_name='Код')
    name = models.CharField(max_length=100, verbose_name='Название')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    
    class Meta:
        verbose_name = 'Тип документа'
        verbose_name_plural = 'Типы документов'
        ordering = ['code']
    
    def __str__(self):
        return self.name


class Document(models.Model):
    """Документ движения товара"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('saved', 'Сохранен'),
        ('posted', 'Проведен'),
    ]
    
    document_number = models.CharField(max_length=50, blank=True, null=True, verbose_name='Номер документа')
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, related_name='documents', verbose_name='Тип документа')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='outgoing_documents', null=True, blank=True, verbose_name='Со склада')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='incoming_documents', null=True, blank=True, verbose_name='На склад')
    document_date = models.DateField(default=timezone.now, verbose_name='Дата документа')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_documents', verbose_name='Создан')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')
    deleted = models.BooleanField(default=False, verbose_name='Пометка на удаление')
    
    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['-document_date', '-created_at']
        indexes = [
            models.Index(fields=['document_number']),
            models.Index(fields=['status', 'document_date']),
        ]
    
    def __str__(self):
        if self.document_number:
            return f"{self.document_number} - {self.document_type.name}"
        return f"{self.id}"
    
    def save(self, *args, **kwargs):
        # Генерация номера документа, если не задан
        if not self.document_number and self.document_type:
            # Получаем префикс из name (первые 3 символа)
            prefix = self.document_type.name[:3].upper()
            date_part = self.document_date.strftime('%Y%m%d')
            
            # Считаем количество документов за сегодня с этим типом и префиксом
            count = Document.objects.filter(
                document_type=self.document_type,
                document_date=self.document_date,
                document_number__icontains=f"{prefix}-{date_part}"
            ).count()
            
            # Генерируем номер
            self.document_number = f"{prefix}-{date_part}-{count + 1:04d}"
        
        super().save(*args, **kwargs)
    
    def can_edit(self):
        """Можно ли редактировать документ"""
        return self.status in ['draft', 'saved'] and not self.deleted
    
    def can_delete(self):
        """Можно ли пометить на удаление"""
        return self.status in ['draft', 'saved'] and not self.deleted
    
    def can_add_item(self):
        """Можно ли добавить товар в документ"""
        return not self.deleted and not self.status == 'posted'
    
    def can_post(self):
        """Можно ли провести документ"""
        return self.status in ['draft', 'saved'] and self.items.exists() and not self.deleted
    
    def can_unpost(self):
        """Можно ли отменить проведение"""
        return self.status == 'posted' and not self.deleted
    
    def get_status_color(self):
        """Цвет статуса для Bootstrap"""
        colors = {
            'draft': 'warning',
            'saved': 'info',
            'posted': 'success',
        }
        return colors.get(self.status, 'secondary')


class DocumentItem(models.Model):
    """Позиция документа"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='items', verbose_name='Документ')
    product_name = models.CharField(max_length=100, verbose_name='Номенклатура', null=True, blank=True)
    tires = models.ManyToManyField(Tire, related_name='document_items', verbose_name='Шины')
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)], verbose_name='Количество')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    
    class Meta:
        verbose_name = 'Позиция документа'
        verbose_name_plural = 'Позиции документов'
        ordering = ['id']
        unique_together = ['document', 'product_name']
    
    def __str__(self):
        return f"{self.document_id} - {self.product_name} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class WarehouseMovement(models.Model):
    """История перемещения шин между складами"""
    MOVEMENT_TYPES = [
        ('in', 'Поступление'),
        ('out', 'Списание'),
        ('transfer', 'Перемещение'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name='movements', verbose_name='Документ')
    tire = models.ForeignKey(Tire, on_delete=models.PROTECT, related_name='warehouse_movements', verbose_name='Шина')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, verbose_name='Тип движения')
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='outgoing_movements', null=True, blank=True, verbose_name='Со склада')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='incoming_movements', null=True, blank=True, verbose_name='На склад')
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)], verbose_name='Количество')
    movement_date = models.DateTimeField(default=timezone.now, verbose_name='Дата движения')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    class Meta:
        verbose_name = 'История перемещения'
        verbose_name_plural = 'История перемещений'
        ordering = ['-movement_date']
        indexes = [
            models.Index(fields=['movement_date']),
            models.Index(fields=['tire']),
            models.Index(fields=['from_warehouse', 'to_warehouse']),
        ]
    
    def __str__(self):
        return f"{self.tire.qr_code} - {self.movement_date}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
