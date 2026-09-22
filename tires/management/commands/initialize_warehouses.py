from django.core.management.base import BaseCommand
from tires.models import Warehouse, Supplier


class Command(BaseCommand):
    help = 'Создает начальные данные для складов и поставщиков'

    def handle(self, *args, **kwargs):
        # Создаем основной склад
        main_warehouse, created = Warehouse.objects.get_or_create(
            name='Основной склад',
            defaults={'warehouse_type': 'main'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Основной склад создан'))
        else:
            self.stdout.write('Основной склад уже существует')

        # Создаем склад ОХ
        oh_warehouse, created = Warehouse.objects.get_or_create(
            name='Склад ОХ',
            defaults={'warehouse_type': 'oh'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Склад ОХ создан'))
        else:
            self.stdout.write('Склад ОХ уже существует')

        # Создаем поставщика "Наше" для основного склада
        our_supplier, created = Supplier.objects.get_or_create(
            name='Наше',
            defaults={}
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Поставщик "Наше" создан'))
        else:
            self.stdout.write('Поставщик "Наше" уже существует')

        self.stdout.write(self.style.SUCCESS('Начальные данные успешно созданы'))
