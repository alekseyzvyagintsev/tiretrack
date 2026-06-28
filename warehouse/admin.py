from django.contrib import admin

from .models import Document, DocumentType, DocumentItem, WarehouseMovement


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


@admin.register(DocumentItem)
class DocumentItemAdmin(admin.ModelAdmin):
    list_display = ('document', 'tire', 'quantity', 'created_at')
    list_filter = ('document', 'tire', 'created_at')
    search_fields = ('tire__qr_code', 'tire__product_name')
    ordering = ('-created_at',)
    raw_id_fields = ('document', 'tire')


@admin.register(WarehouseMovement)
class WarehouseMovementAdmin(admin.ModelAdmin):
    list_display = ('document', 'tire', 'movement_type', 'from_warehouse', 'to_warehouse', 'movement_date')
    list_filter = ('movement_type', 'from_warehouse', 'to_warehouse', 'movement_date')
    search_fields = ('tire__qr_code', 'document__document_number')
    ordering = ('-movement_date',)
    date_hierarchy = 'movement_date'
    raw_id_fields = ('document', 'tire')
