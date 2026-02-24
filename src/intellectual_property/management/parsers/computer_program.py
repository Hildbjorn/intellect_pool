"""
Парсер для программ для ЭВМ
"""

from intellectual_property.models import IPType
from .base import BaseFIPSParser


class ComputerProgramParser(BaseFIPSParser):
    """Парсер для программ для ЭВМ"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='computer-program').first()

    def get_required_columns(self):
        return ['registration number', 'program name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер программ для ЭВМ готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
