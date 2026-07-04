from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Count
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

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
    """Создание нового документа - обработка POST запроса"""
    from .services import DocumentService
    
    if request.method != 'POST':
        messages.error(request, 'Некорректный метод запроса')
        return redirect('warehouse:document-list')
    
    form = DocumentForm(request.POST)
    if form.is_valid():
        try:
            data = {
                'document_type': form.cleaned_data['document_type'],
                'from_warehouse': form.cleaned_data['from_warehouse'],
                'to_warehouse': form.cleaned_data['to_warehouse'],
                'notes': form.cleaned_data.get('notes', ''),
                'document_date': form.cleaned_data.get('document_date', timezone.now().date()),
            }
            document = DocumentService.create(data, request.user)
            messages.success(request, 'Документ создан.')
            return redirect('warehouse:document-detail', pk=document.pk)
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, 'warehouse/document_detail.html', {
                'form': form,
                'document': None,
            })
    else:
        messages.error(request, 'Ошибка при создании документа')
        return render(request, 'warehouse/document_detail.html', {
            'form': form,
            'document': None,
        })


@login_required
def document_new(request):
    """Создание нового документа - показ пустой формы"""
    from django.utils import timezone
    
    document_types = DocumentType.objects.filter(is_active=True)
    warehouses = Warehouse.objects.all()
    
    # Проверка наличия обязательных данных
    if not document_types.exists():
        messages.error(request, 'Нет доступных типов документов. Создайте типы документов в админке.')
        return redirect('warehouse:document-list')
    
    if not warehouses.exists():
        messages.error(request, 'Нет доступных складов. Создайте склады в админке.')
        return redirect('warehouse:document-list')
    
    return render(request, 'warehouse/document_detail.html', {
        'form': DocumentForm(),
        'document': None,
        'document_types': document_types,
        'warehouses': warehouses,
        'today': timezone.now().date().strftime('%Y-%m-%d'),
    })


@login_required
def document_detail(request, pk):
    """Детальный просмотр документа"""
    from django.utils import timezone
    from django.core.exceptions import ValidationError
    
    document = get_object_or_404(Document, pk=pk)
    warehouses = Warehouse.objects.all()
    document_types = DocumentType.objects.filter(is_active=True)
    
    # Обработка POST запроса (редактирование документа)
    if request.method == 'POST' and document.can_edit():
        form = DocumentForm(request.POST, instance=document, document=document)
        if form.is_valid():
            doc = form.save()
            messages.success(request, 'Документ обновлен')
            return redirect('warehouse:document-detail', pk=doc.pk)
        else:
            messages.error(request, 'Ошибка при обновлении документа')
    else:
        form = DocumentForm(instance=document, document=document)
    
    context = {
        'document': document,
        'warehouses': warehouses,
        'document_types': document_types,
        'form': form,
        'items': document.items.all(),
        'today': timezone.now().date().strftime('%Y-%m-%d'),
    }
    
    return render(request, 'warehouse/document_detail.html', context)


@login_required
def document_add_item(request, pk):
    """Добавление товара в документ"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        quantity = int(request.POST.get('quantity', 1))
        
        if not product_name:
            messages.error(request, 'Выберите номенклатуру')
            return redirect('warehouse:document-detail', pk=pk)
        
        if quantity < 1:
            messages.error(request, 'Количество должно быть больше 0')
            return redirect('warehouse:document-detail', pk=pk)
        
        # Извлекаем nomenclature_key из product_name (size+brand+model)
        # product_name должен содержать size brand model в этом формате
        from tires.models import Tire
        nomenclature_key = product_name
        
        # Проверяем наличие активных шин с этой номенклатурой на складе отправления
        # Сортировка: старые шины вперёд (по created_at по возрастанию)
        available_tires = Tire.objects.filter(
            product_name=product_name,
            warehouse_id=document.from_warehouse_id,
            is_active=True
        ).order_by('created_at')
        
        if not available_tires.exists():
            messages.error(request, f'Нет доступных шин с номенклатурой {product_name}')
            return redirect('warehouse:document-detail', pk=pk)
        
        # Проверяем достаточно ли шин для добавления
        if available_tires.count() < quantity:
            messages.error(request, f'Недостаточно шин. Доступно {available_tires.count()} шт., добавить {quantity}')
            return redirect('warehouse:document-detail', pk=pk)
        
        # Проверяем, существует ли уже позиция с этой номенклатурой
        existing_item = DocumentItem.objects.filter(
            document=document,
            nomenclature_key=nomenclature_key
        ).first()
        
        if existing_item:
            # Если позиция уже существует, проверяем лимит
            currently_added = existing_item.tires.count()
            
            # Добавляем только если есть свободные шины
            if currently_added + quantity > available_tires.count():
                messages.error(request, f'Недостаточно шин для добавления {quantity} позиций')
                return redirect('warehouse:document-detail', pk=pk)
            
            # Добавляем шины (старые вперёд)
            tires_to_add = available_tires[currently_added:currently_added + quantity]
            existing_item.tires.add(*tires_to_add)
            existing_item.quantity = currently_added + quantity
            existing_item.save()
            
            messages.success(request, f'Добавлено {quantity} шин номенклатуры {product_name}')
        else:
            # Создаем новую позицию с указанным количеством
            item = DocumentItem.objects.create(
                document=document,
                product_name=product_name,
                nomenclature_key=nomenclature_key,
                quantity=quantity,
            )
            # Привязываем шины (старые вперёд)
            tires_to_add = available_tires[:quantity]
            item.tires.add(*tires_to_add)
            item.refresh_from_db()  # Обновляем объект из БД
            
            messages.success(request, f'Номенклатура {product_name} добавлена в документ ({quantity} шин)')
        
        # HTMX-запрос - возвращаем частичный HTML
        if 'HX-Request' in request.headers:
            return render(request, 'warehouse/partials/document_items.html', {
                'document': document,
                'items': document.items.all(),
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
        try:
            DocumentService.delete_item(document, item)
            messages.success(request, 'Позиция удалена из документа')
        except ValidationError as e:
            messages.error(request, str(e))
        
        # HTMX-запрос - возвращаем частичный HTML
        is_hx_request = any(h in request.headers for h in ['hx-request', 'HX-Request', 'hx_request', 'Hx-Request', 'hxRequest'])
        if is_hx_request:
            return render(request, 'warehouse/partials/document_items.html', {
                'document': document,
                'items': document.items.all(),
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
        
        # Сохраняем статус как "saved", если еще не saved
        if document.status != 'saved':
            document.status = 'saved'
            document.save()
        
        # HTMX-запрос - возвращаем частичный HTML
        if 'HX-Request' in request.headers:
            return render(request, 'warehouse/partials/document_items.html', {
                'document': document,
                'items': document.items.all(),
            })
        
        messages.success(request, 'Изменения сохранены')
        return redirect('warehouse:document-detail', pk=pk)


def _document_list_htmx_response(request, documents, show_deleted=False, status_filter='', type_filter='', query=''):
    """Общий метод для формирования HTMX ответа со списком документов"""
    # Подсчет статистики
    total_count = documents.count()
    draft_count = documents.filter(status='draft').count()
    saved_count = documents.filter(status='saved').count()
    posted_count = documents.filter(status='posted').count()
    deleted_count = documents.filter(deleted=True).count()
    
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'warehouse/partials/document_list.html', {
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


def _document_toggle_deleted(request, pk, mark_deleted=True):
    """Общий метод для пометки/снятия пометки на удаление"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        try:
            if mark_deleted:
                DocumentService.mark_deleted(document)
                messages.success(request, 'Документ помечен на удаление')
            else:
                DocumentService.unmark_deleted(document)
                messages.success(request, 'Пометка на удаление снята')
        except ValidationError as e:
            messages.error(request, str(e))
        
        # HTMX-запрос - возвращаем частичный HTML со списком документов
        if 'HX-Request' in request.headers:
            show_deleted = request.GET.get('show_deleted', 'false') == 'true'
            
            base_query = Document.objects.select_related('document_type', 'from_warehouse', 'to_warehouse', 'created_by')
            documents = base_query.order_by('-document_date') if show_deleted else base_query.filter(deleted=False).order_by('-document_date')
            
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
            
            return _document_list_htmx_response(request, documents, show_deleted, status_filter, type_filter, query)
        
        return redirect('warehouse:document-list')
    
    return redirect('warehouse:document-detail', pk=pk)


@login_required
def document_mark_deleted(request, pk):
    """Пометка документа на удаление (как в 1С)"""
    return _document_toggle_deleted(request, pk, mark_deleted=True)


@login_required
def document_unmark_deleted(request, pk):
    """Снятие пометки на удаление"""
    return _document_toggle_deleted(request, pk, mark_deleted=False)


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
    
    # Получение параметров фильтрации
    supplier_id = request.GET.get('supplier_id', '')
    our_supplier = request.GET.get('our_supplier', '')
    
    # Формирование списка шин
    from tires.models import Tire
    from tires.utils import search_tire_nomenclature
    
    # Если выбран конкретный поставщик
    if supplier_id:
        supplier = get_object_or_404(Supplier, pk=supplier_id)
        tires = Tire.objects.filter(supplier=supplier, is_active=True).select_related('warehouse', 'supplier').order_by('-created_at')
        supplier_tires = search_tire_nomenclature('', warehouse_id=None)
        supplier_tires = [t for t in supplier_tires if t.get('supplier') and t['supplier'].id == int(supplier_id)]
    elif our_supplier:
        # Наше - без поставщика (supplier=None)
        tires = Tire.objects.filter(supplier__isnull=True, is_active=True).select_related('warehouse').order_by('-created_at')
        supplier_tires = search_tire_nomenclature('', warehouse_id=None)
        supplier_tires = [t for t in supplier_tires if not t.get('supplier')]
    else:
        # Все поставщики
        tires = Tire.objects.filter(is_active=True).select_related('warehouse', 'supplier').order_by('-created_at')
        supplier_tires = search_tire_nomenclature('', warehouse_id=None)
    
    # Подсчёт статистики
    all_tires_count = Tire.objects.filter(is_active=True).count()
    our_supplier_tires_count = Tire.objects.filter(supplier__isnull=True, is_active=True).count()
    
    return render(request, 'warehouse/reports/supplier.html', {
        'suppliers': suppliers,
        'supplier_tires': supplier_tires,
        'all_tires_count': all_tires_count,
        'our_supplier_tires_count': our_supplier_tires_count,
        'supplier_id': supplier_id,
        'our_supplier': our_supplier,
    })
