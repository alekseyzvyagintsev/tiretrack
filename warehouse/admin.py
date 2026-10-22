from django.contrib import admin

from .models import Document, DocType, DocumentItem


class DocumentItemInline(admin.TabularInline):
    model = DocumentItem
    extra = 0
    fields = ('nomenclature', 'quantity')
    readonly_fields = ('nomenclature',)


@admin.register(DocType)
class DocTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'prefix', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'doc_type', 'status', 'author',
        'source_warehouse', 'created_at', 'posted_at'
    )
    list_filter = ('status', 'doc_type', 'source_platform', 'created_at')
    search_fields = ('number', 'notes')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    raw_id_fields = ('author', 'source_platform', 'writeoff_platform', 'source_warehouse', 'target_warehouse')
    readonly_fields = ('number', 'created_at', 'updated_at', 'posted_at')
    inlines = [DocumentItemInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'posted':
            return self.readonly_fields | ('doc_type', 'author', 'source_platform', 'source_warehouse')
        return self.readonly_fields


@admin.register(DocumentItem)
class DocumentItemAdmin(admin.ModelAdmin):
    list_display = ('document', 'nomenclature', 'quantity', 'created_at')
    list_filter = ('document', 'nomenclature', 'created_at')
    search_fields = ('nomenclature__brand', 'nomenclature__model', 'nomenclature__size')
    ordering = ('-created_at',)
