# Data migration: migrate Tire data to TireCode and TireNomenclature

from django.db import migrations


def migrate_tire_to_tirecode(apps, schema_editor):
    """Мигрирует данные из Tire в TireNomenclature и TireCode."""
    Tire = apps.get_model('tires', 'Tire')
    TireNomenclature = apps.get_model('tires', 'TireNomenclature')
    TireCode = apps.get_model('tires', 'TireCode')
    Warehouse = apps.get_model('tires', 'Warehouse')
    Supplier = apps.get_model('tires', 'Supplier')

    tires = Tire.objects.all()

    for tire in tires:
        # Создаём или получаем номенклатуру
        nomenclature, _ = TireNomenclature.objects.get_or_create(
            brand=tire.brand,
            model=tire.model,
            size=tire.size,
            defaults={
                'product_name': tire.product_name,
                'is_active': tire.is_active,
            }
        )
        # Если product_name уже есть, не перезаписываем (БП 14)
        if not nomenclature.product_name and tire.product_name:
            nomenclature.product_name = tire.product_name
            nomenclature.save(update_fields=['product_name'])

        # Создаём TireCode
        TireCode.objects.create(
            qr_code=tire.qr_code,
            nomenclature=nomenclature,
            warehouse=tire.warehouse,
            supplier=tire.supplier,
            is_active=tire.is_active,
            is_used=tire.departure_date is not None,
            honest_sign_data=tire.honest_sign_data,
            created_at=tire.arrival_date,
            used_at=tire.departure_date,
        )


def unmigrate_tirecode_to_tire(apps, schema_editor):
    """Обратная миграция: TireCode → Tire (для отката)."""
    Tire = apps.get_model('tires', 'Tire')
    TireCode = apps.get_model('tires', 'TireCode')

    tire_codes = TireCode.objects.select_related('nomenclature').all()

    for tc in tire_codes:
        Tire.objects.create(
            qr_code=tc.qr_code,
            brand=tc.nomenclature.brand,
            model=tc.nomenclature.model,
            size=tc.nomenclature.size,
            product_name=tc.nomenclature.product_name,
            arrival_date=tc.created_at,
            departure_date=tc.used_at,
            warehouse=tc.warehouse,
            supplier=tc.supplier,
            is_active=tc.is_active,
            honest_sign_data=tc.honest_sign_data,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('tires', '0006_add_nomenclature_and_tirecode_models'),
    ]

    operations = [
        migrations.RunPython(
            migrate_tire_to_tirecode,
            unmigrate_tirecode_to_tire,
            atomic=True
        ),
    ]
