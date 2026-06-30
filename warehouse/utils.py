from django.db.models import Count, Q

from .models import Document, DocumentType, DocumentItem, WarehouseMovement
from tires.models import Tire, Warehouse, Supplier


def get_tire_by_search(query, warehouse_id=None):
    """
    Поиск шин по запросу
    Используется для автоподстановки в формы
    """
    queryset = Tire.objects.filter(is_active=True)
    
    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)
    
    if query:
        queryset = queryset.filter(
            Q(qr_code__icontains=query) |
            Q(product_name__icontains=query) |
            Q(brand__icontains=query) |
            Q(model__icontains=query)
        )
    
    return queryset.select_related('warehouse', 'supplier').order_by('-created_at')


def get_tire_groups_by_search(query, warehouse_id=None):
    """
    Поиск шин с группировкой по номенклатуре
    Возвращает структуру для отображения в UI
    """
    queryset = Tire.objects.filter(is_active=True)
    
    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)
    
    if query:
        queryset = queryset.filter(
            Q(product_name__icontains=query) |
            Q(brand__icontains=query)
        )
    
    # Группируем по номенклатуре
    tire_groups = {}
    for tire in queryset:
        key = f"{tire.product_name or tire.brand} ({tire.brand} {tire.size})"
        if key not in tire_groups:
            tire_groups[key] = {
                'product_name': tire.product_name,
                'brand': tire.brand,
                'size': tire.size,
                'tires': [],
            }
        tire_groups[key]['tires'].append(tire)
    
    return list(tire_groups.values())


def get_document_statistics():
    """
    Получить статистику по документам
    Возвращает количество документов по статусам
    """
    return {
        'total': Document.objects.count(),
        'saved': Document.objects.filter(status='saved').count(),
        'posted': Document.objects.filter(status='posted').count(),
        'deleted': Document.objects.filter(deleted=True).count(),
    }


def get_movement_statistics(start_date=None, end_date=None, warehouse_id=None):
    """
    Получить статистику по движению
    """
    movements = WarehouseMovement.objects.all()
    
    if start_date:
        movements = movements.filter(movement_date__gte=start_date)
    if end_date:
        movements = movements.filter(movement_date__lte=end_date)
    if warehouse_id:
        movements = movements.filter(
            Q(from_warehouse_id=warehouse_id) | Q(to_warehouse_id=warehouse_id)
        )
    
    return {
        'in': movements.filter(movement_type='in').count(),
        'out': movements.filter(movement_type='out').count(),
        'transfer': movements.filter(movement_type='transfer').count(),
        'total': movements.count(),
    }


def get_supplier_statistics():
    """
    Получить статистику по поставщикам
    """
    return Supplier.objects.annotate(
        tire_count=Count('tire')
    ).order_by('-tire_count')


def get_stock_by_warehouse():
    """
    Получить остатки по складам
    """
    return Warehouse.objects.annotate(
        tire_count=Count('tire')
    ).order_by('name')


def get_stock_by_product(warehouse_id=None):
    """
    Получить остатки по номенклатуре
    """
    queryset = Tire.objects.filter(is_active=True)
    
    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)
    
    return queryset.values(
        'product_name', 'warehouse__name'
    ).annotate(
        count=Count('id'),
        qr_codes=Count('qr_code')
    ).order_by('product_name', 'warehouse__name')
