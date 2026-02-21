"""
Утилиты для улучшения админ-панели Django.
"""

from django.templatetags.static import static
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
