"""
Детектор типов сущностей
"""

from .text_processor import RussianTextProcessor


class EntityTypeDetector:
    """Детектор типов сущностей"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def detect_type(self, text: str) -> str:
        """Определение типа сущности"""
        if self.processor.is_person(text):
            return 'person'
        return 'organization'
