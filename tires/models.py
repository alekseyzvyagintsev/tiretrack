from django.db import models
from users.models import User
from django.utils.translation import gettext_lazy as _


class TireStatus(models.TextChoices):
    INTERNAL = 'internal', _('Внутренний')
    INTERMEDIATE = 'intermediate', _('Промежуточный')
    EXTERNAL = 'external', _('Внешний')


class OwnerType(models.TextChoices):
    EXCLUSIVE = 'exclusive', _('ООО Эксклюзив')
    SUPPLIER = 'supplier', _('Поставщик')
    OH = 'oh', _('Ответственное хранение')


class Owner(models.Model):
    name = models.CharField(max_length=255, unique=True)
    owner_type = models.CharField(max_length=20, choices=OwnerType.choices)
    honest_sign_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Владелец')
        verbose_name_plural = _('Владельцы')
        ordering = ['name']

    def __str__(self):
        return self.name


class Tire(models.Model):
    qr_code = models.CharField(max_length=100, unique=True)
    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    size = models.CharField(max_length=50)
    arrival_date = models.DateTimeField(auto_now_add=True)
    departure_date = models.DateTimeField(blank=True, null=True)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='tires')
    status = models.CharField(max_length=20, choices=TireStatus.choices, default=TireStatus.INTERNAL)
    honest_sign_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Шина')
        verbose_name_plural = _('Шины')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.qr_code} - {self.manufacturer} {self.model}"


class TireTransfer(models.Model):
    tire = models.ForeignKey(Tire, on_delete=models.CASCADE, related_name='transfers')
    from_owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='outgoing_transfers')
    to_owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='incoming_transfers')
    transferred_by = models.ForeignKey(User, on_delete=models.CASCADE)
    transfer_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('Передача шины')
        verbose_name_plural = _('Передачи шин')
        ordering = ['-transfer_date']

    def __str__(self):
        return f"{self.tire.qr_code} from {self.from_owner} to {self.to_owner}"