"""
Конфигурация приложения common.
"""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Конфигурация приложения common."""
    
    name = 'common'
    verbose_name = 'Общие утилиты'
    
    def ready(self):
        """
        Инициализация приложения.
        Здесь можно импортировать сигналы или выполнить другие настройки.
        """
        # Импортируем сигналы, если они есть
        try:
            import common.signals
        except ImportError:
            pass