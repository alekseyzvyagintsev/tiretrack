from django.db.models import Count, Q, Value, Case, When, F
from django.db.models.fields import CharField, IntegerField
from django.db.models.functions import Concat

from .models import Tire, Warehouse, Supplier


def search_tire_nomenclature(query='', warehouse_id=None):
    """Поиск номенклатуры шин по запросу (поиск по brand, model, size, product_name)
    
    Оптимизированная версия с SQL-группировкой:
    - Группировка происходит на уровне SQL (GROUP BY)
    - Подсчёт количества в каждой группе через COUNT
    - Сортировка по количеству или точности совпадения
    """
    # Базовый запрос - только активные шины
    tires_qs = Tire.objects.filter(is_active=True)
    
    # Фильтрация по складу если указан
    if warehouse_id:
        tires_qs = tires_qs.filter(warehouse_id=warehouse_id)
    
    # Создаём аннотацию для nomenclature_key (size + brand + model)
    tires_qs = tires_qs.annotate(
        nomenclature_key=Concat(
            'size', Value(' '), 'brand', Value(' '), 'model',
            output_field=CharField()
        )
    )
    
    # Если есть поисковый запрос - фильтруем по nomenclature_key
    if query:
        # Ищем как подстроку в сформированной строке nomenclature_key
        tires_qs = tires_qs.filter(nomenclature_key__icontains=query)
        
        # Добавляем поле match_score для сортировки по точности совпадения
        tires_qs = tires_qs.annotate(
            match_score=Case(
                # Полное совпадение - наивысший приоритет
                When(nomenclature_key__iexact=query, then=Value(100)),
                # Начинается с запроса - второй приоритет
                When(nomenclature_key__istartswith=query, then=Value(50)),
                # Содержит запрос в середине - третий приоритет
                When(nomenclature_key__icontains=query, then=Value(25)),
                default=Value(1),
                output_field=IntegerField()
            )
        )
    else:
        # Без запроса - сортируем по количеству (уменьшение)
        tires_qs = tires_qs.annotate(match_score=Value(0, output_field=IntegerField()))
    
    # Группировка на уровне SQL (SELECT ... GROUP BY)
    # И подсчёт количества в каждой группе
    group_by_fields = ['size', 'brand', 'model', 'warehouse', 'supplier']
    tires_groups_qs = tires_qs.values(*group_by_fields).annotate(
        count=Count('id'),
        nomenclature_key=Concat(
            'size', Value(' '), 'brand', Value(' '), 'model',
            output_field=CharField()
        ),
        match_score=F('match_score')
    )
    
    # Сортировка: сначала по точности совпадения (match_score), потом по количеству
    tires_groups_qs = tires_groups_qs.order_by('-match_score', '-count')
    
    # Получаем ID склада для выборки (для select_related в финальном запросе)
    warehouse_ids = list(tires_groups_qs.values_list('warehouse', flat=True).distinct())
    
    # Создаём словарь складов для оптимизации
    warehouses_dict = {}
    if warehouse_ids:
        warehouses_dict = {w.id: w for w in Warehouse.objects.filter(id__in=warehouse_ids)}
    
    # Создаём словарь поставщиков
    supplier_ids = list(tires_groups_qs.values_list('supplier', flat=True).distinct())
    suppliers_dict = {}
    if supplier_ids:
        from .models import Supplier
        suppliers_dict = {s.id: s for s in Supplier.objects.filter(id__in=supplier_ids)}
    
    # Формируем финальный результат
    tire_groups = []
    for group in tires_groups_qs:
        # Находим первую шину из группы (для получения дополнительных данных)
        first_tire = Tire.objects.filter(
            size=group['size'],
            brand=group['brand'],
            model=group['model'],
            warehouse_id=group.get('warehouse'),
            supplier_id=group.get('supplier')
        ).select_related('warehouse', 'supplier').first()
        
        if first_tire:
            tire_groups.append({
                'product_name': first_tire.get_display_name(),
                'count': group['count'],
                'qr_code': first_tire.qr_code,
                'brand': group['brand'],
                'model': group['model'],
                'size': group['size'],
                'warehouse': warehouses_dict.get(first_tire.warehouse_id) if first_tire.warehouse_id else None,
                'supplier': suppliers_dict.get(first_tire.supplier_id) if first_tire.supplier_id else None,
                'arrival_date': first_tire.arrival_date,
                'nomenclature_key': group['nomenclature_key'],
            })
    
    return tire_groups
