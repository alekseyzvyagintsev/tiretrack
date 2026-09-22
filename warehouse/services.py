"""DocumentService — бизнес-логика документов."""
import logging
from typing import List, Optional

from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Document, DocumentItem, DocType
from tires.models import TireNomenclature, TireCode, Warehouse, Platform

logger = logging.getLogger(__name__)


class DocumentService:
    """Сервис для работы с документами списания/выкупа."""

    @staticmethod
    @transaction.atomic
    def create(user, doc_type, source_warehouse, target_warehouse=None,
               notes='', writeoff_platform=None):
        """Создать новый документ в статусе draft.

        Args:
            user: автор документа
            doc_type: DocType (writeoff/buyout)
            source_warehouse: склад-источник
            target_warehouse: склад-получатель (для выкупа)
            notes: примечания
            writeoff_platform: площадка списания (может отличаться от source_platform)

        Returns:
            Document
        """
        source_platform = user.platform

        document = Document.objects.create(
            doc_type=doc_type,
            author=user,
            source_platform=source_platform,
            writeoff_platform=writeoff_platform or source_platform,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
            status='draft',
            notes=notes,
        )

        logger.info('Создан документ %d: %s', document.id, doc_type.name)
        return document

    @staticmethod
    @transaction.atomic
    def save_draft(document):
        """Сохранить черновик: draft → saved, присвоить номер.

        Args:
            document: Document

        Returns:
            Document
        """
        if document.status != 'draft':
            raise ValidationError('Можно сохранить только черновик')

        if not document.items.exists():
            raise ValidationError('Документ должен содержать хотя бы одну строку')

        # Присваиваем номер
        document.number = DocumentService._generate_number(document)
        document.status = 'saved'
        document.save()

        logger.info('Документ %d сохранён: %s', document.id, document.number)
        return document

    @staticmethod
    @transaction.atomic
    def add_item(document, nomenclature, quantity=1):
        """Добавить строку в документ.

        Если номенклатура уже есть — quantity++.

        Args:
            document: Document (draft или saved)
            nomenclature: TireNomenclature
            quantity: количество

        Returns:
            DocumentItem, is_duplicate: bool
        """
        if document.status not in ('draft', 'saved'):
            raise ValidationError('Можно добавлять строки только в черновик или сохранённый документ')

        item, created = DocumentItem.objects.get_or_create(
            document=document,
            nomenclature=nomenclature,
            defaults={'quantity': quantity},
        )

        if not created:
            item.quantity += quantity
            item.save()
            logger.info(
                'Увеличено количество строки %d: %d → %d',
                item.id, item.quantity - quantity, item.quantity
            )
            return item, True

        logger.info('Добавлена строка %d в документ %d', item.id, document.id)
        return item, False

    @staticmethod
    @transaction.atomic
    def update_item(item, quantity):
        """Обновить количество в строке."""
        if quantity < 1:
            raise ValidationError('Количество должно быть ≥ 1')
        item.quantity = quantity
        item.save()
        return item

    @staticmethod
    @transaction.atomic
    def delete_item(item):
        """Удалить строку из документа."""
        document = item.document
        if document.status not in ('draft', 'saved'):
            raise ValidationError('Можно удалять строки только из черновика или сохранённого документа')

        item.delete()
        logger.info('Удалена строка %d из документа %d', item.id, document.id)
        return document

    @staticmethod
    @transaction.atomic
    def post_document(document):
        """Проведение документа: saved → posted.

        Атомарная транзакция:
        1. Проверка остатка по каждой строке
        2. FIFO-выбор кодов
        3. Пометка кодов: is_used=True, is_active=False
        4. Для выкупа — перевязка на target_warehouse (БП 8)
        5. Смена статуса

        При нехватке — ROLLBACK, документ остаётся saved.
        """
        if document.status != 'saved':
            raise ValidationError('Можно провести только сохранённый документ')

        if not document.items.exists():
            raise ValidationError('Документ должен содержать хотя бы одну строку')

        is_buyout = document.doc_type.code == 'buyout'
        target_warehouse = document.target_warehouse if is_buyout else None

        # Проверяем остатки и выбираем коды (FIFO)
        selected_codes = []
        for item in document.items.select_for_update().all():
            nomenclature = item.nomenclature
            source_warehouse = document.source_warehouse

            # FIFO: по created_at ASC, id ASC
            available_codes = TireCode.objects.filter(
                nomenclature=nomenclature,
                warehouse=source_warehouse,
                is_active=True,
                is_used=False,
            ).order_by('created_at', 'id')

            if available_codes.count() < item.quantity:
                available = available_codes.count()
                raise ValidationError(
                    f'Недостаточно кодов для {nomenclature.display_name()}: '
                    f'требуется {item.quantity}, доступно {available}'
                )

            selected_codes.extend(available_codes[:item.quantity])

        # Все проверки пройдены — применяем
        for code in selected_codes:
            code.is_used = True
            code.is_active = False
            code.document = document
            code.used_at = timezone.now()

            # Для выкупа — перевязка на target_warehouse (БП 8)
            if target_warehouse:
                code.warehouse = target_warehouse

            code.save(update_fields=['is_used', 'is_active', 'document', 'used_at', 'warehouse'])

        # Смена статуса через update()
        Document.objects.filter(pk=document.pk).update(
            status='posted',
            posted_at=timezone.now()
        )
        document.status = 'posted'
        document.posted_at = timezone.now()

        logger.info(
            'Документ %d проведён: %d кодов (buyout=%s)',
            document.id, len(selected_codes), is_buyout
        )
        return document

    @staticmethod
    @transaction.atomic
    def unpost_document(document):
        """Распроведение: posted → saved.

        Возвращает коды в активные.
        """
        if document.status != 'posted':
            raise ValidationError('Можно распроведать только проведённый документ')

        # Откат кодов
        codes = document.tire_codes.all()
        for code in codes:
            code.is_used = False
            code.is_active = True
            code.document = None
            code.used_at = None
            code.save(update_fields=['is_used', 'is_active', 'document', 'used_at'])

        # Смена статуса
        document.status = 'saved'
        document.posted_at = None
        document.save(update_fields=['status', 'posted_at'])

        logger.info('Документ %d распроведён', document.id)
        return document

    @staticmethod
    @transaction.atomic
    def mark_deleted(document):
        """Пометить документ на удаление.

        Если posted → сначала распроведение.
        """
        if document.status == 'posted':
            DocumentService.unpost_document(document)

        document.is_deleted = True
        document.status = 'marked_deleted'
        document.save(update_fields=['is_deleted', 'status'])

        logger.info('Документ %d помечен на удаление', document.id)
        return document

    @staticmethod
    def _generate_number(document) -> str:
        """Сгенерировать номер: СП-ГГГГ-NNNNNN / ВК-ГГГГ-NNNNNN.

        Сброс счётчика в начале года.
        """
        year = document.created_at.year if document.created_at else timezone.now().year
        prefix = document.doc_type.prefix
        count = Document.objects.filter(
            doc_type=document.doc_type,
            number__startswith=f'{prefix}-{year}-',
        ).count()
        return f'{prefix}-{year}-{count + 1:06d}'
