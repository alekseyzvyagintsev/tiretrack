from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db import transaction
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .models import Tire, Warehouse, Supplier
from .utils import search_tire_nomenclature


def homepage(request):
    """Домашняя страница - приветственная страница"""
    return render(request, 'tires/home.html')


def warehouse_list(request):
    """Список складов"""
    query = request.GET.get('q', '')
    warehouses = Warehouse.objects.all().order_by('name')
    
    if query:
        warehouses = warehouses.filter(Q(name__icontains=query))
    
    paginator = Paginator(warehouses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'tires/warehouses.html', {
        'page_obj': page_obj,
        'query': query,
    })


def warehouse_create(request):
    """Создание нового склада"""
    if request.method == 'POST':
        name = request.POST.get('name')
        warehouse_type = request.POST.get('warehouse_type')
        
        if Warehouse.objects.filter(name=name).exists():
            messages.error(request, 'Склад с таким именем уже существует')
            return redirect('tires:warehouse-create')
        
        Warehouse.objects.create(
            name=name,
            warehouse_type=warehouse_type,
        )
        messages.success(request, 'Склад успешно создан')
        return redirect('tires:warehouse-list')
    
    return render(request, 'tires/warehouse_form.html')


def warehouse_edit(request, pk):
    """Редактирование склада"""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        warehouse_type = request.POST.get('warehouse_type')
        
        if Warehouse.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, 'Склад с таким именем уже существует')
            return redirect('tires:warehouse-edit', pk=pk)
        
        warehouse.name = name
        warehouse.warehouse_type = warehouse_type
        warehouse.save()
        
        messages.success(request, 'Склад успешно обновлен')
        return redirect('tires:warehouse-list')
    
    return render(request, 'tires/warehouse_form.html', {'warehouse': warehouse})


def warehouse_delete(request, pk):
    """Удаление склада"""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    if request.method == 'POST':
        warehouse.delete()
        messages.success(request, 'Склад успешно удален')
        return redirect('tires:warehouse-list')
    
    return render(request, 'tires/warehouse_confirm_delete.html', {'warehouse': warehouse})


def supplier_list(request):
    """Список поставщиков"""
    query = request.GET.get('q', '')
    suppliers = Supplier.objects.all().order_by('name')
    
    if query:
        suppliers = suppliers.filter(Q(name__icontains=query))
    
    paginator = Paginator(suppliers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'tires/suppliers.html', {
        'page_obj': page_obj,
        'query': query,
    })


def supplier_create(request):
    """Создание нового поставщика"""
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if Supplier.objects.filter(name=name).exists():
            messages.error(request, 'Поставщик с таким именем уже существует')
            return redirect('tires:supplier-create')
        
        Supplier.objects.create(name=name)
        messages.success(request, 'Поставщик успешно создан')
        return redirect('tires:supplier-list')
    
    return render(request, 'tires/supplier_form.html')


def supplier_edit(request, pk):
    """Редактирование поставщика"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if Supplier.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, 'Поставщик с таким именем уже существует')
            return redirect('tires:supplier-edit', pk=pk)
        
        supplier.name = name
        supplier.save()
        
        messages.success(request, 'Поставщик успешно обновлен')
        return redirect('tires:supplier-list')
    
    return render(request, 'tires/supplier_form.html', {'supplier': supplier})


def supplier_delete(request, pk):
    """Удаление поставщика"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, 'Поставщик успешно удален')
        return redirect('tires:supplier-list')
    
    return render(request, 'tires/supplier_confirm_delete.html', {'supplier': supplier})


def tire_list(request):
    """Список шин"""
    warehouse_filter = request.GET.get('warehouse', '')
    query = request.GET.get('q', '')
    
    tires = Tire.objects.all().select_related('warehouse', 'supplier').order_by('-created_at')
    
    # Применяем фильтры всегда если есть параметры
    if warehouse_filter:
        tires = tires.filter(warehouse_id=warehouse_filter)
    
    # Доступные склады для фильтра
    warehouses = Warehouse.objects.all()
    
    # Используем выделенную функцию поиска номенклатуры (с фильтрацией по складу)
    tire_groups = search_tire_nomenclature(query, warehouse_id=warehouse_filter if warehouse_filter else None)
    
    paginator = Paginator(tire_groups, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Подсчёт количества шин по складам
    warehouse_counts = Warehouse.objects.annotate(tire_count=Count('tire'))
    
    return render(request, 'tires/list.html', {
        'tires': page_obj,
        'page_obj': page_obj,
        'warehouse_filter': warehouse_filter,
        'query': query,
        'warehouses': warehouses,
        'warehouse_counts': warehouse_counts,
    })


def tire_list_partial(request):
    """AJAX-часть списка шин (только таблица)"""
    warehouse_filter = request.GET.get('warehouse', '')
    query = request.GET.get('q', '')
    
    # Используем выделенную функцию поиска номенклатуры (с фильтрацией по складу)
    tire_groups = search_tire_nomenclature(query, warehouse_id=warehouse_filter if warehouse_filter else None)
    
    paginator = Paginator(tire_groups, 20)
    page_number = request.GET.get('page', '1')
    page_obj = paginator.get_page(page_number)
    
    # Подсчёт количества шин по складам
    warehouse_counts = Warehouse.objects.annotate(tire_count=Count('tire'))
    
    return render(request, 'tires/partials/table.html', {
        'tires': page_obj,
        'warehouse_counts': warehouse_counts,
    })


def tire_create(request):
    """Создание новой шины"""
    warehouses = Warehouse.objects.all()
    suppliers = Supplier.objects.all()
    
    if request.method == 'POST':
        qr_code = request.POST.get('qr_code')
        brand = request.POST.get('brand')
        model = request.POST.get('model')
        size = request.POST.get('size')
        warehouse_id = request.POST.get('warehouse')
        supplier_id = request.POST.get('supplier')
        
        if Tire.objects.filter(qr_code=qr_code).exists():
            messages.error(request, 'Шина с таким QR-кодом уже существует')
            return redirect('tires:tire-create')
        
        warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
        
        # Если склад ОХ, поставщик обязателен
        if warehouse.warehouse_type == 'oh' and not supplier_id:
            messages.error(request, 'Для склада ОХ необходимо выбрать поставщика')
            return redirect('tires:tire-create')
        
        # Если склад Основной, поставщик автоматически "Наше"
        if warehouse.warehouse_type == 'main':
            supplier, _ = Supplier.objects.get_or_create(name='Наше')
        elif supplier_id:
            supplier = get_object_or_404(Supplier, pk=supplier_id)
        else:
            supplier = None
        
        Tire.objects.create(
            qr_code=qr_code,
            brand=brand,
            model=model,
            size=size,
            warehouse=warehouse,
            supplier=supplier,
        )
        messages.success(request, 'Шина успешно создана')
        return redirect('tires:tire-list')
    
    return render(request, 'tires/tire_form.html', {
        'warehouses': warehouses,
        'suppliers': suppliers,
    })


def tire_edit(request, pk):
    """Редактирование шины"""
    tire = get_object_or_404(Tire, pk=pk)
    warehouses = Warehouse.objects.all()
    suppliers = Supplier.objects.all()
    
    if request.method == 'POST':
        qr_code = request.POST.get('qr_code')
        brand = request.POST.get('brand')
        model = request.POST.get('model')
        size = request.POST.get('size')
        warehouse_id = request.POST.get('warehouse')
        supplier_id = request.POST.get('supplier')
        
        if Tire.objects.filter(qr_code=qr_code).exclude(pk=pk).exists():
            messages.error(request, 'Шина с таким QR-кодом уже существует')
            return redirect('tires:tire-edit', pk=pk)
        
        warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
        
        # Если склад ОХ, поставщик обязателен
        if warehouse.warehouse_type == 'oh' and not supplier_id:
            messages.error(request, 'Для склада ОХ необходимо выбрать поставщика')
            return redirect('tires:tire-edit', pk=pk)
        
        # Если склад Основной, поставщик автоматически "Наше"
        if warehouse.warehouse_type == 'main':
            supplier, _ = Supplier.objects.get_or_create(name='Наше')
        elif supplier_id:
            supplier = get_object_or_404(Supplier, pk=supplier_id)
        else:
            supplier = None
        
        tire.qr_code = qr_code
        tire.brand = brand
        tire.model = model
        tire.size = size
        tire.warehouse = warehouse
        tire.supplier = supplier
        tire.save()
        
        messages.success(request, 'Шина успешно обновлена')
        return redirect('tires:tire-list')
    
    return render(request, 'tires/tire_form.html', {
        'tire': tire,
        'warehouses': warehouses,
        'suppliers': suppliers,
    })


def tire_delete(request, pk):
    """Удаление шины"""
    tire = get_object_or_404(Tire, pk=pk)
    
    if request.method == 'POST':
        tire.delete()
        messages.success(request, 'Шина успешно удалена')
        return redirect('tires:tire-list')
    
    return render(request, 'tires/tire_confirm_delete.html', {'tire': tire})
