from nechestniy_znak import Crpt
import json

def encrypt(text) -> None | list | dict | str:
    crpt = Crpt()
    if text:
        try:
            return(crpt.infoFromDataMatrix(text))  # Из Data Matrix
        except Exception as ex:
            print(f"Error: {str(ex)}")
            return None

def parse_tire_data(qr_code, honest_sign_data):
    """
    Парсит данные из ответа Честного Знака и создает данные для шины
    
    Args:
        qr_code: QR-код или Data Matrix
        honest_sign_data: данные из системы "Честный Знак"
        
    Returns:
        dict: данные для создания шины или None если good_attrs пуст
    """
    if not honest_sign_data or not isinstance(honest_sign_data, dict):
        return None
    
    # Данные находятся в catalogData[0].good_attrs
    if 'catalogData' not in honest_sign_data or not honest_sign_data['catalogData']:
        return None
    
    catalog_data = honest_sign_data['catalogData'][0]
    good_attrs = catalog_data.get('good_attrs', [])
    
    if not good_attrs:
        return None
    
    # Получаем productName из catalogData
    product_name = catalog_data.get('good_name', '')
    
    # Получаем brand из catalogData
    brand = catalog_data.get('brand_name', '')
    
    pars_model = ''
    pars_size = ''
    
    # Словарь для хранения значений атрибутов
    attr_values = {}
    
    for attr in good_attrs:
        attr_name = attr.get('attr_name', '')
        attr_value = attr.get('attr_value', '')
        attr_values[attr_name] = attr_value
    
    # Парсим модель из good_attrs:
    # из "attr_name": "Модель / артикул производителя" по ключу "attr_value"
    # +
    # из "attr_name": "Индекс нагрузки на шину" по ключу "attr_value"
    model_part = attr_values.get('Модель / артикул производителя', '')
    load_index_part = attr_values.get('Индекс нагрузки на шину', '')
    
    # Складываем с пробелами
    parts = []
    if model_part:
        parts.append(model_part)
    if load_index_part:
        parts.append(load_index_part)
    pars_model = ' '.join(parts)
    
    # Парсим размер из good_attrs:
    # из "attr_name": "Ширина профиля шины (камеры), мм/дюйм" по ключу "attr_value"
    # +/+ из "attr_name": "Номинальное отношение высоты профиля шины к его ширине, %" по ключу "attr_value" (если "attr_value": "НЕ КЛАССИФИЦИРОВАНО" то "attr_value": "80")
    # +R+ из "attr_name": "Номинальный посадочный диаметр обода, дюйм" по ключу "attr_value"
    width_part = attr_values.get('Ширина профиля шины (камеры), мм/дюйм', '')
    ratio_part = attr_values.get('Номинальное отношение высоты профиля шины к его ширине, %', '')
    diameter_part = attr_values.get('Номинальный посадочный диаметр обода, дюйм', '')
    
    # Если ratio_part == "НЕ КЛАССИФИЦИРОВАНО", заменяем на "80"
    if ratio_part == 'НЕ КЛАССИФИЦИРОВАНО':
        ratio_part = '80'
    
    # Складываем без пробелов: ширина+соотношение+R+диаметр
    pars_size = f"{width_part}/{ratio_part}R{diameter_part}"
    
    return {
        'qr_code': qr_code,
        'brand': brand,
        'model': pars_model,
        'size': pars_size,
        'product_name': product_name,
        'honest_sign_data': honest_sign_data
    }
