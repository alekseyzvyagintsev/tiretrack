# Generated migration for setting platform on existing warehouses

from django.db import migrations


def set_platform_for_warehouses(apps, schema_editor):
    """Проставляет Platform='Софийская Груз' для всех существующих складов."""
    Warehouse = apps.get_model('tires', 'Warehouse')
    Platform = apps.get_model('tires', 'Platform')

    platform, created = Platform.objects.get_or_create(
        name='Софийская Груз',
        defaults={'name': 'Софийская Груз'}
    )

    Warehouse.objects.filter(platform__isnull=True).update(platform=platform)


def unset_platform_for_warehouses(apps, schema_editor):
    """Обратная миграция — убирает platform."""
    Warehouse = apps.get_model('tires', 'Warehouse')
    Warehouse.objects.update(platform=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tires', '0004_add_platform_to_warehouse'),
    ]

    operations = [
        migrations.RunPython(set_platform_for_warehouses, unset_platform_for_warehouses),
    ]
