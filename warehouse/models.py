from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from users.models import User
from tires.models import Tire, Warehouse, Supplier, TireNomenclature


class DocType(models.Model):
    """Тип документа: списание или выкуп"""
    CODES = [
        ('writeoff', 'Списание'),
        ('buyout', 'Выкуп'),
    ]

    code = models.CharField(max_length=20, unique=True, choices=CODES, verbose_name=_('Код'))
    name = models.CharField(max_length=100, verbose_name=_('Название'))
    prefix = models.CharField(max_length=5, verbose_name=_('Префикс номера'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активен'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создан'))

    class Meta:
        verbose_name = _('Тип документа')
        verbose_name_plural = _('Типы документов')
        ordering = ['code']

    def __str__(self):
        return self.name


class Document(models.Model):
    """Документ списания или выкупа DataMatrix-кодов"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('saved', 'Сохранён'),
        ('posted', 'Проведён'),
        ('marked_deleted', 'Помечен на удаление'),
    ]

    doc_type = models.ForeignKey(
        DocType,
        on_delete=models.PROTECT,
        related_name='documents',
        verbose_name=_('Тип документа'),
        null=True,
        blank=True
    )
    number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_('Номер')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_('Статус')
    )
    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='documents',
        verbose_name=_('Автор'),
        null=True,
        blank=True
    )
    source_platform = models.ForeignKey(
        'tires.Platform',
        on_delete=models.PROTECT,
        related_name='source_documents',
        verbose_name=_('Площадка-источник'),
        null=True,
        blank=True
    )
    writeoff_platform = models.ForeignKey(
        'tires.Platform',
        on_delete=models.PROTECT,
        related_name='writeoff_documents',
        null=True,
        blank=True,
        verbose_name=_('Площадка списания')
    )
    source_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='source_documents',
        verbose_name=_('Склад-источник'),
        null=True,
        blank=True
    )
    target_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='target_documents',
        null=True,
        blank=True,
        verbose_name=_('Склад-получатель')
    )
    is_deleted = models.BooleanField(default=False, verbose_name=_('Помечен на удаление'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создан'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлен'))
    posted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Дата проведения')
    )
    notes = models.TextField(blank=True, verbose_name=_('Примечания'))

    class Meta:
        verbose_name = _('Документ')
        verbose_name_plural = _('Документы')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['number']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['source_platform', 'status']),
        ]

    def __str__(self):
        if self.number:
            return f"{self.number} - {self.doc_type.name}"
        return f"{self.id}"

    def save(self, *args, **kwargs):
        # Запрещаем сохранять документы в статусе posted (только при обычном save)
        # При проведении используется update(), поэтому проверка не нужна
        if self.status == 'posted' and not kwargs.get('_bypass_posted_check', False):
            from django.core.exceptions import ValidationError
            raise ValidationError('Нельзя сохранять документ в статусе проведённый')

        # Генерация номера при переходе draft → saved
        if not self.number and self.status == 'saved' and self.doc_type:
            year = self.created_at.year if self.created_at else timezone.now().year
            prefix = self.doc_type.prefix
            count = Document.objects.filter(
                doc_type=self.doc_type,
                number__startswith=f"{prefix}-{year}-",
            ).count()
            self.number = f"{prefix}-{year}-{count + 1:06d}"

        super().save(*args, **kwargs)

    def can_edit(self):
        """Можно ли редактировать документ."""
        return self.status in ('draft', 'saved') and not self.is_deleted

    def can_post(self):
        """Можно ли провести документ."""
        return self.status == 'saved' and self.items.exists() and not self.is_deleted

    def can_unpost(self):
        """Можно ли распроведать документ."""
        return self.status == 'posted' and not self.is_deleted

    def mark_deleted(self):
        """Пометить документ на удаление."""
        if self.status == 'posted':
            from .services import DocumentService
            DocumentService.unpost_document(self)
        self.is_deleted = True
        self.status = 'marked_deleted'
        self.save()

    def get_status_color(self):
        """Цвет статуса для Bootstrap."""
        colors = {
            'draft': 'secondary',
            'saved': 'primary',
            'posted': 'success',
            'marked_deleted': 'danger',
        }
        return colors.get(self.status, 'secondary')


class DocumentItem(models.Model):
    """Позиция документа"""
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Документ')
    )
    nomenclature = models.ForeignKey(
        TireNomenclature,
        on_delete=models.PROTECT,
        related_name='document_items',
        verbose_name=_('Номенклатура'),
        null=True,
        blank=True
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_('Количество')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создан'))

    class Meta:
        verbose_name = _('Позиция документа')
        verbose_name_plural = _('Позиции документов')
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['document', 'nomenclature'],
                name='unique_item_per_document_and_nomenclature'
            ),
        ]

    def __str__(self):
        return f"{self.document.number or self.document.id} - {self.nomenclature} ({self.quantity})"

    @property
    def display_name(self):
        """Отображаемое имя номенклатуры."""
        return self.nomenclature.display_name()



