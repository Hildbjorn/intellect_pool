"""
Утилиты для отображения прогресс-баров
Вынесены отдельно для переиспользования в других парсерах
"""

import sys
from tqdm import tqdm
from contextlib import contextmanager
from typing import Optional, Iterable, Iterator, Any


class ProgressManager:
    """
    Менеджер для работы с прогресс-барами
    Все прогресс-бары отображаются в одной строке (как в оригинальном tqdm)
    """
    
    def __init__(self, enabled: bool = True, file=sys.stdout):
        self.enabled = enabled
        self.file = file
        self._current_bar = None  # Текущий активный прогресс-бар
    
    @contextmanager
    def task(self, description: str, total: Optional[int] = None, unit: str = "элем"):
        """
        Контекстный менеджер для задачи с прогресс-баром
        Все задачи используют одну строку (предыдущая закрывается)
        """
        # Если есть предыдущий бар, закрываем его
        if self._current_bar is not None:
            self._current_bar.close()
        
        # Создаем новый прогресс-бар (без position, чтобы был в одной строке)
        bar = tqdm(
            total=total,
            desc=description,
            unit=unit,
            file=self.file,
            leave=False,  # Не оставлять после завершения
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
        
        self._current_bar = bar
        
        try:
            yield bar
        finally:
            bar.close()
            self._current_bar = None
            # Печатаем пустую строку для отделения следующего вывода
            print(file=self.file)
    
    @contextmanager
    def subtask(self, description: str, total: Optional[int] = None, unit: str = "элем"):
        """Алиас для task (для обратной совместимости)"""
        with self.task(description, total, unit) as bar:
            yield bar
    
    def step(self, message: str):
        """Вывод сообщения о шаге (всегда с новой строки)"""
        # Если есть активный прогресс-бар, временно его скрываем
        if self._current_bar is not None:
            self._current_bar.clear()
        print(f"🔹 {message}", file=self.file)
        if self._current_bar is not None:
            self._current_bar.refresh()
    
    def success(self, message: str):
        """Вывод сообщения об успехе"""
        if self._current_bar is not None:
            self._current_bar.clear()
        print(f"✅ {message}", file=self.file)
        if self._current_bar is not None:
            self._current_bar.refresh()
    
    def warning(self, message: str):
        """Вывод предупреждения"""
        if self._current_bar is not None:
            self._current_bar.clear()
        print(f"⚠️ {message}", file=self.file)
        if self._current_bar is not None:
            self._current_bar.refresh()
    
    def error(self, message: str):
        """Вывод ошибки"""
        if self._current_bar is not None:
            self._current_bar.clear()
        print(f"❌ {message}", file=self.file)
        if self._current_bar is not None:
            self._current_bar.refresh()


def batch_iterator(iterable, batch_size: int):
    """Разбивает итерируемый объект на батчи"""
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
