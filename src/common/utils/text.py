"""
Утилиты для обработки текста и строк.
"""

import re
from uuid import uuid4
from typing import Optional, Tuple, Any
import pytils
from django.utils.text import slugify


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
    
    @staticmethod
    def inflect_russian(text: str, case: str) -> str:
        """
        Склоняет слова и словосочетания по падежам русского языка.
        
        Args:
            text: Исходный текст (слово или словосочетание)
            case: Целевой падеж (nominative, genitive, dative, accusative, instrumental, prepositional)
                или краткая форма: им, род, дат, вин, тв, пр
        
        Returns:
            Склоненная форма слова или исходный текст, если склонение невозможно
            
        Raises:
            ValueError: Если указан неизвестный падеж
        """
        if not text or not isinstance(text, str):
            return text
        
        # Словарь падежей и их окончаний для разных типов слов
        cases_map = {
            'nominative': {'name': 'именительный', 'suffix': ''},
            'genitive': {'name': 'родительный', 'suffix': ''},
            'dative': {'name': 'дательный', 'suffix': ''},
            'accusative': {'name': 'винительный', 'suffix': ''},
            'instrumental': {'name': 'творительный', 'suffix': ''},
            'prepositional': {'name': 'предложный', 'suffix': ''},
            'им': 'nominative',
            'род': 'genitive',
            'дат': 'dative',
            'вин': 'accusative',
            'тв': 'instrumental',
            'пр': 'prepositional'
        }
        
        # Нормализуем название падежа
        target_case = cases_map.get(case.lower(), case.lower())
        if target_case not in cases_map and target_case not in ['nominative', 'genitive', 'dative', 'accusative', 'instrumental', 'prepositional']:
            raise ValueError(f"Неизвестный падеж: {case}. Допустимые значения: nominative, genitive, dative, accusative, instrumental, prepositional или им, род, дат, вин, тв, пр")
        
        # Словарь окончаний для разных родов и чисел
        endings = {
            'masculine': {
                'nominative': '',
                'genitive': 'а',
                'dative': 'у',
                'accusative': '',
                'instrumental': 'ом',
                'prepositional': 'е'
            },
            'feminine': {
                'nominative': '',
                'genitive': 'ы',
                'dative': 'е',
                'accusative': 'у',
                'instrumental': 'ой',
                'prepositional': 'е'
            },
            'neuter': {
                'nominative': '',
                'genitive': 'а',
                'dative': 'у',
                'accusative': '',
                'instrumental': 'ом',
                'prepositional': 'е'
            },
            'plural': {
                'nominative': 'ы',
                'genitive': 'ов',
                'dative': 'ам',
                'accusative': 'ы',
                'instrumental': 'ами',
                'prepositional': 'ах'
            }
        }
        
        # Слова-исключения
        exceptions = {
            'человек': {
                'genitive': 'человека',
                'dative': 'человеку',
                'accusative': 'человека',
                'instrumental': 'человеком',
                'prepositional': 'человеке'
            },
            'ребенок': {
                'genitive': 'ребенка',
                'dative': 'ребенку',
                'accusative': 'ребенка',
                'instrumental': 'ребенком',
                'prepositional': 'ребенке'
            },
            'год': {
                'genitive': 'года',
                'dative': 'году',
                'accusative': 'год',
                'instrumental': 'годом',
                'prepositional': 'годе'
            },
            'день': {
                'genitive': 'дня',
                'dative': 'дню',
                'accusative': 'день',
                'instrumental': 'днем',
                'prepositional': 'дне'
            },
            'ночь': {
                'genitive': 'ночи',
                'dative': 'ночи',
                'accusative': 'ночь',
                'instrumental': 'ночью',
                'prepositional': 'ночи'
            },
            'мать': {
                'genitive': 'матери',
                'dative': 'матери',
                'accusative': 'мать',
                'instrumental': 'матерью',
                'prepositional': 'матери'
            },
            'отец': {
                'genitive': 'отца',
                'dative': 'отцу',
                'accusative': 'отца',
                'instrumental': 'отцом',
                'prepositional': 'отце'
            }
        }
        
        # Определяем пол слова по окончанию
        def detect_gender(word):
            word = word.lower().strip()
            
            # Проверяем исключения
            if word in exceptions:
                return word
            
            # Определяем род по окончанию
            if word.endswith(('а', 'я')):
                return 'feminine'
            elif word.endswith(('о', 'е', 'ё')):
                return 'neuter'
            elif word.endswith(('ь')):
                # Слова на -ь могут быть мужского или женского рода
                feminine_ending_soft = ['сть', 'знь', 'вль', 'бль', 'пль', 'мль', 'фль']
                if any(word.endswith(ending) for ending in feminine_ending_soft):
                    return 'feminine'
                return 'masculine'
            else:
                return 'masculine'
        
        # Склоняем слово по падежу
        def inflect_word(word, target_case):
            if not word:
                return word
            
            # Проверяем исключения для всего слова
            word_lower = word.lower()
            if word_lower in exceptions:
                if target_case in exceptions[word_lower]:
                    # Сохраняем оригинальный регистр первой буквы
                    result = exceptions[word_lower][target_case]
                    if word[0].isupper():
                        result = result.capitalize()
                    return result
            
            # Проверяем исключения для частей слова (например, "пол-")
            parts = word.split('-')
            if len(parts) > 1:
                inflected_parts = [inflect_word(part, target_case) for part in parts]
                return '-'.join(inflected_parts)
            
            gender = detect_gender(word)
            
            # Особые случаи для винительного падежа (одушевленность)
            if target_case == 'accusative':
                # Для мужского рода одушевленных предметов винительный совпадает с родительным
                if gender == 'masculine' and not word.endswith(('метр', 'грамм', 'литр')):
                    return inflect_word(word, 'genitive')
            
            # Получаем основу слова (убираем окончание)
            if gender == 'masculine':
                if word.endswith(('й', 'ь')):
                    stem = word[:-1]
                else:
                    stem = word
            elif gender == 'feminine':
                if word.endswith(('а', 'я')):
                    stem = word[:-1]
                elif word.endswith('ь'):
                    stem = word[:-1]
                else:
                    stem = word
            elif gender == 'neuter':
                if word.endswith(('о', 'е', 'ё')):
                    stem = word[:-1]
                else:
                    stem = word
            else:
                stem = word
            
            # Добавляем окончание для нужного падежа
            if isinstance(gender, str) and gender in endings:
                ending = endings[gender].get(target_case, '')
                if ending:
                    return stem + ending
            
            return word
        
        # Склоняем словосочетание целиком
        words = text.split()
        if len(words) == 1:
            return inflect_word(text, target_case)
        
        # Для словосочетаний склоняем все слова
        inflected_words = []
        for i, word in enumerate(words):
            # Не склоняем предлоги и союзы
            if word.lower() in ['в', 'на', 'с', 'о', 'об', 'про', 'без', 'для', 'до', 'из', 'к', 'у']:
                inflected_words.append(word)
            else:
                inflected_words.append(inflect_word(word, target_case))
        
        return ' '.join(inflected_words)