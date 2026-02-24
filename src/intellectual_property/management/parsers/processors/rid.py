"""
Форматирование названий РИД
"""

from .text_processor import RussianTextProcessor


class RIDNameFormatter:
    """Форматирование названий РИД"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def format(self, text: str) -> str:
        """Форматирование названия РИД"""
        if not text or not isinstance(text, str):
            return text

        if len(text.strip()) <= 1:
            return text

        # Приводим к нижнему регистру и делаем первую букву заглавной
        words = text.lower().split()
        if words:
            words[0] = words[0][0].upper() + words[0][1:]
        return ' '.join(words)
