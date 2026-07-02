from django.urls import path

from . import views

app_name = 'warehouse'

urlpatterns = [
    # Домашняя страница
    path('', views.homepage, name='home'),
    
    # Документы
    path('documents/', views.document_list, name='document-list'),
    path('documents/new/', views.document_new, name='document-new'),
    path('documents/create/', views.document_create, name='document-create'),
    path('documents/<int:pk>/', views.document_detail, name='document-detail'),
    path('documents/<int:pk>/delete/', views.document_mark_deleted, name='document-delete'),
    path('documents/<int:pk>/unmark-delete/', views.document_unmark_deleted, name='document-unmark-delete'),
    path('documents/<int:pk>/add-item/', views.document_add_item, name='document-add-item'),
    path('documents/<int:pk>/delete-item/<int:item_pk>/', views.document_delete_item, name='document-delete-item'),
    path('documents/<int:pk>/post/', views.document_post, name='document-post'),
    path('documents/<int:pk>/unpost/', views.document_unpost, name='document-unpost'),
    path('documents/<int:pk>/save-quantities/', views.document_save_quantities, name='document-save-quantities'),
    
    # Отчеты
    path('reports/stock/', views.report_stock, name='report-stock'),
    path('reports/movement/', views.report_movement, name='report-movement'),
    path('reports/supplier/', views.report_supplier, name='report-supplier'),
]
