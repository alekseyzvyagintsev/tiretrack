"""Utility функции для warehouse."""
from django.db.models import Count, Q

from .models import Document, DocType, DocumentItem
from tires.models import TireNomenclature, Warehouse, Supplier


def get_tire_by_search(query, warehouse_id=None):
    """Поиск номенклатуры по запросу."""
    queryset = TireNomenclature.objects.filter(is_active=True)

    if warehouse_id:
        queryset = queryset.filter(
            tire_codes__warehouse_id=warehouse_id
        ).distinct()

    if query:
        queryset = queryset.filter(
            Q(brand__icontains=query) |
            Q(model__icontains=query) |
            Q(size__icontains=query) |
            Q(product_name__icontains=query)
        )

    return queryset


def get_tire_groups_by_search(query, warehouse_id=None):
    """Поиск и группировка номенклатуры по запросу."""
    return get_tire_by_search(query, warehouse_id)


def get_document_statistics():
    """Статистика по документам."""
    return {
        'total': Document.objects.count(),
        'draft': Document.objects.filter(status='draft').count(),
        'saved': Document.objects.filter(status='saved').count(),
        'posted': Document.objects.filter(status='posted').count(),
        'deleted': Document.objects.filter(status='marked_deleted').count(),
    }


def get_movement_statistics(start_date=None, end_date=None, warehouse_id=None):
    """Статистика по движениям (заглушка для MVP)."""
    return []


def get_supplier_statistics():
    """Статистика по поставщикам (заглушка для MVP)."""
    return []


def get_stock_by_warehouse():
    """Остатки по складам (заглушка для MVP)."""
    return []


def get_stock_by_product(warehouse_id=None):
    """Остатки по номенклатуре (заглушка для MVP)."""
    return []
