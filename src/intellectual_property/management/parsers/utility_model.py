"""
Парсер для полезных моделей
"""

from intellectual_property.models import IPType
from .base import BaseFIPSParser


class UtilityModelParser(BaseFIPSParser):
    """Парсер для полезных моделей"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='utility-model').first()

    def get_required_columns(self):
        return ['registration number', 'utility model name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер полезных моделей готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
