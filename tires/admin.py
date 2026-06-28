from django.contrib import admin

from .models import Tire, Warehouse, Supplier


@admin.register(Tire)
class TireAdmin(admin.ModelAdmin):
    list_display = ('qr_code', 'product_name', 'warehouse', 'supplier', 'is_active', 'arrival_date')
    list_filter = ('warehouse', 'supplier', 'is_active', 'arrival_date')
    search_fields = ('qr_code', 'brand', 'model', 'size')
    ordering = ('-arrival_date',)
    date_hierarchy = 'arrival_date'


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'warehouse_type', 'created_at')
    list_filter = ('warehouse_type',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)
