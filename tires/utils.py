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
    
    # Получаем все уникальные nomenclature_key из get_nomenclature_key() (для группировки)
    tire_dict = {}  # nomenclature_key -> список шин
    for tire in tires:
        key = tire.get_nomenclature_key()
        if key not in tire_dict:
            tire_dict[key] = []
        tire_dict[key].append(tire)
    
    # Для каждого nomenclature_key создаем запись в результатах
    tire_groups = []
    for key, group_tires in tire_dict.items():
        if group_tires:
            first_tire = group_tires[0]
            tire_groups.append({
                'product_name': first_tire.get_display_name(),
                'count': len(group_tires),
                'qr_code': first_tire.qr_code,
                'brand': first_tire.brand,
                'model': first_tire.model,
                'size': first_tire.size,
                'warehouse': first_tire.warehouse,
                'supplier': first_tire.supplier,
                'arrival_date': first_tire.arrival_date,
                'tires': group_tires,
            })
    
    # Сортируем по количеству (уменьшение)
    tire_groups.sort(key=lambda x: x['count'], reverse=True)
    
    return tire_groups
