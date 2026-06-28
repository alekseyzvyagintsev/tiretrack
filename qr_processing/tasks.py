from celery import shared_task
import re
import PyPDF2
import pdfplumber
from .models import FileImport
from tires.models import Tire, Warehouse, Supplier


@shared_task
def process_qr_file(file_import_id):
    """
    Асинхронная задача для обработки файла с QR-кодами
    """
    try:
        file_import = FileImport.objects.get(id=file_import_id)
        file_path = file_import.file.path
        
        # Извлечение QR-кодов из файла
        qr_codes = extract_qr_codes(file_path, file_import.file_type)
        
        success_count = 0
        error_count = 0
        log_messages = []
        
        # Получение склада по умолчанию (Основной)
        warehouse, _ = Warehouse.objects.get_or_create(
            name='Основной склад',
            defaults={'warehouse_type': 'main'}
        )
        
        # Обработка каждого QR-кода
        for qr_code in qr_codes:
            try:
                # Проверка в системе "Честный Знак" (здесь имитация)
                tire_data = verify_with_honest_sign(qr_code)
                
                if tire_data:
                    # Создание или обновление шины в базе данных
                    tire, created = Tire.objects.get_or_create(
                        qr_code=qr_code,
                        defaults={
                            'brand': tire_data.get('brand'),
                            'model': tire_data.get('model'),
                            'size': tire_data.get('size'),
                            'warehouse': warehouse
                        }
                    )
                    
                    success_count += 1
                    log_messages.append(f"QR-код {qr_code} успешно обработан")
                else:
                    error_count += 1
                    log_messages.append(f"QR-код {qr_code} не найден в системе Честный Знак")
                    
            except Exception as e:
                error_count += 1
                log_messages.append(f"Ошибка при обработке QR-кода {qr_code}: {str(e)}")
        
        # Обновление записи об импорте
        file_import.processed = True
        file_import.success_count = success_count
        file_import.error_count = error_count
        file_import.log = "\n".join(log_messages)
        file_import.save()
        
        return f"Обработано {success_count} QR-кодов, ошибок: {error_count}"
        
    except Exception as e:
        file_import = FileImport.objects.get(id=file_import_id)
        file_import.processed = True
        file_import.error_count = 1
        file_import.log = f"Критическая ошибка: {str(e)}"
        file_import.save()
        return f"Ошибка при обработке файла: {str(e)}"


def extract_qr_codes(file_path, file_type):
    """
    Извлечение QR-кодов из файла
    """
    qr_codes = []
    
    try:
        if file_type == 'txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # Поиск QR-кодов (простая реализация)
                pattern = re.compile(r'[A-Z0-9]{10,}')
                qr_codes = pattern.findall(content)
                
        elif file_type == 'pdf':
            # Извлечение текста из PDF
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pattern = re.compile(r'[A-Z0-9]{10,}')
                        qr_codes.extend(pattern.findall(text))
            
            # Альтернативный метод с PyPDF2
            if not qr_codes:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text:
                            pattern = re.compile(r'[A-Z0-9]{10,}')
                            qr_codes.extend(pattern.findall(text))
                            
    except Exception as e:
        print(f"Ошибка при извлечении QR-кодов: {e}")
    
    return qr_codes


def verify_with_honest_sign(qr_code):
    """
    Проверка QR-кода в системе "Честный Знак"
    В реальной системе здесь будет API-запрос
    """
    # Имитация данных из системы "Честный Знак"
    return {
        'qr_code': qr_code,
        'brand': 'Производитель из Честного Знака',
        'model': 'Модель из Честного Знака',
        'size': '295/80R22.5',
        'owner': 'Основной склад'
    }
