from django.urls import path
from . import views

app_name = 'qr_processing'

urlpatterns = [
    path('imports/', views.file_import, name='file-import'),
    path('imports/list/', views.import_list, name='import-list'),
    
    path('exports/', views.export_batch_list, name='export-batch-list'),
    path('exports/create/', views.export_batch_create, name='export-batch-create'),
    path('exports/list/', views.export_batch_list, name='export-batch-list'),
]
