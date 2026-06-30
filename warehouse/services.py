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
    def post_document(document):
        """
        Проведение документа
        Переносит шины между складами и создает записи в истории
        """
        if document.status == 'posted':
            raise ValidationError('Документ уже проведён')
        
        if not document.items.exists():
            raise ValidationError('Нельзя провести пустой документ')
        
        # Меняем статус на "Проведён"
        document.status = 'posted'
        document.save()
        
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
    def mark_deleted(document):
        """Пометка документа на удаление (как в 1С)"""
        if document.deleted:
            raise ValidationError('Документ уже помечен на удаление')
        
        if not document.can_delete():
            raise ValidationError('Чтобы пометить на удаление, нужно отменить проведение документа')
        
        document.deleted = True
        document.save()
        
        return document
    
    @staticmethod
    @transaction.atomic
    def unmark_deleted(document):
        """Снятие пометки на удаление"""
        if not document.deleted:
            raise ValidationError('Документ не помечен на удаление')
        
        document.deleted = False
        document.save()
        
        return document
    
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
