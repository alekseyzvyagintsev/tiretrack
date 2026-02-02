import os
from celery import Celery

# Установка настроек Django для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiretrack.settings')

app = Celery('tiretrack')

# Использование настроек из settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическое обнаружение задач в приложениях Django
app.autodiscover_tasks()