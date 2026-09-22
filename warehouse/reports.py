from django.db.models import Count, Q
from django.utils import timezone

from .models import Document, DocumentType, DocumentItem, WarehouseMovement
from tires.models import Tire, Warehouse, Supplier


def report_stock(warehouse_id=None):
    """
    Отчет по остаткам на складах
    """
    if warehouse_id:
        warehouses = Warehouse.objects.filter(id=warehouse_id).annotate(
            tire_count=Count('tire')
        ).order_by('name')
    else:
        warehouses = Warehouse.objects.annotate(
            tire_count=Count('tire')
        ).order_by('name')
    
    # Группировка по номенклатуре
    stock_by_product = Tire.objects.filter(is_active=True).values(
        'product_name', 'warehouse__name'
    ).annotate(
        count=Count('id'),
        qr_codes=Count('qr_code')
    ).order_by('product_name', 'warehouse__name')
    
    return {
        'warehouses': warehouses,
        'stock_by_product': stock_by_product,
    }


def report_movement(start_date=None, end_date=None, warehouse_id=None):
    """
    Отчет по движению шин
    """
    movements = WarehouseMovement.objects.select_related(
        'document', 'tire', 'from_warehouse', 'to_warehouse'
    ).order_by('-movement_date')
    
    if start_date:
        movements = movements.filter(movement_date__gte=start_date)
    if end_date:
        movements = movements.filter(movement_date__lte=end_date)
    if warehouse_id:
        movements = movements.filter(
            Q(from_warehouse_id=warehouse_id) | Q(to_warehouse_id=warehouse_id)
        )
    
    # Подсчет статистики
    total_in = movements.filter(movement_type='in').count()
    total_out = movements.filter(movement_type='out').count()
    total_transfer = movements.filter(movement_type='transfer').count()
    
    return {
        'movements': movements,
        'total_in': total_in,
        'total_out': total_out,
        'total_transfer': total_transfer,
        'start_date': start_date,
        'end_date': end_date,
        'warehouse_id': warehouse_id,
    }


def report_supplier(supplier_id=None):
    """
    Отчет по поставщикам
    """
    if supplier_id:
        suppliers = Supplier.objects.filter(id=supplier_id).annotate(
            tire_count=Count('tire')
        ).order_by('name')
    else:
        suppliers = Supplier.objects.annotate(
            tire_count=Count('tire')
        ).order_by('name')
    
    # Данные по каждой поставке
    supplier_tires = Tire.objects.select_related('supplier').order_by('-arrival_date')
    
    return {
        'suppliers': suppliers,
        'supplier_tires': supplier_tires,
    }


def get_document_flow_statistics():
    """
    Получить статистику по потоку документов
    """
    return {
        'by_type': DocumentType.objects.annotate(
            count=Count('documents')
        ).order_by('-count'),
        'by_status': Document.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status'),
        'by_month': Document.objects.filter(
            created_at__year=timezone.now().year
        ).extra(
            select={'month': 'extract(month from created_at)'}
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month'),
    }
