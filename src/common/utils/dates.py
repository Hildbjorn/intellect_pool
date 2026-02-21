"""
Утилиты для работы с датами и временем.
"""

from datetime import datetime, date
from typing import List, Tuple, Optional
import pytz


class DateUtils:
    """Класс утилит для обработки дат."""
    
    # Диапазон лет ±100 от текущего года
    YEARS: List[Tuple[int, int]] = [
        (year, year) for year in range(
            datetime.now().year - 100,
            datetime.now().year + 101
        )
    ]
    
    # Диапазон чисел от 1 до 20
    PERIOD: List[Tuple[int, int]] = [(i, i) for i in range(1, 21)]
    
    @staticmethod
    def get_current_year() -> int:
        """Возвращает текущий год."""
        return datetime.now().year
    
    @staticmethod
    def get_current_month() -> int:
        """Возвращает текущий месяц."""
        return datetime.now().month
    
    @staticmethod
    def get_current_date() -> date:
        """Возвращает текущую дату."""
        return datetime.now().date()
    
    @staticmethod
    def get_current_datetime(timezone: Optional[str] = None) -> datetime:
        """
        Возвращает текущую дату и время.
        
        Args:
            timezone: Название таймзоны (например, 'Europe/Moscow')
            
        Returns:
            Текущая дата и время
        """
        if timezone:
            try:
                tz = pytz.timezone(timezone)
                return datetime.now(tz)
            except pytz.UnknownTimeZoneError:
                print(f"Неизвестная таймзона: {timezone}")
        
        return datetime.now()
    
    @staticmethod
    def calculate_period(start_year: int, end_year: Optional[int] = None) -> int:
        """
        Рассчитывает период в годах.
        
        Args:
            start_year: Год начала
            end_year: Год окончания (текущий, если None)
            
        Returns:
            Период в годах
            
        Raises:
            ValueError: Если start_year больше end_year
        """
        if end_year is None:
            end_year = DateUtils.get_current_year()
        
        if start_year > end_year:
            raise ValueError("Год начала не может быть больше года окончания.")
        
        return end_year - start_year
    
    @staticmethod
    def format_experience(years: int) -> str:
        """
        Форматирует строку с опытом работы.
        
        Args:
            years: Количество лет опыта
            
        Returns:
            Отформатированная строка
        """
        if years < 0:
            return "0 лет"
        
        # Склонение для русского языка
        if 11 <= years % 100 <= 14:
            return f"{years} лет"
        
        last_digit = years % 10
        if last_digit == 1:
            return f"{years} год"
        elif 2 <= last_digit <= 4:
            return f"{years} года"
        else:
            return f"{years} лет"
    
    @staticmethod
    def calculate_age(birth_date: date, reference_date: Optional[date] = None) -> int:
        """
        Рассчитывает возраст.
        
        Args:
            birth_date: Дата рождения
            reference_date: Дата, на которую рассчитывается возраст (текущая, если None)
            
        Returns:
            Возраст в годах
            
        Raises:
            ValueError: Если birth_date в будущем
        """
        if reference_date is None:
            reference_date = DateUtils.get_current_date()
        
        if birth_date > reference_date:
            raise ValueError("Дата рождения не может быть в будущем.")
        
        age = reference_date.year - birth_date.year
        
        # Корректировка, если день рождения еще не наступил в этом году
        if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        return age
    
    @staticmethod
    def format_age(age: int) -> str:
        """
        Форматирует возраст с правильным склонением.
        
        Args:
            age: Возраст в годах
            
        Returns:
            Отформатированная строка возраста
        """
        if age < 0:
            return "0 лет"
        
        if 11 <= age % 100 <= 14:
            return f"{age} лет"
        
        last_digit = age % 10
        if last_digit == 1:
            return f"{age} год"
        elif 2 <= last_digit <= 4:
            return f"{age} года"
        else:
            return f"{age} лет"
    
    @staticmethod
    def is_leap_year(year: int) -> bool:
        """
        Проверяет, является ли год високосным.
        
        Args:
            year: Год для проверки
            
        Returns:
            True если год високосный
        """
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    
    @staticmethod
    def get_month_name(month: int, lang: str = 'ru') -> str:
        """
        Возвращает название месяца.
        
        Args:
            month: Номер месяца (1-12)
            lang: Язык ('ru' или 'en')
            
        Returns:
            Название месяца
            
        Raises:
            ValueError: Если месяц не в диапазоне 1-12
        """
        if not 1 <= month <= 12:
            raise ValueError("Месяц должен быть в диапазоне от 1 до 12.")
        
        ru_months = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        
        en_months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        
        if lang == 'ru':
            return ru_months[month - 1]
        else:
            return en_months[month - 1]