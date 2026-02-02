from django.urls import path
from . import views

app_name = 'qr_processing'

urlpatterns = [
    path('imports/', views.FileImportView.as_view(), name='file-import'),
    path('imports/list/', views.FileImportListView.as_view(), name='import-list'),
    
    path('qr-data/', views.QRCodeDataView.as_view(), name='qr-data'),
    
    path('exports/', views.ExportBatchView.as_view(), name='export-batch'),
]