from django.contrib import admin

from .models import Tire, Warehouse, Supplier, Platform, TireNomenclature, TireCode


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)


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


@admin.register(TireNomenclature)
class TireNomenclatureAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'brand', 'model', 'size', 'is_active', 'created_at')
    list_filter = ('is_active', 'brand')
    search_fields = ('brand', 'model', 'size', 'product_name')
    ordering = ('brand', 'model', 'size')


@admin.register(TireCode)
class TireCodeAdmin(admin.ModelAdmin):
    list_display = ('qr_code', 'nomenclature', 'warehouse', 'is_active', 'is_used', 'created_at')
    list_filter = ('is_active', 'is_used', 'warehouse')
    search_fields = ('qr_code', 'nomenclature__brand', 'nomenclature__model', 'nomenclature__size')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
