# Файл: apps.py

```
from django.apps import AppConfig


class IntellectualPropertyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'intellectual_property'
    verbose_name = 'Результаты интеллектуальной деятельности'

```


-----

# Файл: tests.py

```
from django.test import TestCase

# Create your tests here.

```


-----

# Файл: urls.py

```
from django.urls import path


# Маршруты результатов интеллектуальной собственности
urlpatterns = [
]
```


-----

# Файл: __init__.py

```

```


-----

# Файл: admin\admin_fips_catalogue.py

```
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from intellectual_property.models.models_fips_catalogue import FipsOpenDataCatalogue


@admin.register(FipsOpenDataCatalogue)
class FipsOpenDataCatalogueAdmin(admin.ModelAdmin):
    """
    Простой административный интерфейс для модели FipsOpenDataCatalogue.
    """
    
    list_display = [
        'name',
        'ip_type',
        'publication_date',
        'upload_date',
    ]
    
    list_filter = [
        'ip_type',
        'publication_date',
    ]
    
    search_fields = [
        'name',
        'ip_type__name',
    ]
    
    readonly_fields = [
        'upload_date',
        'last_modified',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('ip_type', 'name', 'catalogue_file', 'publication_date', 'description')
        }),
        (_('Служебная информация'), {
            'fields': ('upload_date', 'last_modified'),
            'classes': ('collapse',),
        }),
    )
    
    autocomplete_fields = ['ip_type']
    date_hierarchy = 'publication_date'

```


-----

# Файл: admin\admin_ip.py

```
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from intellectual_property.models.models_ip import IPType, ProtectionDocumentType


@admin.register(ProtectionDocumentType)
class ProtectionDocumentTypeAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели ProtectionDocumentType.
    """
    list_display = [
        'name',
        'description',
        'slug',
    ]
    
    search_fields = [
        'name',
        'description',
        'slug',
    ]
    
    list_filter = [
        'name',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description'),
            'description': _('Основная информация о виде охранного документа')
        }),
        (_('URL параметры'), {
            'fields': ('slug',),
            'description': _('Параметры для формирования URL'),
            'classes': ('wide',),
        }),
    )
    
    readonly_fields = ['slug']
    
    def get_queryset(self, request):
        """
        Оптимизация запросов к БД.
        """
        return super().get_queryset(request).annotate(
            ip_types_count=models.Count('ip_types')
        )


@admin.register(IPType)
class IPTypeAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели IPType.
    """
    # Поля для отображения в списке
    list_display = [
        'name',
        'description',
        'protection_document_link',
        'validity_duration',
        'slug',
    ]
    
    # Поля для поиска
    search_fields = [
        'name',
        'description',
        'slug',
        'protection_document_type__name',
    ]
    
    # Фильтры в правой панели
    list_filter = [
        'protection_document_type',
        'name',
    ]
    
    # Поля для редактирования
    fieldsets = (
        (None, {
            'fields': ('name', 'description'),
            'description': _('Основная информация о типе РИД')
        }),
        (_('Срок действия'), {
            'fields': ('validity_duration',),
            'description': _('Срок действия охранного документа'),
            'classes': ('wide',),
        }),
        (_('Связи'), {
            'fields': ('protection_document_type',),
            'description': _('Связь с видом охранного документа'),
            'classes': ('wide',),
        }),
        (_('URL параметры'), {
            'fields': ('slug',),
            'description': _('Параметры для формирования URL'),
            'classes': ('wide',),
        }),
    )
    
    # Поля только для чтения
    readonly_fields = ['slug']
    
    # Фильтры по связанным полям
    autocomplete_fields = ['protection_document_type']
    
    # Группировка по полям
    list_display_links = ['name']
    
    def get_queryset(self, request):
        """
        Оптимизация запросов к БД.
        """
        return super().get_queryset(request).select_related(
            'protection_document_type'
        )
    
    def protection_document_link(self, obj):
        """
        Ссылка на связанный вид охранного документа.
        Универсальный метод получения URL.
        """
        if obj.protection_document_type:
            try:
                # Способ 1: Пробуем стандартный формат admin:app_model_action
                url = reverse(
                    f'admin:{obj.protection_document_type._meta.app_label}_{obj.protection_document_type._meta.model_name}_change',
                    args=[obj.protection_document_type.id]
                )
            except:
                try:
                    # Способ 2: Пробуем формат без app_label
                    url = reverse(
                        f'{obj.protection_document_type._meta.model_name}_change',
                        args=[obj.protection_document_type.id]
                    )
                except:
                    try:
                        # Способ 3: Пробуем использовать django.contrib.admin.utils.get_admin_url
                        from django.contrib.admin.utils import get_admin_url
                        url = get_admin_url(admin.site, obj.protection_document_type, 'change')
                    except:
                        # Если ничего не работает, возвращаем просто текст без ссылки
                        return obj.protection_document_type.name
            
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.protection_document_type.name
            )
        return '-'
    protection_document_link.short_description = _('Вид охранного документа')
    protection_document_link.admin_order_field = 'protection_document_type__name'
    
    def get_readonly_fields(self, request, obj=None):
        """
        Динамическое определение readonly полей.
        """
        readonly_fields = list(self.readonly_fields)
        
        if obj:  # Редактирование существующего объекта
            readonly_fields.extend(['slug'])
        
        return readonly_fields
    
    def get_list_filter(self, request):
        """
        Динамическое определение фильтров.
        """
        list_filter = list(self.list_filter)
        return list_filter
    
    def save_model(self, request, obj, form, change):
        """
        Действия при сохранении модели.
        """
        super().save_model(request, obj, form, change)
        
        action = _('обновлен') if change else _('создан')
        self.message_user(
            request,
            _('Тип РИД "{}" успешно {}').format(obj.name, action),
            level='SUCCESS'
        )
    
    def response_change(self, request, obj):
        """
        Настройка ответа после изменения.
        """
        if "_continue" in request.POST:
            self.message_user(
                request,
                _('Продолжаем редактирование "{}"').format(obj.name),
                level='INFO'
            )
        return super().response_change(request, obj)
```


-----

# Файл: admin\__init__.py

```
import os
import glob

# Автоматически импортируем все файлы админки из папки
admin_files = glob.glob(os.path.dirname(__file__) + "/*.py")
for module in admin_files:
    if not module.endswith('__init__.py'):
        module_name = os.path.basename(module)[:-3]
        exec(f"from .{module_name} import *")
```


-----

# Файл: forms\__init__.py

```
import os
import glob

# Автоматически импортируем все формы из файлов в папке
model_files = glob.glob(os.path.dirname(__file__) + "/*.py")
for module in model_files:
    if not module.endswith('__init__.py'):
        module_name = os.path.basename(module)[:-3]
        exec(f"from .{module_name} import *")
```


-----

# Файл: models\models_fips_catalogue.py

```
from django.db import models

from intellectual_property.models.models_ip import IPType


class FipsOpenDataCatalogue(models.Model):
    """
    Модель для хранения данных из каталога открытых данных ФИПС Роспатента.
    """
    
    ip_type = models.ForeignKey(
        IPType,
        on_delete=models.PROTECT,
        verbose_name='Тип РИД',
        help_text='Тип РИД, к которому относится каталог',
        related_name='catalogues',
        db_index=True
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name='Название каталога',
        help_text='Название каталога (автоматически извлекается из имени файла)',
        blank=False,
        null=False
    )
    
    catalogue_file = models.FileField(
        upload_to='ip_catalogue/%Y/%m/',
        verbose_name='CSV файл каталога',
        help_text='CSV файл каталога с сайта Роспатента',
        blank=True,
        null=True
    )
    
    publication_date = models.DateField(
        verbose_name='Дата публикации каталога',
        help_text='Дата публикации каталога на сайте Роспатента',
        blank=True,
        null=True,
        db_index=True
    )
    
    upload_date = models.DateTimeField(
        verbose_name='Дата загрузки',
        help_text='Дата и время загрузки файла в систему',
        auto_now_add=True
    )
    
    last_modified = models.DateTimeField(
        verbose_name='Дата последнего изменения',
        help_text='Дата и время последнего изменения записи',
        auto_now=True
    )
    
    description = models.TextField(
        verbose_name='Описание',
        help_text='Дополнительная информация о каталоге',
        blank=True
    )
    
    def __str__(self):
        if self.name:
            return self.name
        date_str = self.publication_date.strftime('%d.%m.%Y') if self.publication_date else 'Дата неизвестна'
        return f"Каталог {self.ip_type.name} от {date_str}"
    
    class Meta:
        verbose_name = 'Каталог открытых данных ФИПС'
        verbose_name_plural = 'Каталоги открытых данных ФИПС'
        ordering = ['-publication_date', '-upload_date']
        indexes = [
            models.Index(fields=['ip_type', 'publication_date']),
            models.Index(fields=['publication_date']),
            models.Index(fields=['name']),
        ]
        unique_together = ['id', 'publication_date']

```


-----

# Файл: models\models_ip.py

```
from django.db import models
from common.utils.text import TextUtils

class ProtectionDocumentType(models.Model):
    """
    Модель для хранения видов охранных документов.
    """
    
    name = models.CharField(
        max_length=255,
        verbose_name='Наименование',
        help_text='Наименование вида охранного документа',
        unique=True,
        db_index=True
    )
    
    description = models.TextField(
        verbose_name='Описание',
        help_text='Подробное описание вида охранного документа',
        blank=True
    )
    
    slug = models.SlugField(
        max_length=255,
        verbose_name='URL-идентификатор',
        help_text='Уникальный идентификатор для использования в URL',
        unique=True,
        db_index=True
    )
    
    class Meta:
        verbose_name = 'Вид охранного документа'
        verbose_name_plural = 'Виды охранных документов'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
        super().save(*args, **kwargs)


class IPType(models.Model):
    """
    Модель для хранения типов результатов интеллектуальной деятельности (РИД).
    """
    
    name = models.CharField(
        max_length=255,
        verbose_name='Наименование',
        help_text='Наименование типа РИД',
        unique=True,
        db_index=True
    )
    
    description = models.TextField(
        verbose_name='Описание',
        help_text='Подробное описание типа РИД и его характеристик',
        blank=True
    )
    
    protection_document_type = models.ForeignKey(
        ProtectionDocumentType,
        on_delete=models.PROTECT,
        verbose_name='Вид охранного документа',
        help_text='Тип документа, удостоверяющего охранные права на данный РИД',
        related_name='ip_types',
        db_index=True
    )
    
    validity_duration = models.PositiveIntegerField(
        verbose_name='Срок действия, лет',
        help_text='Количество лет действия охранного документа',
        blank=True,
        null=True
    )
    
    slug = models.SlugField(
        max_length=255,
        verbose_name='URL-идентификатор',
        help_text='Уникальный идентификатор для использования в URL',
        unique=True,
        db_index=True
    )
    
    class Meta:
        verbose_name = 'Тип РИД'
        verbose_name_plural = 'Типы РИД'
        ordering = ['id']
        indexes = [
            models.Index(fields=['name', 'protection_document_type']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
        super().save(*args, **kwargs)
    
    @property
    def protection_document_name(self):
        """Возвращает наименование охранного документа."""
        return self.protection_document_type.name if self.protection_document_type else None


class IPObject(models.Model):
    """
    Основная модель для всех РИД.
    Использует подход Single Table Inheritance для разных типов.
    """
    pass
```


-----

# Файл: models\models_relations.py

```
from django.db import models


class Authorship(models.Model):
    """
    Связь между РИД и авторами (физическими/юридическими лицами)
    """
    pass


class Ownership(models.Model):
    """
    Связь между РИД и правообладателями (физическими/юридическими лицами)
    """
    pass
```


-----

# Файл: models\models_support.py

```
from django.db import models


class AdditionalPatent(models.Model):
    """
    Дополнительные патенты, выданные для продления срока действия
    """
    pass


class Image(models.Model):
    """
    Изображения, связанные с РИД (чертежи, рендеры, скриншоты)
    """
    pass
```


-----

# Файл: models\__init__.py

```
import os
import glob

# Автоматически импортируем все модели из файлов в папке
model_files = glob.glob(os.path.dirname(__file__) + "/*.py")
for module in model_files:
    if not module.endswith('__init__.py'):
        module_name = os.path.basename(module)[:-3]
        exec(f"from .{module_name} import *")
```


-----

# Файл: views\__init__.py

```

```
