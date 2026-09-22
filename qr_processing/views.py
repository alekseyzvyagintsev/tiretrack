from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
import json

from .models import FileImport, ExportBatch
from tires.models import Tire, Warehouse, Supplier
from .utils import encrypt, parse_tire_data


@login_required
def file_import(request):
    """Импорт QR-кодов из файла"""
    result = None
    check_result = None
    text = ''  # Инициализируем для GET-запроса
    warehouses = Warehouse.objects.all()
    suppliers = Supplier.objects.all()
    
    # GET - отображаем форму
    if request.method == 'GET':
        return render(request, 'qr/import.html', {
            'warehouses': warehouses,
            'suppliers': suppliers,
            'result': result,
            'check_result': check_result,
            'text': text,
        })
    
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        
        if text:
            check_result = encrypt(text)
            # Форматируем JSON если результат - строка с JSON или dict/list
            if isinstance(check_result, str):
                try:
                    parsed = json.loads(check_result)
                    check_result = json.dumps(parsed, indent=2, ensure_ascii=False)
                except (json.JSONDecodeError, ValueError):
                    pass  # Оставляем как есть если не JSON
            elif isinstance(check_result, (dict, list)):
                check_result = json.dumps(check_result, indent=2, ensure_ascii=False)
        
        # Обработка файла
        if 'file' in request.FILES:
            warehouse_id = request.POST.get('warehouse')
            supplier_id = request.POST.get('supplier')
            
            if not warehouse_id:
                messages.error(request, 'Пожалуйста, выберите целевой склад')
                return render(request, 'qr/import.html', {
                    'result': result,
                    'check_result': check_result,
                    'text': text,
                    'warehouses': Warehouse.objects.all(),
                    'suppliers': Supplier.objects.all(),
                })
            
            warehouse = get_object_or_404(Warehouse, id=warehouse_id)
            
            file = request.FILES.get('file')
            
            # Получаем список QR-кодов из файла
            qr_codes = []
            try:
                file_content = file.read().decode('utf-8')
                qr_codes = [line.strip() for line in file_content.split('\n') if line.strip()]
            except Exception as e:
                messages.error(request, f'Ошибка при чтении файла: {str(e)}')
                return render(request, 'qr/import.html', {
                    'result': result,
                    'check_result': check_result,
                    'text': text,
                    'warehouses': Warehouse.objects.all(),
                    'suppliers': Supplier.objects.all(),
                })
            
            if not qr_codes:
                messages.error(request, 'Файл не содержит QR-кодов')
                return render(request, 'qr/import.html', {
                    'result': result,
                    'check_result': check_result,
                    'text': text,
                    'warehouses': Warehouse.objects.all(),
                    'suppliers': Supplier.objects.all(),
                })
            
            # Получаем поставщика (опционально)
            supplier = None
            if supplier_id:
                supplier = get_object_or_404(Supplier, id=supplier_id)
            
            # Обрабатываем каждый QR-код
            success_count = 0
            error_count = 0
            error_messages = []
            created_tires = []  # Список созданных шин для отображения в результате
            
            for qr_code in qr_codes:
                try:
                    # Проверяем, не существует ли уже такая шина
                    if Tire.objects.filter(qr_code=qr_code).exists():
                        error_count += 1
                        error_messages.append(f"Шина с QR-кодом {qr_code} уже существует")
                        continue
                    
                    # Получаем данные из Честного Знака
                    honest_sign_data = encrypt(qr_code)
                    
                    if not honest_sign_data or not isinstance(honest_sign_data, dict):
                        error_count += 1
                        error_messages.append(f"Не удалось получить данные для QR-кода {qr_code}")
                        continue
                    
                    # Парсим данные для шины
                    tire_data = parse_tire_data(qr_code, honest_sign_data)
                    
                    if not tire_data:
                        # Проверяем, есть ли good_attrs
                        good_attrs = honest_sign_data.get('good_attrs', [])
                        if not good_attrs:
                            # Код не найден в Честном Знаке
                            error_count += 1
                            error_messages.append(f"Честный Знак не содержит QR-кода {qr_code} или код выведен из оборота")
                            continue
                        else:
                            error_count += 1
                            error_messages.append(f"Не удалось распарсить данные для QR-кода {qr_code}")
                            continue
                    
                    # Создаем шину
                    tire = Tire.objects.create(
                        qr_code=tire_data['qr_code'],
                        brand=tire_data['brand'],
                        model=tire_data['model'],
                        size=tire_data['size'],
                        product_name=tire_data['product_name'],
                        warehouse=warehouse,
                        supplier=supplier,
                        honest_sign_data=honest_sign_data
                    )
                    
                    success_count += 1
                    
                    # Сохраняем созданную шину для отображения в результате
                    created_tires.append({
                        'qr_code': qr_code,
                        'brand': tire_data['brand'],
                        'model': tire_data['model'],
                        'size': tire_data['size'],
                        'product_name': tire_data['product_name']
                    })
                    
                except Exception as e:
                    error_count += 1
                    error_messages.append(f"Ошибка при обработке QR-кода {qr_code}: {str(e)}")
            
            # Создаем запись об импорте
            file_import = FileImport.objects.create(
                file=file if file else None,
                file_type='txt' if file else 'txt',
                uploaded_by=request.user,
                processed=True,
                success_count=success_count,
                error_count=error_count,
                log='\n'.join(error_messages) if error_messages else 'Импорт завершен успешно'
            )
            
            if success_count > 0:
                messages.success(request, f'Успешно импортировано {success_count} шин')
            if error_count > 0:
                messages.warning(request, f'Ошибок при импорте: {error_count}')
            
            # Возвращаем результат для отображения в интерфейсе
            result_data = {
                'summary': {
                    'total': len(qr_codes),
                    'success': success_count,
                    'errors': error_count
                },
                'errors': error_messages[:10] if error_messages else [],  # Показываем не более 10 ошибок
                'created_tires': created_tires  # Список созданных шин
            }
            
            return render(request, 'qr/import.html', {
                'import_result': result_data,  # Результат импорта
                'check_result': check_result,
                'warehouses': Warehouse.objects.all(),
                'suppliers': Supplier.objects.all(),
            })
    
    return render(request, 'qr/import.html', {
        'result': result,
        'check_result': check_result,
        'text': text,
        'warehouses': Warehouse.objects.all(),
        'suppliers': Supplier.objects.all(),
        'recent_imports': FileImport.objects.all().order_by('-upload_date')[:3],
    })


@login_required
def import_list(request):
    """Список импортов"""
    imports = FileImport.objects.all().order_by('-upload_date')
    
    paginator = Paginator(imports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'qr/import_list.html', {
        'page_obj': page_obj,
    })


@login_required
def export_batch_create(request):
    """Создание пакета экспорта"""
    if request.method == 'POST':
        name = request.POST.get('name')
        export_format = request.POST.get('export_format')
        
        ExportBatch.objects.create(
            name=name,
            export_format=export_format,
            created_by=request.user
        )
        
        messages.success(request, f'Пакет экспорта "{name}" успешно создан')
        return redirect('qr_processing:export-batch-list')
    
    return render(request, 'qr/export_batch_form.html')


@login_required
def export_batch_list(request):
    """Список пакетов экспорта"""
    exports = ExportBatch.objects.all().order_by('-created_at')
    
    paginator = Paginator(exports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'qr/export_batch_list.html', {
        'page_obj': page_obj,
    })
