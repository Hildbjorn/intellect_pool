"""
Утилиты для обработки текста и строк.
"""

import re
from uuid import uuid4
from typing import Optional, Tuple, Any
import pytils
from slugify import slugify


class TextUtils:
    """Утилиты для обработки строк."""
    
    @staticmethod
    def replace_newlines(value: Optional[str]) -> str:
        """
        Заменяет переносы строк на HTML теги <br>.
        
        Args:
            value: Входная строка
            
        Returns:
            Строка с замененными переносами или исходная строка
        """
        if value is None:
            return ''
        
        if not isinstance(value, str):
            value = str(value)
        
        return value.replace('\n', '<br />')
    
    @staticmethod
    def format_number(number: float, decimal_places: int = 2) -> str:
        """
        Форматирует число с разделителями тысяч.
        
        Args:
            number: Число для форматирования
            decimal_places: Количество знаков после запятой
            
        Returns:
            Отформатированная строка
        """
        try:
            # Форматируем с заданным количеством знаков
            formatted = f"{number:,.{decimal_places}f}"
            # Заменяем запятые на пробелы, точку на запятую (для RU локали)
            formatted = formatted.replace(',', ' ').replace('.', ',')
            return formatted
        except (ValueError, TypeError):
            return str(number)
    
    @staticmethod
    def format_integer(number: float) -> str:
        """
        Форматирует целое число с разделителями тысяч.
        
        Args:
            number: Число для форматирования
            
        Returns:
            Отформатированная строка
        """
        try:
            # Округляем до целого
            integer_number = int(round(number))
            formatted = f"{integer_number:,}"
            return formatted.replace(',', ' ')
        except (ValueError, TypeError):
            return str(number)
    
    @staticmethod
    def pluralize_russian(
        number: int, 
        singular: str, 
        dual: str, 
        plural: str
    ) -> Tuple[int, str]:
        """
        Склоняет слова в зависимости от числительного в русском языке.
        
        Args:
            number: Число
            singular: Форма для 1 (год)
            dual: Форма для 2-4 (года)
            plural: Форма для 5-0 (лет)
            
        Returns:
            Кортеж (число, правильная форма слова)
            
        Raises:
            ValueError: Если число отрицательное
        """
        if number is None or number < 0:
            raise ValueError("Число должно быть положительным.")
        
        if number % 10 == 1 and number % 100 != 11:
            return (number, singular)
        elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
            return (number, dual)
        else:
            return (number, plural)
    
    @staticmethod
    def generate_slug(instance: Any, slug_field_name: str = 'slug') -> str:
        """
        Создает уникальный slug для объекта модели.
        
        Args:
            instance: Объект модели Django
            slug_field_name: Имя поля slug в модели
            
        Returns:
            Уникальный slug
            
        Raises:
            ValueError: Если объект не является моделью Django
        """
        try:
            # Транслитерация названия объекта
            transliterated = pytils.translit.translify(str(instance))
            model_name = slugify(instance.__class__.__name__).lower()
            base_slug = slugify(transliterated)
            
            # Создаем базовый slug
            slug = f'{model_name}-{base_slug}'
            
            # Проверяем уникальность
            model_class = instance.__class__
            if hasattr(model_class, 'objects'):
                counter = 1
                original_slug = slug
                
                while model_class.objects.filter(**{slug_field_name: slug}).exists():
                    # Если slug существует, добавляем суффикс
                    slug = f'{original_slug}-{uuid4().hex[:4]}'
                    counter += 1
                    
                    if counter > 10:  # Защита от бесконечного цикла
                        slug = f'{original_slug}-{uuid4().hex[:8]}'
                        break
            return slug
            
        except AttributeError:
            raise ValueError(
                "Переданный объект не имеет атрибута 'objects'. "
                "Убедитесь, что это модель Django."
            )
    
    @staticmethod
    def clean_phone(phone_number: str) -> str:
        """
        Очищает номер телефона от лишних символов.
        
        Args:
            phone_number: Номер телефона для очистки
            
        Returns:
            Очищенный номер телефона
        """
        if not phone_number:
            return ''
        
        # Удаляем все нецифровые символы, кроме плюса
        cleaned = re.sub(r'[^\d+]', '', phone_number)
        return cleaned
    
    @staticmethod
    def normalize_phone_for_whatsapp(phone_number: str) -> str:
        """
        Нормализует номер телефона для WhatsApp.
        
        Args:
            phone_number: Номер телефона
            
        Returns:
            Номер в формате 79991234567
        """
        cleaned = TextUtils.clean_phone(phone_number)
        
        if not cleaned:
            return ''
        
        # Преобразуем российские номера
        if cleaned.startswith('8'):
            cleaned = '7' + cleaned[1:]
        elif cleaned.startswith('+7'):
            cleaned = '7' + cleaned[2:]
        elif cleaned.startswith('9') and len(cleaned) == 10:
            cleaned = '7' + cleaned
        
        return cleaned
    
    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
        """
        Обрезает текст до максимальной длины.
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина
            suffix: Суффикс для обрезанного текста
            
        Returns:
            Обрезанный текст
        """
        if not text or len(text) <= max_length:
            return text
        
        # Обрезаем по границе слова
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.7:  # Обрезаем по границе слова если возможно
            truncated = truncated[:last_space]
        
        return truncated.rstrip() + suffix