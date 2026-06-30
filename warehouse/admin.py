from django.contrib import admin
from django.utils.html import format_html_join

from .models import Document, DocumentType, DocumentItem, WarehouseMovement


class DocumentItemInline(admin.TabularInline):
    model = DocumentItem
    extra = 0
    fields = ('product_name', 'quantity')
    readonly_fields = ('product_name', 'quantity')


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('document_number', 'document_type', 'status', 'from_warehouse', 'to_warehouse', 'created_by', 'document_date')
    list_filter = ('status', 'document_type', 'from_warehouse', 'to_warehouse', 'document_date')
    search_fields = ('document_number', 'notes')
    ordering = ('-document_date',)
    date_hierarchy = 'document_date'
    raw_id_fields = ('created_by',)
    readonly_fields = ('document_number',)
    inlines = [DocumentItemInline]


@admin.register(DocumentItem)
class DocumentItemAdmin(admin.ModelAdmin):
    list_display = ('document', 'product_name', 'quantity', 'tires_list', 'created_at')
    list_filter = ('document', 'product_name', 'created_at')
    search_fields = ('product_name',)
    ordering = ('-created_at',)
    
    def tires_list(self, obj):
        """Показывает список QR-кодов шин, привязанных к позиции"""
        tires = obj.tires.all()
        if not tires.exists():
            return '-'
        # Получаем QR-коды и сокращаем их для компактности
        tire_codes = tires.values_list('qr_code', flat=True)
        return format_html_join(', ', '{}', [(q,) for q in tire_codes])
    tires_list.short_description = 'Шины'


@admin.register(WarehouseMovement)
class WarehouseMovementAdmin(admin.ModelAdmin):
    list_display = ('document', 'tire', 'movement_type', 'from_warehouse', 'to_warehouse', 'movement_date')
    list_filter = ('movement_type', 'from_warehouse', 'to_warehouse', 'movement_date')
    search_fields = ('tire__qr_code', 'document__document_number')
    ordering = ('-movement_date',)
    date_hierarchy = 'movement_date'
    raw_id_fields = ('document', 'tire')
