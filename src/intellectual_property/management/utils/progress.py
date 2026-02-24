# patents/utils/progress.py
from tqdm import tqdm
from contextlib import contextmanager
import sys

class ProgressManager:
    """Централизованное управление прогресс-барами"""
    
    _instance = None
    _progress_bars = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @contextmanager
    def progress(self, description, total=None, unit='зап', position=None):
        """Контекстный менеджер для прогресс-бара"""
        bar = tqdm(
            total=total,
            desc=description,
            unit=unit,
            position=position,
            leave=True,
            file=sys.stdout,
            bar_format='{l_bar}{bar:30}{r_bar}{bar:-10b}'
        )
        try:
            yield bar
        finally:
            bar.close()
    
    def iterate(self, iterable, description, unit='зап', **kwargs):
        """Итерация с прогресс-баром"""
        return tqdm(
            iterable,
            desc=description,
            unit=unit,
            **kwargs
        )

progress = ProgressManager()