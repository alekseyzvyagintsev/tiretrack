"""UploadService — загрузка QR-кодов из файла."""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from django.db import transaction
from django.utils import timezone

from tires.models import TireNomenclature, TireCode, Warehouse, Supplier
from integrations.honest_sign import HonestSignClient

logger = logging.getLogger(__name__)


@dataclass
class UploadReport:
    """Отчёт о загрузке QR-кодов."""

    total_lines: int = 0
    created: int = 0
    duplicates: int = 0
    unrecognized: int = 0
    honest_sign_errors: int = 0

    details: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def summary(self) -> Dict[str, int]:
        return {
            'total_lines': self.total_lines,
            'created': self.created,
            'duplicates': self.duplicates,
            'unrecognized': self.unrecognized,
            'honest_sign_errors': self.honest_sign_errors,
        }


class UploadService:
    """Сервис загрузки QR-кодов из текстового файла."""

    def __init__(self, warehouse: Warehouse, supplier: Optional[Supplier] = None):
        self.warehouse = warehouse
        self.supplier = supplier
        self.client = HonestSignClient()
        self.report = UploadReport()

    @transaction.atomic
    def upload(self, lines: List[str]) -> UploadReport:
        """Загрузить список строк (QR-кодов).

        Args:
            lines: Список строк файла, каждая — DataMatrix-код

        Returns:
            UploadReport с результатами загрузки
        """
        self.report = UploadReport()
        self.report.total_lines = len(lines)

        for line in lines:
            qr_code = line.strip()
            if not qr_code:
                continue

            self._process_code(qr_code)

        logger.info(
            'Загрузка завершена: всего=%d создано=%d дубликаты=%d '
            'нераспознанные=%d ошибки_чз=%d',
            self.report.total_lines,
            self.report.created,
            self.report.duplicates,
            self.report.unrecognized,
            self.report.honest_sign_errors,
        )

        return self.report

    def _process_code(self, qr_code: str) -> None:
        """Обработать один QR-код."""
        # 1. Дедупликация: код с любым статусом → пропуск (БП 3)
        if TireCode.objects.filter(qr_code=qr_code).exists():
            self.report.duplicates += 1
            self.report.details.append({
                'code': qr_code,
                'reason': 'duplicated',
            })
            logger.warning('Дубликат QR-кода: %s', qr_code)
            return

        # 2. Запрос в «Честный знак»
        honest_data = self.client.get_code_info(qr_code)
        if honest_data is None:
            self.report.honest_sign_errors += 1
            self.report.details.append({
                'code': qr_code,
                'reason': 'honest_sign_error',
            })
            logger.warning(
                'Ошибка запроса к Честному знаку для кода: %s', qr_code
            )
            return

        # 3. Парсинг атрибутов: brand, model, size
        brand = honest_data.get('brand', '').strip()
        model = honest_data.get('model', '').strip()
        size = honest_data.get('size', '').strip()
        product_name = honest_data.get('product_name', '').strip() or None

        if not all([brand, model, size]):
            self.report.unrecognized += 1
            self.report.details.append({
                'code': qr_code,
                'reason': 'unrecognized',
            })
            logger.warning(
                'Неполные атрибуты для кода %s: brand=%s model=%s size=%s',
                qr_code, brand, model, size,
            )
            return

        # 4. Авто-создание TireNomenclature (БП 1)
        nomenclature = self._get_or_create_nomenclature(
            brand, model, size, product_name
        )

        # 5. Создание TireCode
        TireCode.objects.create(
            qr_code=qr_code,
            nomenclature=nomenclature,
            warehouse=self.warehouse,
            supplier=self.supplier,
            honest_sign_data=honest_data,
            created_at=timezone.now(),
        )

        self.report.created += 1
        logger.info('Создан TireCode: %s → %s', qr_code, nomenclature)

    @staticmethod
    def _get_or_create_nomenclature(
        brand: str,
        model: str,
        size: str,
        product_name: Optional[str],
    ) -> TireNomenclature:
        """Создать или получить номенклатуру.

        product_name сохраняется только при первом создании (БП 14).
        """
        nomenclature, created = TireNomenclature.objects.get_or_create(
            brand=brand,
            model=model,
            size=size,
            defaults={'product_name': product_name} if product_name else {},
        )

        # Если product_name не задан и номенклатура новая — fallback
        if created and not product_name:
            nomenclature.product_name = f'{brand} {model} {size}'
            nomenclature.save(update_fields=['product_name'])

        return nomenclature
