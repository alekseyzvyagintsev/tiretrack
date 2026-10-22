from django.core.management.base import BaseCommand
from tires.models import Platform


class Command(BaseCommand):
    help = 'Создаёт seed-данные для Platform'

    def handle(self, *args, **options):
        platform, created = Platform.objects.get_or_create(
            name='Софийская Груз',
            defaults={'name': 'Софийская Груз'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Создана площадка: {platform}'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️ Площадка уже существует: {platform}'))
