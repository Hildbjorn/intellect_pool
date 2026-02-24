"""
Детектор типов сущностей с использованием Natasha
"""

from .text_processor import RussianTextProcessor


class EntityTypeDetector:
    """Детектор типов сущностей с использованием Natasha"""

    def __init__(self):
        self.processor = RussianTextProcessor()
        # Кэш для результатов, чтобы не вызывать Natasha повторно для одних и тех же текстов
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def detect_type(self, text: str) -> str:
        """Определение типа сущности с использованием Natasha"""
        if not text:
            return 'organization'

        # Проверяем кэш
        if text in self.cache:
            self.cache_hits += 1
            return self.cache[text]

        self.cache_misses += 1

        # Используем процессор с Natasha для определения
        if self.processor.is_person(text):
            result = 'person'
        else:
            result = 'organization'

        # Кэшируем результат (с ограничением размера)
        if len(self.cache) < 50000:  # Ограничиваем размер кэша
            self.cache[text] = result
        else:
            # Если кэш переполнен, очищаем его
            self.cache.clear()
            self.cache[text] = result

        return result

    def get_cache_stats(self):
        """Статистика кэша для отладки"""
        total = self.cache_hits + self.cache_misses
        return {
            'size': len(self.cache),
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_ratio': self.cache_hits / total if total > 0 else 0
        }