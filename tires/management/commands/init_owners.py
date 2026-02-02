from django.core.management.base import BaseCommand
from tires.models import Owner


class Command(BaseCommand):
    help = 'Создание базовых владельцев'

    def handle(self, *args, **options):
        owners_data = [
            {
                'name': 'ООО Эксклюзив',
                'owner_type': 'exclusive',
                'honest_sign_id': 'EXCLUSIVE_001'
            },
            {
                'name': 'Ответственное хранение',
                'owner_type': 'oh',
                'honest_sign_id': 'OH_001'
            },
            {
                'name': 'Поставщик шин',
                'owner_type': 'supplier',
                'honest_sign_id': 'SUPPLIER_001'
            }
        ]

        created_count = 0
        for owner_data in owners_data:
            owner, created = Owner.objects.get_or_create(
                name=owner_data['name'],
                defaults=owner_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'Создан владелец: {owner.name}')
            else:
                self.stdout.write(f'Владелец уже существует: {owner.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно создано {created_count} владельцев'
            )
        )