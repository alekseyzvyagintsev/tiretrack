from django.db import models
from users.models import User
from tires.models import Tire
from django.utils.translation import gettext_lazy as _


class FileImport(models.Model):
    FILE_TYPE_CHOICES = [
        ('txt', 'Text File'),
        ('pdf', 'PDF File'),
    ]
    
    file = models.FileField(upload_to='imports/')
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    upload_date = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    log = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('Импорт файла')
        verbose_name_plural = _('Импорты файлов')
        ordering = ['-upload_date']

    def __str__(self):
        return f"Import {self.file.name} by {self.uploaded_by.email}"


class QRCodeData(models.Model):
    qr_code = models.CharField(max_length=100, unique=True)
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    owner = models.CharField(max_length=100, blank=True, null=True)
    honest_sign_data = models.JSONField(blank=True, null=True)
    verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Данные QR-кода')
        verbose_name_plural = _('Данные QR-кодов')
        ordering = ['-created_at']

    def __str__(self):
        return self.qr_code


class ExportBatch(models.Model):
    EXPORT_FORMAT_CHOICES = [
        ('txt', 'Text File'),
        ('qr_images', 'QR Code Images'),
    ]
    
    name = models.CharField(max_length=255)
    export_format = models.CharField(max_length=20, choices=EXPORT_FORMAT_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    tire_count = models.IntegerField(default=0)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    completed = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Пакет экспорта')
        verbose_name_plural = _('Пакеты экспорта')
        ordering = ['-created_at']

    def __str__(self):
        return f"Export {self.name} ({self.tire_count} tires)"