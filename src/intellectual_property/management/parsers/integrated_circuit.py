"""
Парсер для топологий интегральных микросхем
"""

from intellectual_property.models import IPType
from .base import BaseFIPSParser


class IntegratedCircuitTopologyParser(BaseFIPSParser):
    """Парсер для топологий интегральных микросхем"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='integrated-circuit-topology').first()

    def get_required_columns(self):
        return ['registration number', 'microchip name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер топологий микросхем готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
