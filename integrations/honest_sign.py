"""Обёртка над библиотекой nechestniy_znak для запроса к «Честному знаку»."""
import logging
from typing import Optional, Dict, Any

from decouple import config

logger = logging.getLogger(__name__)


class HonestSignClient:
    """Клиент для работы с API «Честный знак»."""

    def __init__(self, use_mock: bool = None):
        self.use_mock = use_mock if use_mock is not None else config(
            'USE_MOCK_HONEST_SIGN', default=False, cast=bool
        )
        self.timeout = config('HONEST_SIGN_TIMEOUT', default=30, cast=int)

    def get_code_info(self, qr_code: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о коде по DataMatrix.

        Args:
            qr_code: DataMatrix-код (строка)

        Returns:
            Словарь с атрибутами {brand, model, size, product_name} или None при ошибке
        """
        if self.use_mock:
            return self._mock_get_code_info(qr_code)

        try:
            from nechestniy_znak import Crpt

            crpt = Crpt()
            response = crpt.get_product_info(qr_code)

            if not response:
                logger.warning(
                    'Честный знак вернул пустой ответ для кода %s', qr_code
                )
                return None

            return self._parse_response(response)

        except Exception as exc:
            logger.error(
                'Ошибка запроса к Честному знаку для кода %s: %s',
                qr_code,
                exc,
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # Парсинг ответа
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(response: Any) -> Optional[Dict[str, Any]]:
        """Извлечь brand / model / size / product_name из ответа API."""
        try:
            # Ожидаем структуру, которую возвращает nechestniy_znak
            if isinstance(response, dict):
                return {
                    'brand': response.get('brand', '').strip(),
                    'model': response.get('model', '').strip(),
                    'size': response.get('size', '').strip(),
                    'product_name': response.get('product_name', '').strip()
                    or None,
                }
        except Exception as exc:
            logger.error('Ошибка парсинга ответа Честного знака: %s', exc)

        return None

    # ------------------------------------------------------------------
    # Мок для локальной разработки
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_get_code_info(qr_code: str) -> Optional[Dict[str, Any]]:
        """Возвращает тестовые данные для разработки."""
        # Тестовые данные для нескольких кодов
        mock_data = {
            'TESTCODE000001': {
                'brand': 'Bridgestone',
                'model': 'Potenza',
                'size': '295/80R22.5',
                'product_name': 'Bridgestone Potenza 295/80R22.5',
            },
            'TESTCODE000002': {
                'brand': 'Michelin',
                'model': 'X',
                'size': '315/80R22.5',
                'product_name': 'Michelin X 315/80R22.5',
            },
            'TESTCODE000003': {
                'brand': 'Continental',
                'model': 'HSR2',
                'size': '275/70R22.5',
                'product_name': 'Continental HSR2 275/70R22.5',
            },
        }

        data = mock_data.get(qr_code)
        if data:
            return data

        # Fallback для любых других тестовых кодов
        return {
            'brand': 'MockBrand',
            'model': 'MockModel',
            'size': '295/80R22.5',
            'product_name': 'MockBrand MockModel 295/80R22.5',
        }
