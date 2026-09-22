from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

from tires.models import Warehouse, Supplier
from tires.services import UploadService
from .models import FileImport, ExportBatch


@login_required
def file_import(request):
    """Загрузка QR-кодов из файла (S-03)."""
    # Фильтруем склады по площадке пользователя
    if hasattr(request.user, 'platform') and request.user.platform:
        warehouses = Warehouse.objects.filter(platform=request.user.platform)
    else:
        warehouses = Warehouse.objects.all()

    suppliers = Supplier.objects.all()

    if request.method == 'POST':
        warehouse_id = request.POST.get('warehouse')
        supplier_id = request.POST.get('supplier')
        file = request.FILES.get('file')
        text_data = request.POST.get('text', '').strip()

        # Валидация
        if not file and not text_data:
            messages.error(request, 'Выберите файл или введите QR-коды')
            return render(request, 'qr/import.html', {
                'warehouses': warehouses,
                'suppliers': suppliers,
            })

        if not warehouse_id:
            messages.error(request, 'Выберите склад')
            return render(request, 'qr/import.html', {
                'warehouses': warehouses,
                'suppliers': suppliers,
            })

        warehouse = get_object_or_404(Warehouse, id=warehouse_id)

        # Получаем поставщика (опционально)
        supplier = None
        if supplier_id:
            supplier = get_object_or_404(Supplier, id=supplier_id)

        # Читаем QR-коды
        try:
            if file:
                content = file.read().decode('utf-8')
                lines = [line.strip() for line in content.split('\n') if line.strip()]
            else:
                lines = [line.strip() for line in text_data.split('\n') if line.strip()]
        except Exception as e:
            messages.error(request, f'Ошибка при чтении файла: {e}')
            return render(request, 'qr/import.html', {
                'warehouses': warehouses,
                'suppliers': suppliers,
            })

        if not lines:
            messages.error(request, 'Файл не содержит QR-кодов')
            return render(request, 'qr/import.html', {
                'warehouses': warehouses,
                'suppliers': suppliers,
            })

        # Ограничение на количество строк
        if len(lines) > 100000:
            messages.error(request, 'Файл содержит более 100 000 строк')
            return render(request, 'qr/import.html', {
                'warehouses': warehouses,
                'suppliers': suppliers,
            })

        # Загрузка через UploadService
        service = UploadService(warehouse=warehouse, supplier=supplier)
        report = service.upload(lines)

        # Создаём запись FileImport
        file_import = FileImport.objects.create(
            file=file if file else None,
            file_type='txt',
            uploaded_by=request.user,
            processed=True,
            success_count=report.created,
            error_count=report.duplicates + report.unrecognized + report.honest_sign_errors,
            log=str(report.summary),
            details=report.details,
        )

        # Сообщения
        if report.created > 0:
            messages.success(request, f'Успешно создано: {report.created}')
        if report.duplicates > 0:
            messages.warning(request, f'Дубликатов пропущено: {report.duplicates}')
        if report.unrecognized > 0:
            messages.warning(request, f'Нераспознанных: {report.unrecognized}')
        if report.honest_sign_errors > 0:
            messages.error(request, f'Ошибок Честного знака: {report.honest_sign_errors}')

        # Редирект на отчёт
        return redirect('qr_processing:upload-report', file_import_id=file_import.id)

    return render(request, 'qr/import.html', {
        'warehouses': warehouses,
        'suppliers': suppliers,
    })


@login_required
def upload_report(request, file_import_id):
    """Отчёт о загрузке (S-04)."""
    file_import = get_object_or_404(FileImport, id=file_import_id)

    # Парсим summary из log
    summary = {}
    if file_import.log:
        try:
            import json
            summary = json.loads(file_import.log)
        except (json.JSONDecodeError, ValueError):
            pass

    return render(request, 'qr/export.html', {
        'file_import': file_import,
        'summary': summary,
    })


@login_required
def import_list(request):
    """Список импортов."""
    imports = FileImport.objects.all().order_by('-upload_date')

    paginator = Paginator(imports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'qr/import_list.html', {
        'page_obj': page_obj,
    })


@login_required
def export_batch_create(request):
    """Создание пакета экспорта."""
    if request.method == 'POST':
        name = request.POST.get('name')
        export_format = request.POST.get('export_format')

        ExportBatch.objects.create(
            name=name,
            export_format=export_format,
            created_by=request.user,
        )

        messages.success(request, f'Пакет экспорта "{name}" успешно создан')
        return redirect('qr_processing:export-batch-list')

    return render(request, 'qr/export_batch_form.html')


@login_required
def export_batch_list(request):
    """Список пакетов экспорта."""
    exports = ExportBatch.objects.all().order_by('-created_at')

    paginator = Paginator(exports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'qr/export_batch_list.html', {
        'page_obj': page_obj,
    })
