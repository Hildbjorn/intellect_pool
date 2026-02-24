from .invention import InventionParser
from .utility_model import UtilityModelParser
from .industrial_design import IndustrialDesignParser
from .integrated_circuit import IntegratedCircuitTopologyParser
from .computer_program import ComputerProgramParser
from .database import DatabaseParser

# Импортируем процессоры из правильного места
from .processors import (
    RussianTextProcessor,
    OrganizationNormalizer,
    PersonNameFormatter,
    RIDNameFormatter,
    EntityTypeDetector
)

__all__ = [
    'InventionParser',
    'UtilityModelParser',
    'IndustrialDesignParser',
    'IntegratedCircuitTopologyParser',
    'ComputerProgramParser',
    'DatabaseParser',
    'RussianTextProcessor',
    'OrganizationNormalizer',
    'PersonNameFormatter',
    'RIDNameFormatter',
    'EntityTypeDetector',
]
