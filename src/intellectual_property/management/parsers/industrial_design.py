"""
Парсер для промышленных образцов
"""

from intellectual_property.models import IPType
from .base import BaseFIPSParser


class IndustrialDesignParser(BaseFIPSParser):
    """Парсер для промышленных образцов"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='industrial-design').first()

    def get_required_columns(self):
        return ['registration number', 'industrial design name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер промышленных образцов готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
