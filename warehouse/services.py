from django.db import transaction
from django.db.models import Count, Q
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Document, DocumentItem, WarehouseMovement
from tires.models import Tire


class DocumentService:
    """Сервисные функции для работы с документами"""
    
    @staticmethod
    @transaction.atomic
    def create(data, user):
        """
        Создание нового документа
        
        Args:
            data: словарь с данными формы (document_type, from_warehouse, to_warehouse, notes)
            user: текущий пользователь (creator)
        
        Returns:
            Document: созданный документ
        
        Raises:
            ValidationError: если данные невалидны или нет необходимых данных
        """
        from django.core.exceptions import ValidationError
        
        document_type = data.get('document_type')
        from_warehouse = data.get('from_warehouse')
        to_warehouse = data.get('to_warehouse')
        notes = data.get('notes', '')
        document_date = data.get('document_date', timezone.now().date())
        
        # Проверка наличия типа документа
        if not document_type:
            raise ValidationError('Тип документа не указан')
        
        # Проверка типа документа
        if not isinstance(document_type, DocumentType):
            document_type = DocumentType.objects.filter(pk=document_type).first()
            if not document_type:
                raise ValidationError('Указанный тип документа не найден')
        
        # Проверка наличия складов для разных типов документов
        if document_type.code == 'receipt':
            # Приемка - только to_warehouse
            if not to_warehouse:
                raise ValidationError('Укажите склад приемки')
        elif document_type.code == 'dispatch':
            # Отгрузка - только from_warehouse
            if not from_warehouse:
                raise ValidationError('Укажите склад отгрузки')
        elif document_type.code in ('movement', 'return'):
            # Перемещение и возврат - оба склада
            if not from_warehouse:
                raise ValidationError('Укажите склад отправления')
            if not to_warehouse:
                raise ValidationError('Укажите склад назначения')
        
        # Создание документа
        document = Document.objects.create(
            document_type=document_type,
            from_warehouse=from_warehouse,
            to_warehouse=to_warehouse,
            notes=notes,
            document_date=document_date,
            created_by=user,
        )
        
        # Генерация номера документа
        DocumentService.generate_document_number(document)
        document.status = 'saved'
        document.save()
        
        return document
    
    @staticmethod
    @transaction.atomic
    def post_document(document):
        """
        Проведение документа
        Переносит шины между складами и создает записи в истории
        """
        if document.status == 'posted':
            raise ValidationError('Документ уже проведён')
        
        if not document.items.exists():
            raise ValidationError('Нельзя провести пустой документ')
        
        # Меняем статус на "Проведён" через update(), чтобы обойти валидацию в save()
        Document.objects.filter(pk=document.pk).update(status='posted')
        document.status = 'posted'  # Обновляем локальный объект
        document.refresh_from_db()  # Обновляем объект из БД
        
        # Создаем запись в истории перемещений для каждой шины
        for item in document.items.all():
            # Сортируем шины: старые вперёд (по created_at по возрастанию)
            tires = item.tires.all().order_by('created_at')
            
            for tire in tires:
                warehouse_movement = WarehouseMovement.objects.create(
                    document=document,
                    tire=tire,
                    movement_type='transfer',
                    from_warehouse=document.from_warehouse,
                    to_warehouse=document.to_warehouse,
                    quantity=1,
                    notes=f"Документ {document.document_number}",
                )
                
                # Обновляем шину
                tire.warehouse = document.to_warehouse
                # Для отгрузки (dispatch) шины становятся неактивными
                # Для перемещения (movement) и других типов шины остаются активными
                if document.document_type.code == 'dispatch':
                    tire.is_active = False
                else:
                    tire.is_active = True
                tire.save()
        
        return document
    
    @staticmethod
    @transaction.atomic
    def unpost_document(document):
        """
        Отмена проведения документа
        Возвращает шины на исходный склад и удаляет связи с экземплярами
        Сохраняет список товаров (product_name) в DocumentItem
        """
        if document.status == 'draft':
            raise ValidationError('Документ не проведён')
        
        # Меняем статус на "Сохранен"
        document.status = 'saved'
        document.save()
        
        # Возвращаем шины на исходный склад
        for item in document.items.all():
            # Возвращаем каждую шину на исходный склад
            for tire in item.tires.all():
                tire.warehouse = document.from_warehouse
                tire.is_active = True  # Возвращаем активность
                tire.save()
        
        # Удаляем все связи с экземплярами шин
        # Список товаров (product_name) остаётся неизменным
        for item in document.items.all():
            item.tires.clear()
        
        return document
    
    @staticmethod
    @transaction.atomic
    def toggle_deleted(document, mark_deleted=True):
        """Пометка или снятие пометки на удаление"""
        action = 'пометить' if mark_deleted else 'снять'
        verb = 'помечен' if mark_deleted else 'снят'
        
        if mark_deleted:
            if document.deleted:
                raise ValidationError('Документ уже помечен на удаление')
            if not document.can_delete():
                raise ValidationError('Чтобы пометить на удаление, нужно отменить проведение документа')
            # Помечаем на удаление (для сохраненных документов)
            document.deleted = True
            document.status = 'deleted'
            document.save()
        else:
            if not document.deleted:
                raise ValidationError('Документ не помечен на удаление')
            # Снимаем пометку на удаление
            document.deleted = False
            document.status = 'saved'
            document.save()
        return document
    
    @staticmethod
    @transaction.atomic
    def update(document, data):
        """
        Обновление документа
        
        Args:
            document: документ для обновления
            data: словарь с обновленными данными
        
        Returns:
            Document: обновленный документ
        
        Raises:
            ValidationError: если обновление невозможно
        """
        from django.core.exceptions import ValidationError
        
        # Проверка, что документ можно редактировать
        if not document.can_edit():
            raise ValidationError('Нельзя редактировать этот документ')
        
        # Обновление полей
        if 'from_warehouse' in data:
            document.from_warehouse = data['from_warehouse']
        if 'to_warehouse' in data:
            document.to_warehouse = data['to_warehouse']
        if 'notes' in data:
            document.notes = data['notes']
        
        document.save()
        return document
    
    @staticmethod
    @transaction.atomic
    def mark_deleted(document):
        """Пометка документа на удаление (как в 1С)"""
        return DocumentService.toggle_deleted(document, mark_deleted=True)
    
    @staticmethod
    @transaction.atomic
    def unmark_deleted(document):
        """Снятие пометки на удаление"""
        return DocumentService.toggle_deleted(document, mark_deleted=False)
    
    @staticmethod
    @transaction.atomic
    def delete_item(document, item):
        """
        Удаление позиции из документа
        Если документ проведён - возвращает шины на исходный склад и удаляет связи
        """
        if document.status == 'posted':
            # Возвращаем шины на исходный склад
            for tire in item.tires.all():
                tire.warehouse = document.from_warehouse
                tire.is_active = True
                tire.save()
            # Удаляем связи с экземплярами шин
            item.tires.clear()
        
        # Удаляем позицию
        item.delete()
        
        return document
    
    @staticmethod
    def generate_document_number(document):
        """
        Генерация номера документа на основе типа и даты
        Формат: {PREFIX}-{YYYYMMDD}-{NNNN}
        """
        if not document.document_number:
            prefix = document.document_type.code[:3].upper()
            date_part = document.document_date.strftime('%Y%m%d')
            count = Document.objects.filter(
                document_type=document.document_type,
                document_date=document.document_date
            ).count() + 1
            document.document_number = f"{prefix}-{date_part}-{count:04d}"
        
        return document.document_number


class WarehouseService:
    """Сервисные функции для работы со складами"""
    
    @staticmethod
    def get_warehouse_stock(warehouse_id=None):
        """
        Получить остатки на складе/складах
        Возвращает количество шин по номенклатуре на складах
        """
        from tires.models import Tire
        
        if warehouse_id:
            tires = Tire.objects.filter(warehouse_id=warehouse_id, is_active=True)
        else:
            tires = Tire.objects.filter(is_active=True)
        
        return tires.values(
            'product_name', 'warehouse__name', 'brand', 'model', 'size'
        ).annotate(
            count=Count('id')
        ).order_by('product_name', 'warehouse__name')
    
    @staticmethod
    def get_stock_movement(start_date, end_date, warehouse_id=None):
        """
        Получить движение шин по складам за период
        """
        from .models import WarehouseMovement
        
        movements = WarehouseMovement.objects.select_related(
            'document', 'tire', 'from_warehouse', 'to_warehouse'
        )
        
        if start_date:
            movements = movements.filter(movement_date__gte=start_date)
        if end_date:
            movements = movements.filter(movement_date__lte=end_date)
        if warehouse_id:
            movements = movements.filter(
                from_warehouse_id=warehouse_id
            ) | movements.filter(to_warehouse_id=warehouse_id)
        
        return movements.order_by('-movement_date')
