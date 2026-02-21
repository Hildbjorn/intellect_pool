# Файл: admin_utils.py

```
"""
Утилиты для улучшения админ-панели Django.
"""

from django.templatetags.static import static
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from markdown import markdown
from typing import Optional, Any, Tuple

class AdminImageMixin:
    """
    Миксин для добавления методов отображения изображений в админ-панели.
    
    Атрибуты:
        image_field (str): имя поля с изображением (по умолчанию: 'image')
        default_image (str): путь к изображению по умолчанию
    """

    image_field = 'image'
    default_image = 'img/elements/no_photo.webp'
    
    def image_tag(self, obj):
        """
        Генерирует HTML-тег изображения для отображения в админ-панели.
        
        Args:
            obj: Объект модели Django
            
        Returns:
            HTML-строка с тегом изображения
        """
        image = getattr(obj, self.image_field, None)
        if image and hasattr(image, 'url'):
            return format_html('<img id="image_tag" src="{}" />', image.url)
        else:
            default_image_url = static(self.default_image)
            return format_html('<img id="image_tag" src="{}" />', default_image_url)
    image_tag.short_description = 'Изображение'
    
    def image_thumbnail(self, obj):
        """
        Генерирует HTML-тег миниатюры изображения.
        
        Args:
            obj: Объект модели Django
            
        Returns:
            HTML-строка с тегом миниатюры
        """
        image = getattr(obj, self.image_field, None)
        if image and hasattr(image, 'url'):
            return format_html('<img id="image_thumbnail" src="{}" />', image.url)
        else:
            default_image_url = static(self.default_image)
            return format_html('<img id="image_thumbnail" src="{}" />', default_image_url)
    image_thumbnail.short_description = 'Изображение'

    def star_rating_display(self, obj: Any) -> str:
        """
        Отображение рейтинга в виде звезд Bootstrap.
        
        Args:
            obj: Объект модели с полем star_rating
            
        Returns:
            HTML-строка со звездами рейтинга
        """
        rating = getattr(obj, 'star_rating', None)
        
        if rating is None:
            return format_html(
                '<span class="text-muted">'
                '<i class="bi bi-star me-1"></i>Не оценен'
                '</span>'
            )
        
        try:
            rating_int = int(rating)
            stars = ''.join([
                '<i class="bi bi-star-fill text-warning me-1"></i>' 
                if i < rating_int else 
                '<i class="bi bi-star text-muted me-1"></i>'
                for i in range(5)
            ])
            
            return mark_safe(
                f'<div class="star-rating" title="Рейтинг: {rating}">'
                f'{stars}<small class="text-muted ms-2">{rating}</small>'
                f'</div>'
            )
        except (ValueError, TypeError):
            return format_html(
                '<span class="text-muted">'
                '<i class="bi bi-question-circle me-1"></i>Неверный формат'
                '</span>'
            )
    
    star_rating_display.short_description = 'Рейтинг'
    star_rating_display.allow_tags = True

class AdminDisplayMixin:
    """
    Миксин для отображения иконок и контента в админке.
    
    Атрибуты:
        icon_field (str): имя поля с иконкой
        content_field (str): имя поля с контентом
        icon_html_class (str): CSS класс для иконки
        content_preview_length (Optional[int]): максимальная длина превью контента
    """
    
    icon_field: str = 'icon'
    content_field: str = 'content'
    icon_html_class: str = 'fs-3'
    content_preview_length: Optional[int] = 100
    
    def get_icon_html(self, icon: str) -> str:
        """
        Генерация HTML для иконки.
        
        Args:
            icon: Текст или HTML иконки
            
        Returns:
            HTML-строка иконки
        """
        if not icon:
            return ''
        return f'<span class="{self.icon_html_class}" title="{icon}">{icon}</span>'
    
    def get_content_html(self, content: str) -> str:
        """
        Генерация HTML для контента с поддержкой Markdown.
        
        Args:
            content: Текст контента
            
        Returns:
:            HTML-строка с отформатированным контентом
        """
        if not content:
            return ''
        
        # Ограничение длины превью
        preview = content
        if self.content_preview_length and len(content) > self.content_preview_length:
            preview = content[:self.content_preview_length] + '...'
        
        try:
            # Безопасное преобразование Markdown
            html = markdown(preview, extensions=['extra'])
            return html
        except Exception:
            # В случае ошибки возвращаем обычный текст
            return preview
    
    def display_icon(self, obj: Any) -> str:
        """
        Отображение иконки в list_display.
        
        Args:
            obj: Объект модели
            
        Returns:
            HTML-строка или дефис
        """
        icon = getattr(obj, self.icon_field, None)
        if icon:
            return mark_safe(self.get_icon_html(icon))
        return "-"
    
    display_icon.short_description = 'Иконка'
    display_icon.admin_order_field = 'icon'
    display_icon.allow_tags = True
    
    def display_content_preview(self, obj: Any) -> str:
        """
        Отображение превью контента в list_display.
        
        Args:
            obj: Объект модели
            
        Returns:
            HTML-строка с превью контента
        """
        content = getattr(obj, self.content_field, None)
        if content:
            html = self.get_content_html(str(content))
            return mark_safe(
                f'<div class="content-preview" title="{content[:200]}...">'
                f'{html}'
                f'</div>'
            )
        return "-"
    
    display_content_preview.short_description = 'Содержание'
    display_content_preview.allow_tags = True
    
    def get_list_display(self, request) -> Tuple:
        """
        Автоматическое добавление методов в list_display.
        
        Args:
            request: HttpRequest объект
            
        Returns:
            Кортеж с именами методов для отображения
        """
        list_display = super().get_list_display(request)
        if not list_display:
            list_display = ()
        
        # Преобразуем в список для удобства работы
        display_list = list(list_display)
        
        # Автоматически добавляем методы, если они не указаны явно
        if hasattr(self, 'display_icon') and 'display_icon' not in display_list:
            display_list.insert(0, 'display_icon')
        
        if hasattr(self, 'display_content_preview') and 'display_content_preview' not in display_list:
            display_list.insert(1, 'display_content_preview')
        
        return tuple(display_list)
    
    def created_at_display(self, obj):
        """Форматированное отображение даты создания"""
        if obj.created_at:
            local_time = timezone.localtime(obj.created_at)
            return format_html(
                '<span title="{}">{}</span><br><small style="color: #999;">{}</small>',
                obj.created_at.isoformat(),
                local_time.strftime('%d.%m.%Y'),
                local_time.strftime('%H:%M')
            )
        return '-'
    created_at_display.short_description = 'Создано'
    created_at_display.admin_order_field = 'created_at'

    def updated_at_display(self, obj):
        """Форматированное отображение даты обновления"""
        if obj.updated_at:
            local_time = timezone.localtime(obj.updated_at)
            return format_html(
                '<span title="{}">{}</span><br><small style="color: #999;">{}</small>',
                obj.updated_at.isoformat(),
                local_time.strftime('%d.%m.%Y'),
                local_time.strftime('%H:%M')
            )
        return '-'
    updated_at_display.short_description = 'Обновлено'
    updated_at_display.admin_order_field = 'updated_at'

    def boolean_icon_display(self, value):
        """Отображение булевых значений с иконками"""
        if value:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓</span>'
            )
        return format_html(
            '<span style="color: #dc3545;">✗</span>'
        )

```


-----

# Файл: apps.py

```
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
```


-----

# Файл: __init.py__

```
"""
Модуль common - общие утилиты и инструменты для всего проекта.
Включает утилиты для админки, обработки текста, файлов, дат и шаблонных тегов.
"""

default_app_config = 'common.apps.CommonConfig'

__version__ = '1.0.0'
__author__ = 'Artem Fomin'
__description__ = 'Общие утилиты для Django проекта'
```


-----

# Файл: templatetags\common_tags.py

```
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
```


-----

# Файл: templatetags\__init__.py

```
"""
Шаблонные теги для проекта.
"""
```


-----

# Файл: utils\communications.py

```
"""
Утилиты для коммуникаций (email, Telegram и т.д.).
"""

import logging
from typing import List, Optional
from django.apps import apps
from django.core.mail import send_mail
from django.conf import settings

# Настройка логгера
logger = logging.getLogger(__name__)


class Communications:
    """Класс для управления коммуникациями."""
    
    @staticmethod
    def email_settings_ready() -> bool:
        """
        Проверяет, настроена ли отправка email.
        
        Returns:
            True если все настройки заданы
        """
        required_settings = [
            'EMAIL_HOST',
            'EMAIL_PORT', 
            'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD',
            'DEFAULT_FROM_EMAIL'
        ]
        
        for setting in required_settings:
            if not getattr(settings, setting, None):
                logger.warning(f"Настройка email не задана: {setting}")
                return False
        
        return True
    
    @staticmethod
    def send_email(
        subject: str,
        message: str,
        recipient_list: List[str],
        html_message: Optional[str] = None,
        fail_silently: bool = False
    ) -> bool:
        """
        Отправляет email.
        
        Args:
            subject: Тема письма
            message: Текстовое сообщение
            recipient_list: Список получателей
            html_message: HTML версия сообщения
            fail_silently: Не выбрасывать исключения
            
        Returns:
            True если письмо отправлено успешно
        """
        if not Communications.email_settings_ready():
            logger.warning(
                "Настройки email не заданы. Письмо не отправлено.",
                extra={
                    'subject': subject,
                    'recipients': recipient_list,
                    'message_preview': message[:100]
                }
            )
            
            # Вывод в консоль для разработки
            print(f"\n{'='*50}")
            print("EMAIL (не отправлен - настройки не заданы):")
            print(f"Subject: {subject}")
            print(f"To: {', '.join(recipient_list)}")
            print(f"Message: {message[:200]}...")
            print(f"{'='*50}\n")
            
            return False
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=fail_silently
            )
            
            logger.info(
                f"Email отправлен успешно: {subject}",
                extra={'recipient_count': len(recipient_list)}
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Ошибка при отправке email: {e}",
                extra={'subject': subject, 'recipients': recipient_list},
                exc_info=True
            )
            
            if not fail_silently:
                raise
            return False
    
    @staticmethod
    def send_email_to_user(
        subject: str,
        message: str,
        email: str,
        html_message: Optional[str] = None
    ) -> bool:
        """
        Отправляет email пользователю.
        
        Args:
            subject: Тема письма
            message: Текстовое сообщение
            email: Email получателя
            html_message: HTML версия сообщения
            
        Returns:
            True если письмо отправлено успешно
        """
        if not email:
            logger.warning("Не указан email получателя")
            return False
        
        return Communications.send_email(
            subject=subject,
            message=message,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=True
        )
    
    @staticmethod
    def send_email_to_team(
        subject: str,
        message: str,
        html_message: Optional[str] = None,
        include_superusers: bool = True,
        include_staff: bool = True
    ) -> bool:
        """
        Отправляет email команде (суперпользователям и staff).
        
        Args:
            subject: Тема письма
            message: Текстовое сообщение
            html_message: HTML версия сообщения
            include_superusers: Включать суперпользователей
            include_staff: Включать staff пользователей
            
        Returns:
            True если письмо отправлено успешно
        """
        try:
            # Пытаемся получить модель Profile или User
            try:
                Profile = apps.get_model('users', 'Profile')
                user_model = Profile
            except LookupError:
                from django.contrib.auth.models import User
                user_model = User
            
            # Собираем получателей
            recipients = []
            
            if include_superusers:
                superusers = user_model.objects.filter(is_superuser=True)
                recipients.extend([u.email for u in superusers if u.email])
            
            if include_staff:
                staff_users = user_model.objects.filter(is_staff=True)
                recipients.extend([u.email for u in staff_users if u.email])
            
            # Убираем дубликаты
            recipients = list(set(recipients))
            
            if not recipients:
                logger.warning("Нет получателей для отправки письма команде")
                print("\nНет получателей для отправки письма команде")
                return False
            
            return Communications.send_email(
                subject=subject,
                message=message,
                recipient_list=recipients,
                html_message=html_message,
                fail_silently=True
            )
            
        except Exception as e:
            logger.error(
                f"Ошибка при отправке письма команде: {e}",
                exc_info=True
            )
            print(f"\nОшибка при отправке письма команде: {e}")
            return False
    
    @staticmethod
    def send_telegram_message(
        message: str,
        chat_ids: Optional[List[str]] = None,
        token: Optional[str] = None,
        parse_mode: str = 'HTML'
    ) -> bool:
        """
        Отправляет сообщение в Telegram.
        
        Args:
            message: Сообщение для отправки
            chat_ids: Список ID чатов
            token: Токен бота Telegram
            parse_mode: Режим парсинга ('HTML' или 'Markdown')
            
        Returns:
            True если сообщение отправлено успешно
        """
        try:
            import telepot
        except ImportError:
            logger.error("Библиотека telepot не установлена")
            print("Для отправки Telegram сообщений установите telepot: pip install telepot")
            return False
        
        # Получаем настройки
        token = token or getattr(settings, 'TELEGRAM_TOKEN', None)
        chat_ids = chat_ids or getattr(settings, 'TELEGRAM_CHAT_IDS', [])
        
        if not token or not chat_ids:
            logger.warning(
                "Настройки Telegram не заданы. Сообщение не отправлено.",
                extra={'message_preview': message[:100]}
            )
            
            print(f"\n{'='*50}")
            print("TELEGRAM (не отправлено - настройки не заданы):")
            print(f"Message: {message}")
            print(f"{'='*50}\n")
            return False
        
        try:
            bot = telepot.Bot(token)
            success_count = 0
            
            for chat_id in chat_ids:
                if not chat_id:
                    continue
                
                try:
                    bot.sendMessage(chat_id, message, parse_mode=parse_mode)
                    success_count += 1
                    logger.debug(f"Telegram сообщение отправлено в chat_id: {chat_id}")
                except Exception as e:
                    logger.error(
                        f"Ошибка при отправке Telegram сообщения в {chat_id}: {e}",
                        exc_info=True
                    )
            
            if success_count > 0:
                logger.info(
                    f"Telegram сообщения отправлены в {success_count} чат(ов)",
                    extra={'total_chats': len(chat_ids)}
                )
                return True
            else:
                logger.warning("Telegram сообщения не были отправлены ни в один чат")
                return False
                
        except Exception as e:
            logger.error(
                f"Ошибка при инициализации Telegram бота: {e}",
                exc_info=True
            )
            return False
```


-----

# Файл: utils\dates.py

```
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
```


-----

# Файл: utils\files.py

```
"""
Утилиты для работы с файлами и изображениями.
"""

import os
import re
from typing import Tuple
from PIL import Image
import pytils


class FileUtils:
    """Утилиты для работы с файлами."""
    
    @staticmethod
    def generate_file_path(
        instance, 
        filename: str, 
        directory: str = 'files'
    ) -> str:
        """
        Генерирует путь для сохранения файла.
        
        Args:
            instance: Объект модели
            filename: Имя оригинального файла
            directory: Поддиректория для файлов
            
        Returns:
            Путь для сохранения файла
        """
        try:
            # Транслитерация и очистка имени файла
            transliterated = pytils.translit.translify(filename)
            name, ext = os.path.splitext(transliterated)
            name = re.sub(r'[\W]+', '_', name.strip())
            file_name = f'{name}{ext}'.lower()
            
            # Определение имени класса
            class_name = instance.__class__.__name__.lower()
            
            # Определение именной папки
            named_folder = (
                getattr(instance, 'slug', None) or
                getattr(instance, 'nic_name', None) or
                str(getattr(instance, 'id', 'no_id'))
            )
            
            # Очистка имени папки
            if named_folder:
                named_folder = re.sub(r'[\W]+', '_', str(named_folder).strip())
            else:
                named_folder = 'no_id'
            
            # Формирование пути
            path = f'{class_name}/{named_folder}/{directory}/'
            return os.path.join(path, file_name)
            
        except Exception as e:
            # В случае ошибки возвращаем простой путь
            return f'uploads/{filename}'
    
    @staticmethod
    def resize_and_crop_image(
        image_path: str, 
        max_size: Tuple[int, int] = (150, 150),
        quality: int = 85
    ) -> None:
        """
        Изменяет размер и обрезает изображение.
        
        Оригинальная логика: 
        1. Определяем меньшую сторону изображения
        2. Масштабируем по меньшей стороне до max_size
        3. Обрезаем до нужного размера
        
        Args:
            image_path: Путь к изображению
            max_size: Максимальный размер (ширина, высота)
            quality: Качество JPEG (1-100)
            
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если размер невалидный
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Файл не найден: {image_path}")
        
        if max_size[0] <= 0 or max_size[1] <= 0:
            raise ValueError("Размер должен быть положительным числом.")
        
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # Определяем, какая сторона изображения меньше
                if width < height:
                    # Устанавливаем ширину в max_size[0], сохраняя пропорции
                    new_width = max_size[0]
                    new_height = int((new_width / width) * height)
                else:
                    # Устанавливаем высоту в max_size[1], сохраняя пропорции
                    new_height = max_size[1]
                    new_width = int((new_height / height) * width)
                
                # Меняем размер с сохранением пропорций
                img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Обрезка изображения по центру
                left = (new_width - max_size[0]) / 2
                right = (new_width + max_size[0]) / 2
                top = (new_height - max_size[1]) / 2
                bottom = (new_height + max_size[1]) / 2
                
                # Преобразуем в целые числа для метода crop
                left = int(left)
                top = int(top)
                right = int(right)
                bottom = int(bottom)
                
                img = img.crop((left, top, right, bottom))
                
                # Определяем формат для сохранения
                if image_path.lower().endswith(('.png', '.gif', '.bmp')):
                    img.save(image_path, optimize=True)
                else:
                    img.save(image_path, 'JPEG', quality=quality, optimize=True)
                    
        except Exception as e:
            raise RuntimeError(f"Ошибка при обработке изображения: {e}")
    
    @staticmethod
    def resize_with_transparent_background(
        image_path: str,
        max_size: Tuple[int, int] = (150, 150),
        background_color: Tuple[int, int, int, int] = (255, 255, 255, 0)
    ) -> None:
        """
        Изменяет размер изображения с прозрачным фоном.
        
        Args:
            image_path: Путь к изображению
            max_size: Максимальный размер (ширина, высота)
            background_color: Цвет фона (R, G, B, A)
            
        Raises:
            FileNotFoundError: Если файл не найден
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Файл не найден: {image_path}")
        
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # Определяем коэффициент масштабирования для большей стороны
                if width > height:
                    scale_factor = max_size[0] / width
                else:
                    scale_factor = max_size[1] / height
                
                # Вычисляем новые размеры
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                
                # Изменяем размер изображения
                img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Создаем новое изображение с прозрачным фоном
                new_img = Image.new("RGBA", max_size, background_color)
                
                # Вычисляем координаты для размещения по центру
                left = (max_size[0] - new_width) // 2
                top = (max_size[1] - new_height) // 2
                
                # Размещаем измененное изображение на новом фоне
                if img.mode == 'RGBA':
                    new_img.paste(img, (left, top), img)
                else:
                    new_img.paste(img, (left, top))
                
                # Сохраняем результат
                new_img.save(image_path, 'PNG', optimize=True)
                
        except Exception as e:
            raise RuntimeError(f"Ошибка при обработке изображения: {e}")
    
    @staticmethod
    def remove_empty_directories(root_path: str, dry_run: bool = False) -> int:
        """
        Удаляет пустые директории.
        
        Args:
            root_path: Корневой путь для поиска
            dry_run: Режим предпросмотра (не удалять)
            
        Returns:
            Количество удаленных директорий
        """
        if not os.path.exists(root_path):
            raise FileNotFoundError(f"Директория не найдена: {root_path}")
        
        removed_count = 0
        
        try:
            for root, dirs, files in os.walk(root_path, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    
                    try:
                        if not os.listdir(dir_path):  # Директория пуста
                            if not dry_run:
                                os.rmdir(dir_path)
                                print(f'Удалена пустая папка: {dir_path}')
                            else:
                                print(f'Найдена пустая папка: {dir_path}')
                            removed_count += 1
                    except (OSError, PermissionError) as e:
                        print(f'Не удалось удалить {dir_path}: {e}')
                        continue
                        
        except Exception as e:
            print(f'Ошибка при удалении пустых директорий: {e}')
        
        return removed_count
    
    @staticmethod
    def get_file_size(file_path: str, human_readable: bool = True) -> str:
        """
        Получает размер файла.
        
        Args:
            file_path: Путь к файлу
            human_readable: Форматировать в читаемый вид
            
        Returns:
            Размер файла
        """
        try:
            size = os.path.getsize(file_path)
            
            if human_readable:
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if size < 1024.0:
                        return f"{size:.1f} {unit}"
                    size /= 1024.0
                return f"{size:.1f} PB"
            else:
                return str(size)
                
        except (OSError, FileNotFoundError):
            return "0 B"
```


-----

# Файл: utils\text.py

```
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
```


-----

# Файл: utils\__init__.py

```
"""
Утилиты общего назначения для проекта.
"""

from .text import TextUtils
from .files import FileUtils
from .dates import DateUtils
from .communications import Communications

__all__ = [
    'TextUtils',
    'FileUtils', 
    'DateUtils',
    'Communications',
]
```
