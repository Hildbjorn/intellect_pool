"""
Парсер для баз данных
"""

from intellectual_property.models import IPType
from .base import BaseFIPSParser


class DatabaseParser(BaseFIPSParser):
    """Парсер для баз данных"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='database').first()

    def get_required_columns(self):
        return ['registration number', 'db name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер баз данных готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
