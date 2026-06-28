from django.db.models import Count, Q

from .models import Tire


def search_tire_nomenclature(query='', warehouse_id=None):
    """Поиск номенклатуры шин по запросу (поиск по brand, model, size, product_name)"""
    tires = Tire.objects.filter(is_active=True).select_related('warehouse', 'supplier').order_by('-created_at')
    
    # Фильтрация по складу если указан
    if warehouse_id:
        tires = tires.filter(warehouse_id=warehouse_id)
    
    # Поиск - ищем по всем полям (brand, model, size, product_name)
    if query:
        # Ищем по всем частям запроса в любом из полей
        query_parts = query.split()
        if query_parts:
            q_filter = Q()
            for part in query_parts:
                # Ищем часть как подстроку в любом из полей (регистронезависимо)
                q_filter &= (
                    Q(product_name__icontains=part) |
                    Q(brand__icontains=part) |
                    Q(model__icontains=part) |
                    Q(size__icontains=part)
                )
            tires = tires.filter(q_filter)
    
    # Группировка по product_name с подсчётом количества
    grouped_tires = tires.values('product_name').annotate(
        count=Count('id'),
        qr_codes=Count('qr_code')
    ).order_by('-count', 'product_name')
    
    # Получаем детали для каждой группы
    tire_groups = []
    for group in grouped_tires:
        if group['product_name']:
            first_tire = tires.filter(product_name=group['product_name']).first()
            if first_tire:
                # Получаем все шины в этой группе
                group_tires = tires.filter(product_name=group['product_name'])
                
                tire_groups.append({
                    'product_name': group['product_name'],
                    'count': group['count'],
                    'qr_code': first_tire.qr_code,
                    'brand': first_tire.brand,
                    'model': first_tire.model,
                    'size': first_tire.size,
                    'warehouse': first_tire.warehouse,
                    'supplier': first_tire.supplier,
                    'arrival_date': first_tire.arrival_date,
                    'tires': group_tires,  # Добавляем список шин в группе
                })
    
    return tire_groups
