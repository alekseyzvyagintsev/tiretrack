from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'tires'

urlpatterns = [
    # Домашняя страница
    path('', views.homepage, name='homepage'),
    
    # Склады
    path('warehouses/', views.warehouse_list, name='warehouse-list'),
    path('warehouses/create/', views.warehouse_create, name='warehouse-create'),
    path('warehouses/<int:pk>/edit/', views.warehouse_edit, name='warehouse-edit'),
    path('warehouses/<int:pk>/delete/', views.warehouse_delete, name='warehouse-delete'),
    
    # Поставщики
    path('suppliers/', views.supplier_list, name='supplier-list'),
    path('suppliers/create/', views.supplier_create, name='supplier-create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier-edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier-delete'),
    
    # Шины
    path('list/', views.tire_list, name='tire-list'),
    path('list/partial/', views.tire_list_partial, name='tire-list-partial'),
    path('search/', views.tire_search_ajax, name='tire-search-ajax'),
    path('create/', views.tire_create, name='tire-create'),
    path('<int:pk>/edit/', views.tire_edit, name='tire-edit'),
    path('<int:pk>/delete/', views.tire_delete, name='tire-delete'),
]
