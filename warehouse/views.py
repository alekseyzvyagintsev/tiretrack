"""Views для документов списания/выкупа."""
from io import BytesIO
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
import qrcode

from tires.models import TireNomenclature, TireCode, Platform
from users.models import UserRoles
from .models import Document, DocumentItem, DocType
from .services import DocumentService


@login_required
def homepage(request):
    """Дашборд (S-02)."""
    from tires.models import TireCode

    user = request.user
    platform = user.platform

    # Счётчики
    total_codes = TireCode.objects.filter(warehouse__platform=platform).count()
    active_codes = TireCode.objects.filter(
        warehouse__platform=platform, is_active=True
    ).count()
    used_codes = total_codes - active_codes

    # Документы по статусам
    docs = Document.objects.filter(
        Q(source_platform=platform) | Q(writeoff_platform=platform)
    )
    draft_count = docs.filter(status='draft').count()
    saved_count = docs.filter(status='saved').count()
    posted_count = docs.filter(status='posted').count()

    # Последние 5 документов
    recent_documents = docs.order_by('-created_at')[:5]

    return render(request, 'warehouse/home.html', {
        'total_codes': total_codes,
        'active_codes': active_codes,
        'used_codes': used_codes,
        'draft_count': draft_count,
        'saved_count': saved_count,
        'posted_count': posted_count,
        'recent_documents': recent_documents,
        'warehouses': platform.warehouses.all() if platform else [],
    })


def _check_document_permission(request, document):
    """Проверка прав доступа к документу.

    Returns:
        HttpResponseForbidden или None
    """
    user = request.user

    if user.role == UserRoles.MANAGER:
        # Manager: свои документы — полный доступ, чужие — только чтение
        if document.source_platform != user.platform:
            # Чужая площадка — только чтение
            return None  # Разрешаем чтение
        return None  # Полный доступ

    # Storekeeper: только свои документы
    if document.author != user:
        return HttpResponseForbidden('У вас нет доступа к этому документу')

    return None


from django.http import HttpResponseForbidden


@login_required
def document_list(request):
    """Список документов (S-05)."""
    querysets = Document.objects.select_related(
        'doc_type', 'author', 'source_platform', 'writeoff_platform',
        'source_warehouse', 'target_warehouse'
    ).prefetch_related('items__nomenclature')

    user = request.user

    if user.role == UserRoles.MANAGER:
        # Manager: документы своей площадки + чужие (read-only)
        querysets = querysets.filter(
            Q(source_platform=user.platform) |
            Q(writeoff_platform=user.platform)
        )
    else:
        # Storekeeper: только свои документы
        querysets = querysets.filter(author=user)

    # Фильтры
    doc_type = request.GET.get('doc_type')
    status = request.GET.get('status')
    source_platform = request.GET.get('source_platform')

    if doc_type:
        querysets = querysets.filter(doc_type_id=doc_type)
    if status:
        querysets = querysets.filter(status=status)
    if source_platform:
        querysets = querysets.filter(source_platform_id=source_platform)

    # Сортировка
    querysets = querysets.order_by('-created_at')

    # Пагинация
    paginator = Paginator(querysets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Статистика
    stats = {
        'total': Document.objects.count(),
        'draft': Document.objects.filter(status='draft').count(),
        'saved': Document.objects.filter(status='saved').count(),
        'posted': Document.objects.filter(status='posted').count(),
        'marked_deleted': Document.objects.filter(status='marked_deleted').count(),
    }

    return render(request, 'warehouse/document_list.html', {
        'page_obj': page_obj,
        'stats': stats,
        'doc_types': DocType.objects.filter(is_active=True),
        'platforms': Platform.objects.all(),
    })


@login_required
def document_create(request):
    """Создание нового документа (S-06)."""
    if request.method == 'POST':
        doc_type_id = request.POST.get('doc_type')
        source_warehouse_id = request.POST.get('source_warehouse')
        target_warehouse_id = request.POST.get('target_warehouse')
        notes = request.POST.get('notes', '')

        doc_type = get_object_or_404(DocType, id=doc_type_id)
        source_warehouse = get_object_or_404(
            request.user.platform.warehouses,
            id=source_warehouse_id
        )

        target_warehouse = None
        if target_warehouse_id:
            target_warehouse = get_object_or_404(
                request.user.platform.warehouses,
                id=target_warehouse_id
            )

        document = DocumentService.create(
            user=request.user,
            doc_type=doc_type,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
            notes=notes,
        )

        messages.success(request, 'Документ создан')
        return redirect('warehouse:document-detail', pk=document.id)

    # GET — форма создания
    doc_types = DocType.objects.filter(is_active=True)
    warehouses = request.user.platform.warehouses.all()

    return render(request, 'warehouse/document_form.html', {
        'doc_types': doc_types,
        'warehouses': warehouses,
        'doc_type': None,
    })


@login_required
def document_detail(request, pk):
    """Карточка документа (S-07 — S-10)."""
    document = get_object_or_404(
        Document.objects.select_related(
            'doc_type', 'author', 'source_platform', 'writeoff_platform',
            'source_warehouse', 'target_warehouse'
        ).prefetch_related('items__nomenclature'),
        pk=pk
    )

    # Проверка прав
    permission_check = _check_document_permission(request, document)
    if permission_check:
        return permission_check

    # Storekeeper не видит чужие документы — 404
    if request.user.role == UserRoles.STOREKEEPER and document.author != request.user:
        raise get_object_or_404(Document, pk=-1)

    # Manager чужие документы — только чтение
    is_editable = (
        document.author == request.user and
        document.status in ('draft', 'saved') and
        not document.is_deleted
    )

    return render(request, 'warehouse/document_detail.html', {
        'document': document,
        'is_editable': is_editable,
        'is_manager': request.user.role == UserRoles.MANAGER,
        'is_storekeeper': request.user.role == UserRoles.STOREKEEPER,
    })


@login_required
@transaction.atomic
def document_save(request, pk):
    """Сохранить черновик: draft → saved."""
    document = get_object_or_404(Document, pk=pk)

    if document.author != request.user:
        return HttpResponseForbidden()

    try:
        document = DocumentService.save_draft(document)
        messages.success(request, f'Документ сохранён: {document.number}')
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect('warehouse:document-detail', pk=document.id)


@login_required
@transaction.atomic
def document_post(request, pk):
    """Проведение документа."""
    document = get_object_or_404(Document, pk=pk)

    if document.author != request.user:
        return HttpResponseForbidden()

    try:
        document = DocumentService.post_document(document)
        messages.success(request, f'Документ проведён: {document.number}')
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect('warehouse:document-detail', pk=document.id)


@login_required
@transaction.atomic
def document_unpost(request, pk):
    """Распроведение документа."""
    document = get_object_or_404(Document, pk=pk)

    if document.author != request.user:
        return HttpResponseForbidden()

    try:
        document = DocumentService.unpost_document(document)
        messages.success(request, 'Документ распроведён')
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect('warehouse:document-detail', pk=document.id)


@login_required
@transaction.atomic
def document_mark_deleted(request, pk):
    """Пометить документ на удаление."""
    document = get_object_or_404(Document, pk=pk)

    if document.author != request.user:
        return HttpResponseForbidden()

    try:
        document = DocumentService.mark_deleted(document)
        messages.success(request, 'Документ помечен на удаление')
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect('warehouse:document-list')


@login_required
def nomenclature_search(request):
    """AJAX: поиск номенклатуры (A1)."""
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))

    if not query:
        return JsonResponse({'results': []})

    nomenclatures = TireNomenclature.objects.filter(
        Q(brand__icontains=query) |
        Q(model__icontains=query) |
        Q(size__icontains=query) |
        Q(product_name__icontains=query)
    ).filter(is_active=True)[:limit]

    results = []
    for n in nomenclatures:
        results.append({
            'id': n.id,
            'display_name': n.display_name(),
            'brand': n.brand,
            'model': n.model,
            'size': n.size,
        })

    return JsonResponse({'results': results})


@login_required
@transaction.atomic
def document_add_item(request, pk):
    """AJAX: добавление строки в документ (A2)."""
    document = get_object_or_404(Document, pk=pk)

    if document.status not in ('draft', 'saved'):
        return JsonResponse({'error': 'Можно добавлять строки только в черновик или сохранённый документ'}, status=400)

    if document.author != request.user:
        return HttpResponseForbidden()

    nomenclature_id = request.POST.get('nomenclature_id')
    quantity = int(request.POST.get('quantity', 1))

    nomenclature = get_object_or_404(TireNomenclature, id=nomenclature_id)

    try:
        item, is_duplicate = DocumentService.add_item(document, nomenclature, quantity)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({
        'item_id': item.id,
        'nomenclature': item.nomenclature.display_name(),
        'quantity': item.quantity,
        'is_duplicate': is_duplicate,
    })


@login_required
@transaction.atomic
def document_update_item(request, pk, item_pk):
    """AJAX: обновление количества в строке (A3)."""
    document = get_object_or_404(Document, pk=pk)
    item = get_object_or_404(DocumentItem, pk=item_pk)

    if document.status not in ('draft', 'saved'):
        return JsonResponse({'error': 'Можно редактировать только черновик или сохранённый документ'}, status=400)

    if document.author != request.user:
        return HttpResponseForbidden()

    quantity = int(request.POST.get('quantity', 1))

    try:
        item = DocumentService.update_item(item, quantity)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({
        'quantity': item.quantity,
    })


@login_required
@transaction.atomic
def document_delete_item(request, pk, item_pk):
    """AJAX: удаление строки из документа (A4)."""
    document = get_object_or_404(Document, pk=pk)
    item = get_object_or_404(DocumentItem, pk=item_pk)

    if document.status not in ('draft', 'saved'):
        return JsonResponse({'error': 'Можно удалять строки только из черновика или сохранённого документа'}, status=400)

    if document.author != request.user:
        return HttpResponseForbidden()

    DocumentService.delete_item(item)

    return JsonResponse({'success': True})


@login_required
@transaction.atomic
def document_autosave(request, pk):
    """AJAX: автосохранение черновика (A8)."""
    document = get_object_or_404(Document, pk=pk)

    if document.status != 'draft' or document.author != request.user:
        return JsonResponse({'error': 'Автосохранение доступно только для черновиков автора'}, status=400)

    # Сохраняем состав (items) — просто подтверждаем, что черновик существует
    return JsonResponse({'success': True})


@login_required
def document_codes(request, pk):
    """Экранное отображение кодов (S-11)."""
    document = get_object_or_404(Document, pk=pk)

    if document.status != 'posted':
        return HttpResponseForbidden('Только для проведённых документов')

    codes = document.tire_codes.all().order_by('created_at')

    # Фильтр по номенклатуре
    nomenclature_id = request.GET.get('nomenclature')
    if nomenclature_id:
        codes = codes.filter(nomenclature_id=nomenclature_id)

    # Пагинация
    paginator = Paginator(codes, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'warehouse/document_codes.html', {
        'document': document,
        'page_obj': page_obj,
    })


@login_required
def counters_api(request):
    """AJAX: счётчики активных кодов (A5)."""
    from tires.models import TireCode
    from io import BytesIO
    from django.http import HttpResponse
    import qrcode
    from PIL import Image

    warehouse_id = request.GET.get('warehouse')
    nomenclature_id = request.GET.get('nomenclature')

    queryset = TireCode.objects.filter(is_active=True, is_used=False)

    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)
    if nomenclature_id:
        queryset = queryset.filter(nomenclature_id=nomenclature_id)

    count = queryset.count()

    return JsonResponse({'active': count})


@login_required
def code_card(request, code_id):
    """Карточка кода с DataMatrix (S-12)."""
    import base64

    code = get_object_or_404(
        TireCode.objects.select_related('nomenclature', 'warehouse'),
        pk=code_id
    )

    # Генерация DataMatrix-изображения
    qr_img = qrcode.make(code.qr_code)
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Конвертируем в data URI
    image_data = base64.b64encode(buffer.read()).decode('utf-8')
    qr_image_data = f"data:image/png;base64,{image_data}"

    return render(request, 'warehouse/code_card.html', {
        'code': code,
        'qr_image_data': qr_image_data,
    })
