from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .models import Document, DocumentType, DocumentItem, WarehouseMovement
from .forms import DocumentForm, DocumentItemForm
from .services import DocumentService
from tires.models import Tire, Warehouse, Supplier
from tires.utils import search_tire_nomenclature


@login_required
def homepage(request):
    """Домашняя страница - приветственная страница"""
    from .utils import get_document_statistics, get_movement_statistics
    
    stats = get_document_statistics()
    
    return render(request, 'warehouse/home.html', {
        'total_count': stats['total'],
        'draft_count': stats['draft'],
        'saved_count': stats['saved'],
        'posted_count': stats['posted'],
        'deleted_count': stats['deleted'],
    })


@login_required
def document_list(request):
    """Список всех документов"""
    show_deleted = request.GET.get('show_deleted', 'false') == 'true'
    
    if show_deleted:
        documents = Document.objects.select_related('document_type', 'from_warehouse', 'to_warehouse', 'created_by').order_by('-document_date')
    else:
        documents = Document.objects.filter(deleted=False).select_related('document_type', 'from_warehouse', 'to_warehouse', 'created_by').order_by('-document_date')
    
    # Фильтрация по статусу
    status_filter = request.GET.get('status', '')
    if status_filter:
        documents = documents.filter(status=status_filter)
    
    # Фильтрация по типу
    type_filter = request.GET.get('type', '')
    if type_filter:
        documents = documents.filter(document_type__code=type_filter)
    
    # Поиск по номеру
    query = request.GET.get('q', '')
    if query:
        documents = documents.filter(document_number__icontains=query)
    
    # Подсчет статистики
    total_count = documents.count()
    draft_count = documents.filter(status='draft').count()
    saved_count = documents.filter(status='saved').count()
    posted_count = documents.filter(status='posted').count()
    deleted_count = documents.filter(deleted=True).count()
    
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'warehouse/document_list.html', {
        'page_obj': page_obj,
        'total_count': total_count,
        'draft_count': draft_count,
        'saved_count': saved_count,
        'posted_count': posted_count,
        'deleted_count': deleted_count,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'query': query,
        'show_deleted': show_deleted,
    })


@login_required
def document_create(request):
    """Создание нового документа"""
    document_types = DocumentType.objects.filter(is_active=True)
    warehouses = Warehouse.objects.all()
    
    # Проверка наличия обязательных данных
    if not document_types.exists():
        messages.error(request, 'Нет доступных типов документов. Создайте типы документов в админке.')
        return redirect('warehouse:document-list')
    
    if not warehouses.exists():
        messages.error(request, 'Нет доступных складов. Создайте склады в админке.')
        return redirect('warehouse:document-list')
    
    if request.method == 'POST':
        form = DocumentForm(request.POST)
        if form.is_valid():
            document = form.save(commit=False)
            document.created_by = request.user
            document.save()
            messages.success(request, 'Документ создан')
            return redirect('warehouse:document-detail', pk=document.pk)
        else:
            messages.error(request, 'Ошибка при создании документа')
    else:
        # GET - формируем черновик с первым доступным типом
        default_type = document_types.first()
        default_warehouse = warehouses.first()
        
        document = Document.objects.create(
            document_type=default_type,
            from_warehouse=default_warehouse,
            to_warehouse=None,
            notes='',
            status='draft',
            created_by=request.user,
        )
        return redirect('warehouse:document-detail', pk=document.pk)
    
    return render(request, 'warehouse/document_form.html', {
        'form': form,
        'warehouses': warehouses,
        'document_types': document_types,
    })


@login_required
def document_detail(request, pk):
    """Детальный просмотр документа"""
    document = get_object_or_404(Document, pk=pk)
    items = document.items.all()
    warehouses = Warehouse.objects.all()
    document_types = DocumentType.objects.filter(is_active=True)
    
    if request.method == 'POST' and document.status == 'draft':
        form = DocumentForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, 'Документ обновлен')
            return redirect('warehouse:document-detail', pk=document.pk)
        else:
            messages.error(request, 'Ошибка при обновлении документа')
    else:
        form = DocumentForm(instance=document)
    
    return render(request, 'warehouse/document_detail.html', {
        'document': document,
        'items': items,
        'warehouses': warehouses,
        'document_types': document_types,
        'form': form,
    })


@login_required
def document_edit(request, pk):
    """Редактирование документа"""
    document = get_object_or_404(Document, pk=pk)
    warehouses = Warehouse.objects.all()
    document_types = DocumentType.objects.filter(is_active=True)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, 'Документ обновлен')
            return redirect('warehouse:document-detail', pk=document.pk)
        else:
            messages.error(request, 'Ошибка при обновлении документа')
    else:
        form = DocumentForm(instance=document)
    
    return render(request, 'warehouse/document_form.html', {
        'document': document,
        'warehouses': warehouses,
        'document_types': document_types,
        'form': form,
    })


@login_required
def document_add_item(request, pk):
    """Добавление товара в документ"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        tire_id = request.POST.get('tire')
        
        if not tire_id:
            messages.error(request, 'Выберите товар')
            return redirect('warehouse:document-detail', pk=pk)
        
        tire = get_object_or_404(Tire, pk=tire_id)
        
        # Проверка: шина должна быть на складе отправления
        if tire.warehouse_id != document.from_warehouse_id:
            messages.error(request, f'Шина {tire.qr_code} находится на другом складе')
            return redirect('warehouse:document-detail', pk=pk)
        
        # Проверка: шина не должна быть уже привязана к активному документу
        if tire.document_items.filter(document__status__in=['saved', 'posted']).exists():
            messages.error(request, f'Шина {tire.qr_code} уже привязана к активному документу')
            return redirect('warehouse:document-detail', pk=pk)
        
        # Создаем позицию
        item = DocumentItem.objects.create(
            document=document,
            tire=tire,
            quantity=1,
        )
        
        messages.success(request, 'Товар добавлен в документ')
        
        # HTMX-запрос - возвращаем частичный HTML
        if 'HX-Request' in request.headers:
            items = document.items.all()
            return render(request, 'warehouse/partials/document_items.html', {
                'document': document,
                'items': items,
            })
        
        return redirect('warehouse:document-detail', pk=pk)
    
    # GET - возвращаем список шин для выбора
    query = request.GET.get('q', '')
    tire_groups = search_tire_nomenclature(query, warehouse_id=document.from_warehouse_id)
    
    return render(request, 'warehouse/partials/document_select.html', {
        'tire_groups': tire_groups,
        'document': document,
    })


@login_required
def document_delete_item(request, pk, item_pk):
    """Удаление позиции из документа"""
    document = get_object_or_404(Document, pk=pk)
    item = get_object_or_404(DocumentItem, pk=item_pk, document=document)
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Позиция удалена из документа')
        
        # HTMX-запрос - возвращаем частичный HTML
        if 'HX-Request' in request.headers:
            items = document.items.all()
            return render(request, 'warehouse/partials/document_items.html', {
                'document': document,
                'items': items,
            })
    
    return redirect('warehouse:document-detail', pk=pk)


@login_required
def document_post(request, pk):
    """Проведение документа"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        try:
            DocumentService.post_document(document)
            messages.success(request, 'Документ проведён')
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('warehouse:document-detail', pk=pk)
    
    return redirect('warehouse:document-detail', pk=pk)


@login_required
def document_unpost(request, pk):
    """Отмена проведения документа"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        try:
            DocumentService.unpost_document(document)
            messages.success(request, 'Проведение отменено')
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('warehouse:document-detail', pk=pk)
    
    return redirect('warehouse:document-detail', pk=pk)


@login_required
def document_save_quantities(request, pk):
    """Сохранение количеств и привязки шин к документу"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        # Обрабатываем изменения количества (пока только 1 шина на позицию)
        for key, value in request.POST.items():
            if key.startswith('item_'):
                try:
                    item_pk = key.replace('item_', '')
                    quantity = int(value)
                    if quantity > 0:
                        item = DocumentItem.objects.get(pk=item_pk, document=document)
                        item.quantity = quantity
                        item.save()
                except (ValueError, DocumentItem.DoesNotExist):
                    pass
        
        # Сохраняем статус как "saved"
        document.status = 'saved'
        document.save()
        
        messages.success(request, 'Изменения сохранены')
        
        # HTMX-запрос - возвращаем частичный HTML
        if 'HX-Request' in request.headers:
            items = document.items.all()
            return render(request, 'warehouse/partials/document_items.html', {
                'document': document,
                'items': items,
            })
        
        return redirect('warehouse:document-detail', pk=pk)
    
    return redirect('warehouse:document-detail', pk=pk)


@login_required
def document_mark_deleted(request, pk):
    """Пометка документа на удаление (как в 1С)"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        try:
            DocumentService.mark_deleted(document)
            messages.success(request, 'Документ помечен на удаление')
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('warehouse:document-list')
    
    return redirect('warehouse:document-detail', pk=pk)


@login_required
def document_unmark_deleted(request, pk):
    """Снятие пометки на удаление"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        try:
            DocumentService.unmark_deleted(document)
            messages.success(request, 'Пометка на удаление снята')
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('warehouse:document-detail', pk=pk)
    
    return redirect('warehouse:document-detail', pk=pk)


# Отчеты
from .reports import report_stock as reports_stock, report_movement as reports_movement, report_supplier as reports_supplier

@login_required
def report_stock(request):
    """Отчет по остаткам на складах"""
    warehouses = Warehouse.objects.annotate(
        tire_count=Count('tire')
    ).order_by('name')
    
    # Группировка по номенклатуре
    from tires.models import Tire
    stock_by_product = Tire.objects.filter(is_active=True).values(
        'product_name', 'warehouse__name'
    ).annotate(
        count=Count('id'),
        qr_codes=Count('qr_code')
    ).order_by('product_name', 'warehouse__name')
    
    return render(request, 'warehouse/reports/stock.html', {
        'warehouses': warehouses,
        'stock_by_product': stock_by_product,
    })


@login_required
def report_movement(request):
    """Отчет по движению шин"""
    movements = WarehouseMovement.objects.select_related('document', 'tire', 'from_warehouse', 'to_warehouse').order_by('-movement_date')
    
    # Фильтрация
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    warehouse_filter = request.GET.get('warehouse', '')
    
    if from_date:
        movements = movements.filter(movement_date__gte=from_date)
    if to_date:
        movements = movements.filter(movement_date__lte=to_date)
    if warehouse_filter:
        movements = movements.filter(
            Q(from_warehouse_id=warehouse_filter) | Q(to_warehouse_id=warehouse_filter)
        )
    
    # Подсчет статистики
    total_in = movements.filter(movement_type='in').count()
    total_out = movements.filter(movement_type='out').count()
    total_transfer = movements.filter(movement_type='transfer').count()
    
    paginator = Paginator(movements, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'warehouse/reports/movement.html', {
        'page_obj': page_obj,
        'total_in': total_in,
        'total_out': total_out,
        'total_transfer': total_transfer,
        'from_date': from_date,
        'to_date': to_date,
        'warehouse_filter': warehouse_filter,
    })


@login_required
def report_supplier(request):
    """Отчет по поставщикам"""
    suppliers = Supplier.objects.annotate(
        tire_count=Count('tire')
    ).order_by('name')
    
    # Данные по каждой поставке
    from tires.models import Tire
    supplier_tires = Tire.objects.select_related('supplier').order_by('-arrival_date')
    
    return render(request, 'warehouse/reports/supplier.html', {
        'suppliers': suppliers,
        'supplier_tires': supplier_tires,
    })
