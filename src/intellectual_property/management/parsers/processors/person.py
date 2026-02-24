"""
Форматирование имен людей
"""

from .text_processor import RussianTextProcessor


class PersonNameFormatter:
    """Форматирование имен людей"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def format(self, name: str) -> str:
        """Форматирование ФИО"""
        return self.processor.format_person_name(name)
