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
from common.admin_utils import AdminDisplayMixin, AdminImageMixin
from intellectual_property.models.models_ip import AdditionalPatent, IPImage, IPObject, IPType, ProtectionDocumentType


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


@admin.register(AdditionalPatent)
class AdditionalPatentAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для дополнительных патентов.
    """
    list_display = [
        'patent_number',
        'patent_date',
        'description_short',
        'ip_objects_count',
    ]
    
    search_fields = [
        'patent_number',
        'description',
    ]
    
    list_filter = [
        'patent_date',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('patent_number', 'patent_date', 'description')
        }),
    )
    
    def description_short(self, obj):
        """Короткое описание для списка"""
        if obj.description and len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description
    description_short.short_description = _('Описание')
    
    def get_queryset(self, request):
        """Оптимизация запросов с подсчетом связанных РИД"""
        return super().get_queryset(request).annotate(
            ip_objects_count=models.Count('ip_objects')
        )
    
    def ip_objects_count(self, obj):
        """Количество РИД, связанных с этим патентом"""
        count = getattr(obj, 'ip_objects_count', 0)
        if count:
            url = reverse('admin:intellectual_property_ipobject_changelist') + f'?additional_patents__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    ip_objects_count.short_description = _('Связанных РИД')
    ip_objects_count.admin_order_field = 'ip_objects_count'


@admin.register(IPImage)
class IPImageAdmin(AdminImageMixin, admin.ModelAdmin):
    """
    Административный интерфейс для изображений РИД.
    """
    list_display = [
        'image_thumbnail',
        'title',
        'is_main',
        'sort_order',
        'ip_objects_count',
    ]
    
    search_fields = [
        'title',
        'description',
    ]
    
    list_filter = [
        'is_main',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('image', 'title', 'description', 'is_main', 'sort_order')
        }),
    )
    
    def get_queryset(self, request):
        """Оптимизация запросов с подсчетом связанных РИД"""
        return super().get_queryset(request).annotate(
            ip_objects_count=models.Count('ip_objects')
        )
    
    def ip_objects_count(self, obj):
        """Количество РИД, связанных с этим изображением"""
        count = getattr(obj, 'ip_objects_count', 0)
        if count:
            url = reverse('admin:intellectual_property_ipobject_changelist') + f'?images__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    ip_objects_count.short_description = _('Связанных РИД')
    ip_objects_count.admin_order_field = 'ip_objects_count'


@admin.register(IPObject)
class IPObjectAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Административный интерфейс для объектов РИД.
    """
    list_display = [
        'name',
        'ip_type',
        'registration_number',
        'actual_badge',
        'application_date',
        'expiration_date',
        'created_at_display',
    ]
    
    list_filter = [
        'ip_type',
        'actual',
        'application_date',
        'registration_date',
        'expiration_date',
    ]
    
    search_fields = [
        'name',
        'registration_number',
        'ea_application_number',
        'pct_application_number',
        'description',
        'abstract',
        'claims',
    ]
    
    filter_horizontal = [
        'authors',
        'owner_persons',
        'owner_organizations',
        'owner_foivs',
        'first_usage_countries',
        'additional_patents',
        'images',
        'programming_languages',
        'dbms',
        'operating_systems',
    ]
    
    autocomplete_fields = [
        'ip_type',
        'paris_convention_priority_country',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'all_owners_display',
    ]
    
    fieldsets = (
        (_('📋 Основная информация'), {
            'fields': (
                'name',
                'ip_type',
                'actual',
            )
        }),
        
        (_('👥 Авторы и правообладатели'), {
            'fields': (
                'authors',
                'owner_persons',
                'owner_organizations',
                'owner_foivs',
                'all_owners_display',
            ),
            'classes': ('wide',),
        }),
        
        (_('📅 Даты и сроки'), {
            'fields': (
                ('creation_year', 'publication_year', 'update_year'),
                ('application_date', 'registration_date'),
                ('patent_starting_date', 'expiration_date'),
            ),
            'classes': ('wide',),
        }),
        
        (_('🔢 Номера и идентификаторы'), {
            'fields': (
                'registration_number',
                'revoked_patent_number',
                'publication_url',
            ),
            'classes': ('wide',),
        }),
        
        (_('🌍 Евразийская заявка'), {
            'fields': (
                'ea_application_number',
                'ea_application_date',
                ('ea_application_publish_number', 'ea_application_publish_date'),
            ),
            'classes': ('collapse',),
        }),
        
        (_('🌐 PCT заявка'), {
            'fields': (
                'pct_application_number',
                'pct_application_date',
                ('pct_application_publish_number', 'pct_application_publish_date'),
                'pct_application_examination_start_date',
            ),
            'classes': ('collapse',),
        }),
        
        (_('🏛️ Парижская конвенция'), {
            'fields': (
                'paris_convention_priority_number',
                'paris_convention_priority_date',
                'paris_convention_priority_country',
            ),
            'classes': ('collapse',),
        }),
        
        (_('📍 Использование топологии'), {
            'fields': (
                'first_usage_date',
                'first_usage_countries',
            ),
            'classes': ('collapse',),
        }),
        
        (_('📄 Текстовые описания'), {
            'fields': (
                'abstract',
                'claims',
                'description',
                'source_code_deposit',
            ),
            'classes': ('wide',),
        }),
        
        (_('📎 Связанные объекты'), {
            'fields': (
                'additional_patents',
                'images',
            ),
            'classes': ('wide',),
        }),
        
        (_('💻 IT-специфика'), {
            'fields': (
                'programming_languages',
                'dbms',
                'operating_systems',
            ),
            'classes': ('collapse',),
        }),
        
        (_('⚙️ Системная информация'), {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    def actual_badge(self, obj):
        """Отображение статуса действия правовой охраны"""
        if obj.actual:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 7px; border-radius: 10px;">✓ Действует</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 7px; border-radius: 10px;">✗ Не действует</span>'
        )
    actual_badge.short_description = _('Статус')
    actual_badge.admin_order_field = 'actual'
    
    def all_owners_display(self, obj):
        """Отображение всех правообладателей в детальной странице"""
        owners = obj.all_owners
        if owners:
            html = ['<ul style="margin: 0; padding-left: 20px;">']
            for owner in owners:
                # Пытаемся получить ссылку на админку
                try:
                    app_label = owner._meta.app_label
                    model_name = owner._meta.model_name
                    url = reverse(f'admin:{app_label}_{model_name}_change', args=[owner.pk])
                    html.append(f'<li><a href="{url}">{owner}</a></li>')
                except:
                    html.append(f'<li>{owner}</li>')
            html.append('</ul>')
            return format_html(''.join(html))
        return '-'
    all_owners_display.short_description = _('Все правообладатели')
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related(
            'ip_type',
            'paris_convention_priority_country',
        ).prefetch_related(
            'authors',
            'owner_persons',
            'owner_organizations',
            'owner_foivs',
            'first_usage_countries',
            'programming_languages',
            'dbms',
            'operating_systems',
        )
    
    actions = ['mark_as_actual', 'mark_as_not_actual']
    
    @admin.action(description=_('✅ Отметить как действующие'))
    def mark_as_actual(self, request, queryset):
        updated = queryset.update(actual=True)
        self.message_user(request, _('Обновлено {} объектов РИД').format(updated))
    
    @admin.action(description=_('❌ Отметить как недействующие'))
    def mark_as_not_actual(self, request, queryset):
        updated = queryset.update(actual=False)
        self.message_user(request, _('Обновлено {} объектов РИД').format(updated))
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
from core.models.models_foiv import FOIV
from core.models.models_geo import Country
from core.models.models_it import DBMS, OperatingSystem, ProgrammingLanguage
from core.models.models_organization import Organization
from core.models.models_person import Person

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


class AdditionalPatent(models.Model):
    """
    Дополнительные патенты, выданные для продления срока действия.
    """
    patent_number = models.CharField(
        max_length=50,
        verbose_name='Номер дополнительного патента',
        null=True,
        blank=True,
        db_index=True
    )
    patent_date = models.DateField(
        verbose_name='Дата выдачи дополнительного патента',
        null=True,
        blank=True
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )
    
    class Meta:
        verbose_name = 'Дополнительный патент'
        verbose_name_plural = 'Дополнительные патенты'
    
    def __str__(self):
        return self.patent_number


class IPImage(models.Model):
    """
    Изображения, связанные с РИД (чертежи, рендеры, скриншоты).
    """
    image = models.ImageField(
        upload_to='ip_images/%Y/%m/',
        verbose_name='Изображение'
    )
    title = models.CharField(
        max_length=255,
        verbose_name='Название',
        blank=True
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )
    is_main = models.BooleanField(
        default=False,
        verbose_name='Главное изображение'
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Порядок сортировки'
    )
    
    class Meta:
        verbose_name = 'Изображение РИД'
        verbose_name_plural = 'Изображения РИД'
        ordering = ['sort_order', 'id']
    
    def __str__(self):
        return self.title or f"Изображение {self.id}"


class IPObject(models.Model):
    """
    Основная модель для всех РИД.
    """
    
    # === Основная информация ===
    name = models.CharField(
        max_length=500,
        verbose_name='Наименование РИД',
        db_index=True
    )
    
    ip_type = models.ForeignKey(
        IPType,
        on_delete=models.PROTECT,
        verbose_name='Вид РИД',
        related_name='ip_objects',
        null=True,
        blank=True,
        db_index=True
    )
    
    actual = models.BooleanField(
        default=True,
        verbose_name='Признак действия правовой охраны',
        help_text='Отметьте, если правовая охрана действует',
        db_index=True
    )
    
    # === Авторы и правообладатели ===
    authors = models.ManyToManyField(
        Person,
        related_name='authored_ip_objects',
        verbose_name='Авторы',
        blank=True
    )
    
    owner_foivs = models.ManyToManyField(
        FOIV,
        related_name='owned_ip_objects_foiv',
        verbose_name='Правообладатели (ФОИВ)',
        blank=True
    )
    owner_organizations = models.ManyToManyField(
        Organization,
        related_name='owned_ip_objects_organization',
        verbose_name='Правообладатели (организации)',
        blank=True
    )
    owner_persons = models.ManyToManyField(
        Person,
        related_name='owned_ip_objects_person',
        verbose_name='Правообладатели (физ. лица)',
        blank=True
    )
    
    # === Даты и сроки ===
    creation_year = models.PositiveSmallIntegerField(
        verbose_name='Год создания',
        null=True,
        blank=True
    )
    
    publication_year = models.PositiveSmallIntegerField(
        verbose_name='Год обнародования',
        null=True,
        blank=True
    )
    
    update_year = models.PositiveSmallIntegerField(
        verbose_name='Год обновления',
        null=True,
        blank=True
    )
    
    application_date = models.DateField(
        verbose_name='Дата подачи заявки на государственную регистрацию',
        null=True,
        blank=True
    )
    
    registration_date = models.DateField(
        verbose_name='Дата государственной регистрации',
        null=True,
        blank=True
    )
    
    patent_starting_date = models.DateField(
        verbose_name='Дата начала отсчета срока действия патента',
        null=True,
        blank=True
    )
    
    expiration_date = models.DateField(
        verbose_name='Дата истечения срока действия патента / исключительного права',
        null=True,
        blank=True
    )
    
    # === Номера и идентификаторы ===
    registration_number = models.CharField(
        max_length=50,
        verbose_name='Регистрационный номер изобретения (номер патента)',
        blank=True,
        db_index=True
    )
    
    revoked_patent_number = models.CharField(
        max_length=50,
        verbose_name='Номер аннулированного патента, признанного недействительным частично',
        blank=True
    )
    
    publication_url = models.URLField(
        max_length=500,
        verbose_name='URL публикации в открытых реестрах сайта ФИПС',
        blank=True
    )
    
    # === Евразийская заявка ===
    ea_application_number = models.CharField(
        max_length=50,
        verbose_name='Номер евразийской заявки',
        blank=True
    )
    
    ea_application_date = models.DateField(
        verbose_name='Дата подачи евразийской заявки',
        null=True,
        blank=True
    )
    
    ea_application_publish_number = models.CharField(
        max_length=50,
        verbose_name='Номер публикации евразийской заявки',
        blank=True
    )
    
    ea_application_publish_date = models.DateField(
        verbose_name='Дата публикации евразийской заявки',
        null=True,
        blank=True
    )
    
    # === PCT заявка ===
    pct_application_number = models.CharField(
        max_length=50,
        verbose_name='Номер PCT заявки',
        blank=True
    )
    
    pct_application_date = models.DateField(
        verbose_name='Дата подачи PCT заявки',
        null=True,
        blank=True
    )
    
    pct_application_publish_number = models.CharField(
        max_length=50,
        verbose_name='Номер публикации PCT заявки',
        blank=True
    )
    
    pct_application_publish_date = models.DateField(
        verbose_name='Дата публикации PCT заявки',
        null=True,
        blank=True
    )
    
    pct_application_examination_start_date = models.DateField(
        verbose_name='Дата начала рассмотрения заявки РСТ на национальной фазе',
        null=True,
        blank=True
    )
    
    # === Парижская конвенция ===
    paris_convention_priority_number = models.CharField(
        max_length=50,
        verbose_name='Номер первой заявки в государстве - участнике Парижской конвенции',
        blank=True
    )
    
    paris_convention_priority_date = models.DateField(
        verbose_name='Дата подачи первой заявки в государстве - участнике Парижской конвенции',
        null=True,
        blank=True
    )
    
    paris_convention_priority_country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        verbose_name='Код страны подачи первой заявки',
        related_name='paris_priority_ip_objects',
        null=True,
        blank=True
    )
    
    # === Использование топологии ===
    first_usage_date = models.DateField(
        verbose_name='Дата первого использования топологии',
        null=True,
        blank=True
    )
    
    first_usage_countries = models.ManyToManyField(
        Country,
        related_name='first_usage_ip_objects',
        verbose_name='Страна (страны) первого использования топологии',
        blank=True
    )
    
    # === Документы и обязательства ===
    information_about_the_obligation_to_conclude_contract_of_alienation = models.TextField(
        verbose_name='Сведения о поданном заявлении об обязательстве заключить договор об отчуждении патента',
        blank=True
    )
    
    # === Текстовые поля ===
    abstract = models.TextField(
        verbose_name='Реферат',
        blank=True
    )
    
    claims = models.TextField(
        verbose_name='Формула',
        blank=True
    )
    
    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )
    
    source_code_deposit = models.TextField(
        verbose_name='Исходный код (депонируемые материалы)',
        blank=True
    )
    
    # === Связанные модели (One-to-Many) ===
    additional_patents = models.ManyToManyField(
        AdditionalPatent,
        related_name='ip_objects',
        verbose_name='Дополнительные патенты для продления срока действия',
        blank=True
    )
    
    images = models.ManyToManyField(
        IPImage,
        related_name='ip_objects',
        verbose_name='Фотографии или рендеры изделия',
        blank=True
    )
    
    # === IT-специфика (для программ) ===
    programming_languages = models.ManyToManyField(
        ProgrammingLanguage,
        related_name='ip_objects',
        verbose_name='Язык(и) программирования',
        blank=True
    )
    
    dbms = models.ManyToManyField(
        DBMS,
        related_name='ip_objects',
        verbose_name='Система управления базами данных',
        blank=True
    )
    
    operating_systems = models.ManyToManyField(
        OperatingSystem,
        related_name='ip_objects',
        verbose_name='Целевая операционная система',
        blank=True
    )
    
    # === Системные поля ===
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания',
        null=True,
        blank=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = 'Объект РИД'
        verbose_name_plural = 'Объекты РИД'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['registration_number']),
            models.Index(fields=['application_date']),
            models.Index(fields=['registration_date']),
            models.Index(fields=['expiration_date']),
            models.Index(fields=['ip_type', 'actual']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def all_owners(self):
        """Возвращает всех правообладателей (всех типов)"""
        from itertools import chain
        return list(chain(
            self.owner_persons.all(),
            self.owner_organizations.all(),
            self.owner_foivs.all()
        ))
    
    @property
    def is_expired(self):
        """Проверяет, истек ли срок действия"""
        from django.utils import timezone
        if self.expiration_date:
            return self.expiration_date < timezone.now().date()
        return False
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
