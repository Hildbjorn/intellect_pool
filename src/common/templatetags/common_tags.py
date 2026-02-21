"""
Пользовательские шаблонные теги и фильтры.
"""

import json
import re
from typing import Any, Dict, Optional
from django import template
from django.template.loader import get_template
from django.utils.safestring import mark_safe
import markdown
from typus import ru_typus
from common.utils.text import TextUtils

register = template.Library()


# ==================== ФИЛЬТРЫ ====================

@register.filter
def template_exists(template_name: str) -> bool:
    """
    Проверяет существование шаблона.
    
    Args:
        template_name: Имя шаблона
        
    Returns:
        True если шаблон существует
    """
    try:
        get_template(template_name)
        return True
    except template.TemplateDoesNotExist:
        return False


@register.simple_tag
def verbose_name(instance: Any, field_name: str) -> str:
    """
    Возвращает verbose_name для поля модели.
    
    Args:
        instance: Объект модели
        field_name: Имя поля
        
    Returns:
        Человекочитаемое имя поля
    """
    try:
        field = instance._meta.get_field(field_name)
        return str(ru_typus(field.verbose_name))
    except (AttributeError, KeyError):
        return field_name


@register.filter(is_safe=True)
def replace_n(value: Optional[str]) -> str:
    """
    Заменяет переносы строк на теги <br>.
    
    Args:
        value: Входная строка
        
    Returns:
        Строка с HTML переносами
    """
    return TextUtils.replace_newlines(value)


@register.filter
def format_number(number: float) -> str:
    """
    Форматирует число с разделителями тысяч и двумя знаками после запятой.
    
    Args:
        number: Число для форматирования
        
    Returns:
        Отформатированная строка
    """
    return TextUtils.format_number(number, 2)


@register.filter
def format_number_int(number: float) -> str:
    """
    Форматирует целое число с разделителями тысяч.
    
    Args:
        number: Число для форматирования
        
    Returns:
        Отформатированная строка
    """
    return TextUtils.format_integer(number)


@register.filter
def get_item(dictionary: Dict, key: str) -> Any:
    """
    Получает значение из словаря по ключу.
    
    Args:
        dictionary: Словарь
        key: Ключ
        
    Returns:
        Значение или None
    """
    return dictionary.get(key) if dictionary else None


@register.filter(is_safe=True)
def replace_comma(value: str) -> str:
    """
    Заменяет запятую на точку (для JS совместимости).
    
    Args:
        value: Входная строка
        
    Returns:
        Строка с заменой
    """
    if value is not None:
        return value.replace(',', '.')
    return ''


@register.filter(is_safe=True)
def js(obj: Any) -> str:
    """
    Конвертирует объект в JSON строку.
    
    Args:
        obj: Объект для конвертации
        
    Returns:
        JSON строка
    """
    try:
        return mark_safe(json.dumps(obj, default=str))
    except (TypeError, ValueError):
        return 'null'


@register.filter(name="typus", is_safe=True)
def typus(value: str) -> str:
    """
    Применяет русскую типографику к тексту.
    
    Args:
        value: Входной текст
        
    Returns:
        Отформатированный текст
    """
    if not value:
        return ''
    return ru_typus(value)


@register.simple_tag()
def my_set(value: Any) -> Any:
    """
    Тег для установки значения в переменную контекста.
    
    Args:
        value: Значение
        
    Returns:
        То же значение
    """
    return value


@register.filter(name="without_quotes", is_safe=True)
def without_quotes(value: str) -> str:
    """
    Удаляет кавычки из строки.
    
    Args:
        value: Входная строка
        
    Returns:
        Строка без кавычек
    """
    if not value:
        return ''
    
    # Удаляем кавычки в начале и конце
    value = value.strip()
    if value.startswith('"'):
        value = value[1:]
    if value.endswith('"'):
        value = value[:-1]
    
    return ru_typus(value)


@register.filter(name="format_phone_to_whatsapp", is_safe=True)
def format_phone_to_whatsapp(phone_number: str) -> str:
    """
    Форматирует номер телефона для WhatsApp.
    
    Args:
        phone_number: Номер телефона
        
    Returns:
        Отформатированный номер
    """
    return TextUtils.normalize_phone_for_whatsapp(phone_number)


@register.filter(name="clean_phone", is_safe=True)
def clean_phone(phone_number: str) -> str:
    """
    Очищает номер телефона от лишних символов.
    
    Args:
        phone_number: Номер телефона
        
    Returns:
        Очищенный номер
    """
    return TextUtils.clean_phone(phone_number)


@register.filter(name='markdown')
def markdown_to_html(text: Optional[str]) -> str:
    """
    Конвертирует Markdown в HTML.
    
    Args:
        text: Текст в формате Markdown
        
    Returns:
        HTML строка
    """
    if not text:
        return ''
    
    try:
        # Безопасное преобразование (отключаем небезопасные теги)
        html = markdown.markdown(
            text,
            extensions=['extra', 'nl2br'],
            output_format='html5'
        )
        return mark_safe(html)
    except Exception:
        return text


# ==================== CSS КЛАССЫ ====================

@register.filter(name='ppx_3')
def add_class_to_p(value: str) -> str:
    """
    Добавляет класс px-3 к тегам <p>.
    
    Args:
        value: HTML строка
        
    Returns:
        Модифицированная HTML строка
    """
    if not value:
        return ''
    return re.sub(r'<p>', r'<p class="px-3">', value)


@register.filter(name='limb_2')
def add_class_to_li(value: str) -> str:
    """
    Добавляет класс mb-2 к тегам <li>.
    
    Args:
        value: HTML строка
        
    Returns:
        Модифицированная HTML строка
    """
    if not value:
        return ''
    return re.sub(r'<li>', r'<li class="mb-2">', value)


@register.filter(name='h4mb_3')
def add_class_to_h4(value: str) -> str:
    """
    Добавляет классы к тегам <h4>.
    
    Args:
        value: HTML строка
        
    Returns:
        Модифицированная HTML строка
    """
    if not value:
        return ''
    return re.sub(r'<h4>', r'<h4 class="fw-bold mb-3">', value)


# ==================== ТЕГИ ====================

@register.simple_tag
def query_transform(request, **kwargs) -> str:
    """
    Обновляет параметры запроса URL.
    
    Args:
        request: HttpRequest объект
        **kwargs: Параметры для обновления
        
    Returns:
        Строка запроса URL
    """
    updated = request.GET.copy()
    
    for key, value in kwargs.items():
        if value is not None:
            updated[key] = value
        else:
            updated.pop(key, None)
    
    return updated.urlencode()


# ==================== ДОПОЛНИТЕЛЬНЫЕ ФИЛЬТРЫ ====================

@register.filter(name='truncate')
def truncate_text(value: str, length: int = 100) -> str:
    """
    Обрезает текст до указанной длины.
    
    Args:
        value: Входной текст
        length: Максимальная длина
        
    Returns:
        Обрезанный текст
    """
    return TextUtils.truncate_text(value, length)


@register.filter(name='yesno_ru')
def yesno_ru(value: bool) -> str:
    """
    Преобразует булево значение в русский текст.
    
    Args:
        value: Булево значение
        
    Returns:
        "Да" или "Нет"
    """
    if value is None:
        return "—"
    return "Да" if value else "Нет"


@register.filter(name='split')
def split_string(value: str, delimiter: str = ',') -> list:
    """
    Разделяет строку по разделителю.
    
    Args:
        value: Входная строка
        delimiter: Разделитель
        
    Returns:
        Список строк
    """
    if not value:
        return []
    return [item.strip() for item in value.split(delimiter) if item.strip()]