from django.urls import path
from . import views

app_name = 'qr_processing'

urlpatterns = [
    # Загрузка QR-кодов
    path('imports/', views.file_import, name='file-import'),
    path('imports/report/<int:file_import_id>/', views.upload_report, name='upload-report'),
    path('imports/list/', views.import_list, name='import-list'),

    # Экспорт
    path('exports/', views.export_batch_list, name='export-batch-list'),
    path('exports/create/', views.export_batch_create, name='export-batch-create'),
]
