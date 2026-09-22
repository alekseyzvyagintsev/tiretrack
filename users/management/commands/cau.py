#############################################################################################################
import logging

from django.core.management import BaseCommand

from users.models import User, UserRoles
from tires.models import Platform

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Создаёт пользователей с ролями и площадками."

    def handle(self, *args, **options):
        # Создаём площадку если нет
        platform, _ = Platform.objects.get_or_create(
            name='Софийская Груз',
            defaults={'name': 'Софийская Груз'}
        )

        # Суперпользователь (admin)
        admin, created = User.objects.get_or_create(
            email="admin@example.com",
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "role": UserRoles.MANAGER,
                "platform": platform,
                "is_active": True
            }
        )
        if created:
            admin.set_password("qwer1234")
            admin.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Суперпользователь {admin.email} создан."))
        else:
            self.stdout.write(f"⚠️ Пользователь {admin.email} уже существует.")

        # Менеджер (начальник склада)
        manager, created = User.objects.get_or_create(
            email="manager@example.com",
            defaults={
                "is_staff": True,
                "role": UserRoles.MANAGER,
                "platform": platform,
                "is_active": True
            }
        )
        if created:
            manager.set_password("qwer1234")
            manager.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Менеджер {manager.email} создан."))
        else:
            self.stdout.write(f"⚠️ Пользователь {manager.email} уже существует.")

        # Кладовщик
        storekeeper, created = User.objects.get_or_create(
            email="storekeeper@example.com",
            defaults={
                "role": UserRoles.STOREKEEPER,
                "platform": platform,
                "is_active": True
            }
        )
        if created:
            storekeeper.set_password("qwer1234")
            storekeeper.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Кладовщик {storekeeper.email} создан."))
        else:
            self.stdout.write(f"⚠️ Пользователь {storekeeper.email} уже существует.")


#############################################################################################################
