"""
Детектор типов сущностей с использованием Natasha и кэшированием
"""

# ИСПРАВЛЕНО: импортируем из текущего пакета (.text_processor)
from .text_processor import RussianTextProcessor


class EntityTypeDetector:
    """
    Детектор типов сущностей с использованием Natasha и кэшированием
    Определяет, является ли текст именем человека или названием организации
    """

    def __init__(self, cache_size: int = 50000):
        self.processor = RussianTextProcessor()
        # Кэш для результатов, чтобы не вызывать Natasha повторно
        self.cache = {}
        self.cache_size = cache_size
        self.cache_hits = 0
        self.cache_misses = 0

    def detect_type(self, text: str) -> str:
        """
        Определение типа сущности с использованием Natasha

        Args:
            text: Название сущности (ФИО или название организации)

        Returns:
            'person' или 'organization'
        """
        if not text or len(text) < 2:
            return 'organization'

        # Проверяем кэш
        if text in self.cache:
            self.cache_hits += 1
            return self.cache[text]

        self.cache_misses += 1

        # Используем процессор с Natasha для определения
        # is_person() внутри использует NER и другие методы Natasha
        if self.processor.is_person(text):
            result = 'person'
        else:
            result = 'organization'

        # Кэшируем результат с контролем размера
        self._add_to_cache(text, result)

        return result

    def detect_type_batch(self, texts: list) -> dict:
        """
        Пакетное определение типов для списка текстов

        Args:
            texts: Список текстов для анализа

        Returns:
            Словарь {текст: тип}
        """
        result = {}

        # Сначала проверяем кэш
        to_process = []
        for text in texts:
            if text in self.cache:
                result[text] = self.cache[text]
                self.cache_hits += 1
            else:
                to_process.append(text)
                self.cache_misses += 1

        # Обрабатываем новые тексты
        for text in to_process:
            if self.processor.is_person(text):
                result[text] = 'person'
            else:
                result[text] = 'organization'
            self._add_to_cache(text, result[text])

        return result

    def _add_to_cache(self, text: str, result: str):
        """
        Добавление результата в кэш с контролем размера
        """
        if len(self.cache) >= self.cache_size:
            # Очищаем 20% самых старых записей
            items = list(self.cache.items())
            self.cache = dict(items[-int(self.cache_size * 0.8):])

        self.cache[text] = result

    def get_cache_stats(self) -> dict:
        """
        Статистика кэша для отладки
        """
        total = self.cache_hits + self.cache_misses
        return {
            'size': len(self.cache),
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_ratio': self.cache_hits / total if total > 0 else 0
        }

    def clear_cache(self):
        """Очистка кэша для освобождения памяти"""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0