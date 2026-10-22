from celery import Celery

app = Celery('tiretrack')

# Использование настроек из settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическое обнаружение задач в приложениях Django
app.autodiscover_tasks()

# Настройка filesystem broker для worker
app.conf.update(
    broker_url='filesystem://',
    broker_transport_options={
        'data_folder_out': '/home/alexey/IdeaProjects/tiretrack/celery/out',
        'data_folder_in': '/home/alexey/IdeaProjects/tiretrack/celery/in',
        'data_folder_processed': '/home/alexey/IdeaProjects/tiretrack/celery/processed',
    },
    result_backend='cache+memory://',
)

if __name__ == '__main__':
    app.start()
