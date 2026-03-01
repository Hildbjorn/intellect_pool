# Файл: apps.py

```
from django.apps import AppConfig


class IntellectualPropertyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'intellectual_property'
    verbose_name = 'Результаты интеллектуальной деятельности'

```


-----

# Файл: filters.py

```
import django_filters
from django import forms
from .models import IPObject, IPType

class IPObjectFilter(django_filters.FilterSet):
    """Фильтр для списка РИД."""
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        label='Наименование РИД',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск по названию...'})
    )
    registration_number = django_filters.CharFilter(
        field_name='registration_number',
        lookup_expr='icontains',
        label='Рег. номер',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Номер...'})
    )
    ip_type = django_filters.ModelChoiceFilter(
        queryset=IPType.objects.all(),
        label='Вид РИД',
        empty_label='Все виды',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    actual = django_filters.BooleanFilter(
        field_name='actual',
        label='Действует',
        widget=forms.Select(
            choices=[('', 'Все'), (True, 'Да'), (False, 'Нет')],
            attrs={'class': 'form-select'}
        )
    )
    # Добавьте другие фильтры по необходимости

    class Meta:
        model = IPObject
        fields = ['name', 'registration_number', 'ip_type', 'actual']

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
from .views.views_ip_list import *

urlpatterns = [
    path('', IPObjectListView.as_view(), name='ip_list'),
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

# Файл: management\pars_fips_catalogue_help.txt

```
python manage.py pars_fips_catalogue \
  --catalogue-id 42 \
  --ip-type invention \
  --dry-run \
  --encoding utf-8 \
  --delimiter , \
  --batch-size 1000 \
  --min-year 2020 \
  --max-year 2023 \
  --skip-filters \
  --only-active \
  --max-rows 10000 \
  --force \
  --mark-processed \
  --process-by-year \
  --year-step 1 \
  --start-year 2021

  # Только активные изобретения с 2020 года, по годам
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --only-active --process-by-year

# Тест для 2023 года (10 записей)
python manage.py pars_fips_catalogue --ip-type computer-program --min-year 2023 --max-year 2023 --max-rows 10 --process-by-year

# Принудительный перепарсинг конкретного каталога
python manage.py pars_fips_catalogue --catalogue-id 42 --force

# Все программы для ЭВМ без фильтров
python manage.py pars_fips_catalogue --ip-type computer-program --skip-filters

# ============================================================================
# ПАРСЕР КАТАЛОГОВ ОТКРЫТЫХ ДАННЫХ ФИПС РОСПАТЕНТА
# ============================================================================

# ----------------------------------------------------------------------------
# ОСНОВНЫЕ РЕЖИМЫ РАБОТЫ
# ----------------------------------------------------------------------------

# Режим ONLY-ACTIVE: парсинг только активных записей (actual = True)
# Режим MIN-YEAR 2020: парсинг только записей 2020 года и позже
# Режим MAX-YEAR 2023: парсинг только записей до 2023 года включительно
# Режим PROCESS-BY-YEAR: обработка по годам (уменьшает нагрузку на БД)
# Режим DRY-RUN: изменения НЕ будут сохранены в БД
# Режим FORCE: принудительный парсинг, игнорируя дату последней обработки

# ----------------------------------------------------------------------------
# ТИПЫ РИД ДЛЯ ПАРСИНГА
# ----------------------------------------------------------------------------

# --ip-type invention                      # Изобретения
# --ip-type utility-model                  # Полезные модели
# --ip-type industrial-design              # Промышленные образцы
# --ip-type integrated-circuit-topology    # Топологии интегральных микросхем
# --ip-type computer-program               # Программы для ЭВМ
# --ip-type database                       # Базы данных

# ----------------------------------------------------------------------------
# ПРИМЕРЫ ЗАПУСКА
# ----------------------------------------------------------------------------

# 1. ТЕСТОВЫЙ ЗАПУСК (мало записей)
# ----------------------------------------------------------------------------

# Тест для изобретений (10 записей)
python manage.py pars_fips_catalogue --ip-type invention --max-rows 10

# Тест для изобретений 2026 года (10 записей)
python manage.py pars_fips_catalogue --ip-type invention --min-year 2026 --max-rows 10

# Тест для программ для ЭВМ (активные, 2023 год, 100 записей)
python manage.py pars_fips_catalogue --ip-type computer-program --min-year 2023 --max-year 2023 --only-active --max-rows 100

# Тест в режиме DRY-RUN (проверка без сохранения)
python manage.py pars_fips_catalogue --ip-type database --min-year 2024 --dry-run --max-rows 50

# ----------------------------------------------------------------------------
# 2. ОБРАБОТКА ПО ГОДАМ (РЕКОМЕНДУЕТСЯ ДЛЯ БОЛЬШИХ ОБЪЕМОВ)
# ----------------------------------------------------------------------------

# Все изобретения с 2020 года, разбивая по годам
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --process-by-year

# Все полезные модели с 2018 по 2022 год с шагом 2 года
python manage.py pars_fips_catalogue --ip-type utility-model --min-year 2018 --max-year 2022 --process-by-year --year-step 2

# Начать обработку программ для ЭВМ с 2021 года (пропустить ранние)
python manage.py pars_fips_catalogue --ip-type computer-program --min-year 2020 --process-by-year --start-year 2021

# Только активные промышленные образцы 2023 года
python manage.py pars_fips_catalogue --ip-type industrial-design --min-year 2023 --max-year 2023 --only-active --process-by-year

# ----------------------------------------------------------------------------
# 3. ПОЛНЫЙ ПАРСИНГ (ВСЕ ЗАПИСИ)
# ----------------------------------------------------------------------------

# Все изобретения (без фильтров)
python manage.py pars_fips_catalogue --ip-type invention --skip-filters

# Все полезные модели (без фильтров)
python manage.py pars_fips_catalogue --ip-type utility-model --skip-filters

# Все программы для ЭВМ (без фильтров)
python manage.py pars_fips_catalogue --ip-type computer-program --skip-filters

# ----------------------------------------------------------------------------
# 4. ПАРСИНГ ПО КАТАЛОГАМ
# ----------------------------------------------------------------------------

# Конкретный каталог по ID
python manage.py pars_fips_catalogue --catalogue-id 42

# Конкретный каталог с принудительным перепарсингом
python manage.py pars_fips_catalogue --catalogue-id 42 --force

# Конкретный каталог с пометкой как обработанный (даже с ошибками)
python manage.py pars_fips_catalogue --catalogue-id 42 --mark-processed

# ----------------------------------------------------------------------------
# 5. ПАРСИНГ С ФИЛЬТРАЦИЕЙ ПО ГОДАМ
# ----------------------------------------------------------------------------

# Все изобретения с 2020 года
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020

# Все изобретения с 2015 по 2020 год
python manage.py pars_fips_catalogue --ip-type invention --min-year 2015 --max-year 2020

# Все изобретения с 2020 года (только активные)
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --only-active

# Все изобретения с 2020 года (только активные, по годам)
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --only-active --process-by-year

# ----------------------------------------------------------------------------
# 6. ПРОДВИНУТЫЕ СЦЕНАРИИ
# ----------------------------------------------------------------------------

# Полный перепарсинг всех изобретений с 2020 года (игнорируя даты обработки)
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --force --process-by-year

# Парсинг баз данных с кастомной кодировкой и разделителем
python manage.py pars_fips_catalogue --ip-type database --encoding cp1251 --delimiter ';' --min-year 2020

# Парсинг с большими пачками для ускорения
python manage.py pars_fips_catalogue --ip-type invention --batch-size 5000 --min-year 2020 --process-by-year

# Парсинг всех типов РИД с 2020 года (последовательно)
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --process-by-year
python manage.py pars_fips_catalogue --ip-type utility-model --min-year 2020 --process-by-year
python manage.py pars_fips_catalogue --ip-type industrial-design --min-year 2020 --process-by-year
python manage.py pars_fips_catalogue --ip-type integrated-circuit-topology --min-year 2020 --process-by-year
python manage.py pars_fips_catalogue --ip-type computer-program --min-year 2020 --process-by-year
python manage.py pars_fips_catalogue --ip-type database --min-year 2020 --process-by-year

# ----------------------------------------------------------------------------
# ПОЛНОЕ ОПИСАНИЕ ПАРАМЕТРОВ
# ----------------------------------------------------------------------------

usage: manage.py pars_fips_catalogue [-h] [--catalogue-id CATALOGUE_ID] 
                                     [--ip-type {invention,utility-model,industrial-design,integrated-circuit-topology,computer-program,database}] 
                                     [--dry-run] [--encoding ENCODING] [--delimiter DELIMITER] 
                                     [--batch-size BATCH_SIZE] [--min-year MIN_YEAR] [--max-year MAX_YEAR] 
                                     [--skip-filters] [--only-active] [--max-rows MAX_ROWS] [--force] 
                                     [--mark-processed] [--process-by-year] [--year-step YEAR_STEP] 
                                     [--start-year START_YEAR] [--version] [-v {0,1,2,3}] 
                                     [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] 
                                     [--no-color] [--force-color] [--skip-checks]

Парсинг каталогов открытых данных ФИПС Роспатента с поддержкой обработки по годам

options:
  -h, --help            show this help message and exit
  
  --catalogue-id CATALOGUE_ID
                        ID конкретного каталога для парсинга
                        
  --ip-type {invention,utility-model,industrial-design,integrated-circuit-topology,computer-program,database}
                        Тип РИД для парсинга (если не указан, парсятся все)
                        
  --dry-run             Режим проверки без сохранения в БД
  
  --encoding ENCODING   Кодировка CSV файла (по умолчанию: utf-8)
  
  --delimiter DELIMITER
                        Разделитель в CSV файле (по умолчанию: ,)
                        
  --batch-size BATCH_SIZE
                        Размер пакета для bulk-операций (по умолчанию: 100)
                        
  --min-year MIN_YEAR   Минимальный год регистрации для фильтрации (по умолчанию: 2000)
  
  --max-year MAX_YEAR   Максимальный год регистрации для фильтрации (опционально)
  
  --skip-filters        Пропустить фильтрацию (обработать все записи)
  
  --only-active         Парсить только активные патенты (actual = True)
  
  --max-rows MAX_ROWS   Максимальное количество строк для обработки (для тестирования)
  
  --force               Принудительный парсинг даже если каталог уже обработан
  
  --mark-processed      Пометить каталог как обработанный (даже если были ошибки)
  
  --process-by-year     Обрабатывать данные по годам (уменьшает нагрузку на БД)
  
  --year-step YEAR_STEP
                        Шаг по годам при обработке (по умолчанию: 1)
                        
  --start-year START_YEAR
                        Начальный год для обработки (если нужно начать не с минимального)
  
  --version             Show program's version number and exit.
  
  -v, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 
                        3=very verbose output
                        
  --settings SETTINGS   The Python path to a settings module, e.g. "myproject.settings.main". 
                        If this isn't provided, the DJANGO_SETTINGS_MODULE environment variable 
                        will be used.
                        
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g. 
                        "/home/djangoprojects/myproject".
                        
  --traceback           Display a full stack trace on CommandError exceptions.
  
  --no-color            Don't colorize the command output.
  
  --force-color         Force colorization of the command output.
  
  --skip-checks         Skip system checks.

# ----------------------------------------------------------------------------
# ПРИМЕРЫ ВЫВОДА СТАТИСТИКИ
# ----------------------------------------------------------------------------

# При обработке по годам вы увидите:
# ============================================================
# 📁 Обработка каталога: Изобретения 2024
#    ID: 42, Тип: Изобретение
# ============================================================
#   
#   📅 Найдены годы в каталоге: 2020 - 2024 (всего 5 лет)
#   
#   📅 Год 2024 (1/5)
#   🔹 Начинаем парсинг изобретений для 2024 года
#   🔹 Чтение CSV и сбор регистрационных номеров
#   🔹 Всего записей в CSV: 1250
#   ...
#   ✅ Парсинг изобретений для 2024 года завершен
#      Создано: 120, Обновлено: 30, Без изменений: 1100
#   
#   📅 Год 2023 (2/5)
#   ...

# Итоговая статистика:
# ============================================================
# 📊 ИТОГОВАЯ СТАТИСТИКА
# ============================================================
# 📁 Обработано каталогов: 1
# 📝 Всего записей обработано: 6250
# ✅ Создано: 600
# 🔄 Обновлено: 150
# ⏸️  Без изменений: 5500
# ⏭️  Пропущено всего: 0
#    └─ по дате обновления: 0
# ✅ Ошибок: 0
# ============================================================

# ----------------------------------------------------------------------------
# РЕКОМЕНДАЦИИ ПО ИСПОЛЬЗОВАНИЮ
# ----------------------------------------------------------------------------

# Для больших объемов данных (более 100 000 записей):
#   - Используйте --process-by-year для разбивки по годам
#   - Увеличьте --batch-size до 1000-5000 для ускорения
#   - Используйте --only-active если нужны только действующие патенты
#   - При проблемах с памятью уменьшите --batch-size

# Для тестирования:
#   - Всегда используйте --dry-run для проверки
#   - Ограничивайте количество записей через --max-rows
#   - Проверяйте один год через --min-year и --max-year

# Для повторного парсинга:
#   - Используйте --force для игнорирования даты обработки
#   - Используйте --mark-processed если хотите пометить как обработанный даже с ошибками

# Для отладки:
#   - Используйте -v 2 или -v 3 для подробного вывода
#   - Используйте --traceback для полной трассировки ошибок
```


-----

# Файл: management\update_ip_help.txt

```
============================================================================
КОМАНДА: update_ip - ОБНОВЛЕНИЕ ДАННЫХ РИД ПАРСИНГОМ СТРАНИЦ ФИПС
============================================================================

Команда предназначена для обновления данных объектов РИД (результатов 
интеллектуальной деятельности) путем парсинга страниц ФИПС Роспатента 
по ссылкам из поля publication_url.

============================================================================
ЛОГИКА РАБОТЫ
============================================================================

┌─────────────────┬────────────────────────────────────────────────────┐
│ Режим           │ Что делает                                         │
├─────────────────┼────────────────────────────────────────────────────┤
│ Обычный запуск  │ Находит ПЕРВУЮ запись с пустым abstract и         │
│                 │ начинает обработку с неё. Пропускает уже          │
│                 │ заполненные записи.                                │
├─────────────────┼────────────────────────────────────────────────────┤
│ --force         │ Начинает с САМОГО НАЧАЛА, обрабатывает ВСЕ        │
│                 │ записи подряд, даже если поля уже заполнены.      │
├─────────────────┼────────────────────────────────────────────────────┤
│ --only-actual   │ Обновляет ТОЛЬКО поле actual (статус) у ВСЕХ      │
│                 │ записей, независимо от заполненности других полей.│
└─────────────────┴────────────────────────────────────────────────────┘

============================================================================
СИНТАКСИС
============================================================================

python manage.py update_ip [options]

============================================================================
ОСНОВНЫЕ ПАРАМЕТРЫ
============================================================================

--ip-type {invention,utility-model,industrial-design,
           integrated-circuit-topology,computer-program,database,all}
    Тип РИД для обработки (по умолчанию: all - все типы)

--batch-size BATCH_SIZE
    Размер пакета для обработки (по умолчанию: 100)

--delay DELAY
    Задержка между запросами в секундах (по умолчанию: 1.0)

--random-delay
    Использовать случайную задержку (0.5-1.5 от указанной)

--max-requests MAX_REQUESTS
    Максимальное количество запросов (для тестирования)

--dry-run
    Режим проверки без сохранения в БД

--force
    Принудительное обновление с начала (обрабатывает все записи подряд)

--only-actual
    Обновлять только поле actual (статус) по всем записям

--start-from-latest
    Начинать с последних по дате регистрации (по умолчанию: True)

--start-from-oldest
    Начинать с самых старых записей

--start-from-id ID
    Начать обработку с конкретного ID (переопределяет автоопределение)

--timeout TIMEOUT
    Таймаут запроса в секундах (по умолчанию: 30)

--block-retry-delay SECONDS
    Задержка перед повтором после блокировки (по умолчанию: 3600 - 1 час)

--auto-retry-after-block
    Автоматически повторять после блокировки

============================================================================
ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
============================================================================

----------------------------------------------------------------------------
1. ОБЫЧНЫЙ РЕЖИМ (начинает с первого пустого abstract)
----------------------------------------------------------------------------

# Запуск с автоопределением стартовой позиции
python manage.py update_ip

# Для конкретного типа
python manage.py update_ip --ip-type invention

# С подробным выводом
python manage.py update_ip -v 2

----------------------------------------------------------------------------
2. РЕЖИМ FORCE (с начала, все подряд)
----------------------------------------------------------------------------

# Принудительное обновление всех записей с начала
python manage.py update_ip --force

# Принудительное обновление только изобретений
python manage.py update_ip --ip-type invention --force

----------------------------------------------------------------------------
3. РЕЖИМ ONLY-ACTUAL (только статус)
----------------------------------------------------------------------------

# Обновить статус у всех записей
python manage.py update_ip --only-actual

# Обновить статус у изобретений
python manage.py update_ip --ip-type invention --only-actual

----------------------------------------------------------------------------
4. ТЕСТОВЫЕ ЗАПУСКИ
----------------------------------------------------------------------------

# Проверить, что будет обновлено (без сохранения)
python manage.py update_ip --dry-run --max-requests 10

# Проверить режим force
python manage.py update_ip --force --dry-run --max-requests 5

# Проверить только статус
python manage.py update_ip --only-actual --dry-run --max-requests 5

----------------------------------------------------------------------------
5. УПРАВЛЕНИЕ СТАРТОВОЙ ПОЗИЦИЕЙ
----------------------------------------------------------------------------

# Начать с конкретного ID
python manage.py update_ip --start-from-id 1000

# Начать с самых старых записей
python manage.py update_ip --start-from-oldest

# Начать с ID 5000 в режиме only-actual
python manage.py update_ip --only-actual --start-from-id 5000

----------------------------------------------------------------------------
6. ЗАЩИТА ОТ БЛОКИРОВКИ
----------------------------------------------------------------------------

# С автоматическим повтором через час после блокировки
python manage.py update_ip --auto-retry-after-block

# Увеличенная задержка
python manage.py update_ip --delay 3 --random-delay

# С ограничением запросов
python manage.py update_ip --max-requests 500

============================================================================
ЧТО ОБНОВЛЯЕТСЯ ДЛЯ КАЖДОГО ТИПА РИД
============================================================================

┌─────────────────────────────┬──────────────────┬────────────────────────┐
│ Тип РИД                      │ Поле в БД        │ Что парсится           │
├─────────────────────────────┼──────────────────┼────────────────────────┤
│ Изобретение                  │ abstract         │ Реферат (id='Abs')     │
│ (invention)                  │ claims           │ Формула изобретения    │
│                             │ actual           │ Статус (действует/нет) │
├─────────────────────────────┼──────────────────┼────────────────────────┤
│ Полезная модель              │ abstract         │ Реферат (id='Abs')     │
│ (utility-model)              │ claims           │ Формула                │
│                             │ actual           │ Статус                 │
├─────────────────────────────┼──────────────────┼────────────────────────┤
│ Промышленный образец         │ actual           │ Статус                 │
│ (industrial-design)          │                  │                        │
├─────────────────────────────┼──────────────────┼────────────────────────┤
│ Топология ИМС                 │ abstract         │ Реферат (id='Abs')     │
│ (integrated-circuit-topology)│                  │                        │
├─────────────────────────────┼──────────────────┼────────────────────────┤
│ Программа для ЭВМ            │ abstract         │ Реферат (id='Abs')     │
│ (computer-program)           │ programming_     │ Языки программирования │
│                             │ languages        │ (в кавычках)           │
├─────────────────────────────┼──────────────────┼────────────────────────┤
│ База данных                  │ abstract         │ Реферат (id='Abs')     │
│ (database)                   │ dbms             │ СУБД (в кавычках)      │
└─────────────────────────────┴──────────────────┴────────────────────────┘

============================================================================
ПРИМЕРЫ ВЫВОДА
============================================================================

----------------------------------------------------------------------------
ОБЫЧНЫЙ ЗАПУСК (с автоопределением)
----------------------------------------------------------------------------

================================================================================
🚀 ЗАПУСК ОБНОВЛЕНИЯ ДАННЫХ РИД
================================================================================
📌 Порядок обработки: от новых к старым
📌 Защита от блокировки: включена

📋 Обработка всех типов РИД: invention, utility-model, industrial-design...

🎯 Начинаем с ID 15243 (первая запись с пустым abstract)

📊 Найдено записей для обработки: 3847

Обработка записей: 100%|████████████████| 3847/3847 [2:15:32<00:00,  2.1зап/s]

================================================================================
📊 ИТОГОВАЯ СТАТИСТИКА
================================================================================
📁 Всего записей: 3847
📝 Обработано: 3847
✅ Успешно обновлено: 3124
❌ Неудачно: 245
⏭️  Пропущено: 478
📡 Выполнено запросов: 3847
🎯 Стартовая позиция: ID 15243
================================================================================

----------------------------------------------------------------------------
РЕЖИМ FORCE
----------------------------------------------------------------------------

================================================================================
🚀 ЗАПУСК ОБНОВЛЕНИЯ ДАННЫХ РИД
================================================================================
📌 РЕЖИМ: принудительное обновление с начала (--force)
📌 Порядок обработки: от новых к старым

🎯 Режим --force: начинаем с начала, обрабатываем все записи

📊 Найдено записей для обработки: 5496
...

----------------------------------------------------------------------------
ПРИ БЛОКИРОВКЕ
----------------------------------------------------------------------------

================================================================================
🚫 ОБНАРУЖЕНА БЛОКИРОВКА
================================================================================
🔸 URL: https://www1.fips.ru/registers-doc-view/fips_servlet?DB=RUPAT&rn=2765432
🔸 Время: 2026-03-01 15:30:45
🔸 Выполнено запросов до блокировки: 245
🔸 Заблокирован до: 01.04.2026 включительно
🔸 Осталось дней: 31
🔸 ID подключения: 13675712
🔸 Для разблокировки напишите в техподдержку с указанием этого ID
================================================================================

============================================================================
РЕКОМЕНДАЦИИ
============================================================================

1. Для первого запуска используйте обычный режим - он начнет с первого пустого
2. После блокировки используйте --start-from-id с ID последней обработанной
3. Для массового обновления статуса используйте --only-actual
4. Для полного перезаполнения используйте --force
5. Всегда используйте задержки (--delay 1.5-2) для предотвращения блокировки
```


-----

# Файл: management\__init__.py

```

```


-----

# Файл: management\commands\pars_fips_catalogue.py

```
"""
Команда для парсинга каталогов открытых данных ФИПС Роспатента.
Обертка, которая делегирует выполнение соответствующим парсерам.
Поддерживает обработку по годам для уменьшения нагрузки на БД.
"""

import logging
import os
import gc
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import pandas as pd

from intellectual_property.models import FipsOpenDataCatalogue

# Импортируем парсеры из пакета parsers
from ..parsers import (
    InventionParser, UtilityModelParser, IndustrialDesignParser,
    IntegratedCircuitTopologyParser, ComputerProgramParser, DatabaseParser
)
from ..utils.csv_loader import load_csv_with_strategies
from ..utils.filters import apply_filters, filter_by_actual

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Парсинг каталогов открытых данных ФИПС Роспатента'

    def add_arguments(self, parser):
        parser.add_argument('--catalogue-id', type=int, help='ID конкретного каталога для парсинга')
        parser.add_argument('--ip-type', type=str,
                        choices=['invention', 'utility-model', 'industrial-design',
                                'integrated-circuit-topology', 'computer-program', 'database'],
                        help='Тип РИД для парсинга (если не указан, парсятся все)')
        parser.add_argument('--dry-run', action='store_true', help='Режим проверки без сохранения в БД')
        parser.add_argument('--encoding', type=str, default='utf-8', help='Кодировка CSV файла')
        parser.add_argument('--delimiter', type=str, default=',', help='Разделитель в CSV файле')
        parser.add_argument('--batch-size', type=int, default=100, help='Размер пакета для bulk-операций')
        parser.add_argument('--min-year', type=int, default=2000, help='Минимальный год регистрации для фильтрации')
        parser.add_argument('--max-year', type=int, help='Максимальный год регистрации для фильтрации')
        parser.add_argument('--skip-filters', action='store_true', help='Пропустить фильтрацию (обработать все записи)')
        parser.add_argument('--only-active', action='store_true', help='Парсить только активные патенты (actual = True)')
        parser.add_argument('--max-rows', type=int, help='Максимальное количество строк для обработки (для тестирования)')
        parser.add_argument('--force', action='store_true', help='Принудительный парсинг даже если каталог уже обработан')
        parser.add_argument('--mark-processed', action='store_true',
                        help='Пометить каталог как обработанный (даже если были ошибки)')
        parser.add_argument('--process-by-year', action='store_true',
                        help='Обрабатывать данные по годам (уменьшает нагрузку на БД)')
        parser.add_argument('--year-step', type=int, default=1,
                        help='Шаг по годам при обработке (по умолчанию 1)')
        parser.add_argument('--start-year', type=int,
                        help='Начальный год для обработки (если нужно начать не с минимального)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parsers = {
            'invention': InventionParser(self),
            'utility-model': UtilityModelParser(self),
            'industrial-design': IndustrialDesignParser(self),
            'integrated-circuit-topology': IntegratedCircuitTopologyParser(self),
            'computer-program': ComputerProgramParser(self),
            'database': DatabaseParser(self),
        }

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.encoding = options['encoding']
        self.delimiter = options['delimiter']
        self.batch_size = options['batch_size']
        self.min_year = options['min_year']
        self.max_year = options.get('max_year')
        self.skip_filters = options['skip_filters']
        self.only_active = options['only_active']
        self.max_rows = options.get('max_rows')
        self.force = options.get('force', False)
        self.mark_processed = options.get('mark_processed', False)
        self.process_by_year = options.get('process_by_year', False)
        self.year_step = options.get('year_step', 1)
        self.start_year = options.get('start_year')

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД\n"))

        if self.only_active:
            self.stdout.write(self.style.WARNING("📌 Режим: парсинг только активных записей (actual = True)"))

        if self.force:
            self.stdout.write(self.style.WARNING("⚠️  Режим: принудительный парсинг (игнорирование даты обработки)"))

        if self.process_by_year:
            self.stdout.write(self.style.WARNING(
                f"📅 Режим: обработка по годам с {self.min_year} по {self.max_year or 'все'} (шаг {self.year_step})"
            ))

        catalogues = self.get_catalogues(options.get('catalogue_id'), options.get('ip_type'))

        if not catalogues:
            raise CommandError('Не найдены каталоги для парсинга')

        total_stats = {
            'catalogues': len(catalogues),
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        for catalogue in catalogues:
            self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
            self.stdout.write(self.style.SUCCESS(f"📁 Обработка каталога: {catalogue.name}"))
            self.stdout.write(self.style.SUCCESS(f"   ID: {catalogue.id}, Тип: {catalogue.ip_type.name if catalogue.ip_type else 'Неизвестно'}"))
            self.stdout.write(self.style.SUCCESS(f"{'='*60}"))

            stats = self.process_catalogue(catalogue)

            for key in ['processed', 'created', 'updated', 'unchanged', 'skipped', 'errors']:
                total_stats[key] += stats.get(key, 0)
            total_stats['skipped_by_date'] += stats.get('skipped_by_date', 0)

        self.print_final_stats(total_stats)

    def get_catalogues(self, catalogue_id=None, ip_type_slug=None):
        queryset = FipsOpenDataCatalogue.objects.all()

        if catalogue_id:
            queryset = queryset.filter(id=catalogue_id)
        elif ip_type_slug:
            queryset = queryset.filter(ip_type__slug=ip_type_slug)
        else:
            queryset = queryset.exclude(catalogue_file='')

        return queryset.order_by('ip_type__id', '-publication_date')

    def extract_year_from_date(self, date_str):
        """Извлечение года из строки с датой"""
        try:
            if pd.isna(date_str) or not date_str:
                return None
            date_str = str(date_str).strip()
            if not date_str:
                return None
            
            for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str, fmt).year
                except (ValueError, TypeError):
                    continue
            
            try:
                return pd.to_datetime(date_str).year
            except (ValueError, TypeError):
                return None
        except:
            return None

    def get_years_from_catalogue(self, catalogue):
        """
        Определяет список годов, присутствующих в CSV файле каталога
        """
        df = self.load_csv(catalogue)
        if df is None or df.empty:
            return []
        
        if 'registration date' not in df.columns:
            self.stdout.write(self.style.WARNING(
                f"  ⚠️ Колонка 'registration date' не найдена, не могу определить годы"
            ))
            return []
        
        df['_year'] = df['registration date'].apply(self.extract_year_from_date)
        all_years = sorted(df['_year'].dropna().unique().astype(int).tolist())
        
        if not all_years:
            self.stdout.write(self.style.WARNING("  ⚠️ Не удалось извлечь годы из дат"))
            return []
        
        # Подробный отладочный вывод
        self.stdout.write(f"  📊 Все годы в каталоге: {all_years[0]} - {all_years[-1]} (всего {len(all_years)} лет)")
        
        if len(all_years) > 20:
            self.stdout.write(f"     Первые 10 лет: {all_years[:10]}")
            self.stdout.write(f"     Последние 10 лет: {all_years[-10:]}")
        else:
            self.stdout.write(f"     Все годы: {all_years}")
        
        # ЕСЛИ УКАЗАН --skip-filters - ВОЗВРАЩАЕМ ВСЕ ГОДЫ БЕЗ ФИЛЬТРАЦИИ!
        if self.skip_filters:
            self.stdout.write(f"  🔍 Фильтрация отключена (--skip-filters), обрабатываются все годы")
            return all_years
        
        # Применяем фильтр по минимальному году (ТОЛЬКО если не skip_filters)
        years = all_years
        if self.min_year is not None:
            years = [y for y in all_years if y >= self.min_year]
            self.stdout.write(f"  🔍 После фильтрации по min_year={self.min_year}: {years[0] if years else 'нет'} - {years[-1] if years else 'нет'} (всего {len(years)} лет)")
        
        # Применяем фильтр по максимальному году
        if self.max_year is not None:
            years = [y for y in years if y <= self.max_year]
            self.stdout.write(f"  🔍 После фильтрации по max_year={self.max_year}: {years[0] if years else 'нет'} - {years[-1] if years else 'нет'} (всего {len(years)} лет)")
        
        # Применяем начальный год, если указан
        if self.start_year and self.start_year in years:
            start_idx = years.index(self.start_year)
            years = years[start_idx:]
            self.stdout.write(f"  🔍 Начинаем с {self.start_year}: {years[0]} - {years[-1]} (всего {len(years)} лет)")
        
        return years

    def process_catalogue(self, catalogue):
        """
        Обработка каталога с поддержкой разбивки по годам
        """
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        if not catalogue.catalogue_file:
            self.stdout.write(self.style.ERROR(f"  ❌ У каталога ID={catalogue.id} не загружен файл"))
            stats['errors'] += 1
            return stats

        if not self.force and hasattr(catalogue, 'parsed_date') and catalogue.parsed_date:
            self.stdout.write(self.style.WARNING(
                f"  ⚠️ Каталог уже был обработан {catalogue.parsed_date.strftime('%d.%m.%Y %H:%M')}"
            ))
            self.stdout.write(self.style.WARNING(f"     Используйте --force для повторного парсинга"))
            stats['skipped'] += 1
            return stats

        ip_type_slug = catalogue.ip_type.slug if catalogue.ip_type else None

        if ip_type_slug not in self.parsers:
            self.stdout.write(self.style.ERROR(f"  ❌ Нет парсера для типа РИД: {ip_type_slug}"))
            stats['errors'] += 1
            return stats

        parser = self.parsers[ip_type_slug]
        
        # Определяем режим обработки
        if not self.process_by_year or self.skip_filters or self.min_year is None:
            # Обычный режим - обрабатываем все сразу
            stats = self._process_catalogue_normal(catalogue, parser, stats)
        else:
            # Режим обработки по годам
            stats = self._process_catalogue_by_year(catalogue, parser, stats)
        
        # Помечаем каталог как обработанный
        if not self.dry_run and hasattr(catalogue, 'parsed_date'):
            if stats['errors'] == 0 or self.mark_processed:
                catalogue.parsed_date = timezone.now()
                catalogue.save(update_fields=['parsed_date'])
                self.stdout.write(self.style.SUCCESS(f"  ✅ Каталог помечен как обработанный"))
            else:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠️ Каталог не помечен как обработанный из-за ошибок"
                ))

        return stats

    def _process_catalogue_normal(self, catalogue, parser, stats):
        """Обычная обработка каталога без разбивки по годам"""
        df = self.load_csv(catalogue)
        if df is None or df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Файл пуст или не удалось загрузить"))
            stats['skipped'] += 1
            return stats
        
        self.stdout.write(f"  📊 Загружено записей: {len(df)}")

        missing_columns = self.check_required_columns(df, parser.get_required_columns())
        if missing_columns:
            self.stdout.write(self.style.ERROR(f"  ❌ Отсутствуют обязательные колонки: {missing_columns}"))
            stats['errors'] += 1
            return stats
        
        if not self.skip_filters:
            df = apply_filters(df, self.min_year, self.only_active, self.stdout, self.max_year)
        
        if df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Нет данных после фильтрации"))
            stats['skipped'] += 1
            return stats
        
        self.stdout.write(f"  📊 После фильтрации: {len(df)} записей")
        
        if self.max_rows and len(df) > self.max_rows:
            df = df.head(self.max_rows)
            self.stdout.write(self.style.WARNING(f"  ⚠️ Ограничено до {self.max_rows} записей"))
        
        try:
            parser_stats = parser.parse_dataframe(df, catalogue)
            stats.update(parser_stats)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка при парсинге: {e}"))
            logger.error(f"Error parsing catalogue {catalogue.id}: {e}", exc_info=True)
            stats['errors'] += 1
        
        return stats

    def _process_catalogue_by_year(self, catalogue, parser, stats):
        """Обработка каталога с разбивкой по годам"""
        # Получаем список годов - теперь с учетом skip_filters!
        years = self.get_years_from_catalogue(catalogue)
        
        if not years:
            self.stdout.write(self.style.WARNING(
                f"  ⚠️ Не удалось определить годы в каталоге, обрабатываем целиком"
            ))
            return self._process_catalogue_normal(catalogue, parser, stats)
        
        self.stdout.write(self.style.SUCCESS(
            f"\n  📅 Будет обработано {len(years)} лет: {years[0]} - {years[-1]}"
        ))
        
        # Загружаем полный DataFrame один раз
        full_df = self.load_csv(catalogue)
        if full_df is None or full_df.empty:
            stats['skipped'] += 1
            return stats
        
        missing_columns = self.check_required_columns(full_df, parser.get_required_columns())
        if missing_columns:
            self.stdout.write(self.style.ERROR(f"  ❌ Отсутствуют обязательные колонки: {missing_columns}"))
            stats['errors'] += 1
            return stats
        
        # Добавляем колонку с годом
        full_df['_year'] = full_df['registration date'].apply(self.extract_year_from_date)
        
        # Обрабатываем годы с заданным шагом
        years_to_process = years[::self.year_step]
        
        for year_idx, year in enumerate(years_to_process, 1):
            self.stdout.write(self.style.SUCCESS(
                f"\n  📅 Год {year} ({year_idx}/{len(years_to_process)})"
            ))
            
            # Фильтруем DataFrame для текущего года
            year_df = full_df[full_df['_year'] == year].copy()
            
            # Применяем фильтр по активности (actual) если нужно
            if self.only_active and not self.skip_filters:
                year_df = filter_by_actual(year_df, self.stdout)
            
            if year_df.empty:
                self.stdout.write(self.style.WARNING(f"     ⚠️ Нет данных для года {year} после фильтрации"))
                continue
            
            if self.max_rows:
                year_df = year_df.head(min(self.max_rows, len(year_df)))
            
            try:
                year_stats = parser.parse_dataframe(year_df, catalogue, year=year)
                
                # Обновляем общую статистику
                stats['processed'] += year_stats.get('processed', 0)
                stats['created'] += year_stats.get('created', 0)
                stats['updated'] += year_stats.get('updated', 0)
                stats['unchanged'] += year_stats.get('unchanged', 0)
                stats['errors'] += year_stats.get('errors', 0)
                
                self.stdout.write(f"     Результаты года {year}: "
                                f"создано={year_stats.get('created', 0)}, "
                                f"обновлено={year_stats.get('updated', 0)}, "
                                f"без изменений={year_stats.get('unchanged', 0)}")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Ошибка при парсинге года {year}: {e}"))
                logger.error(f"Error parsing year {year} for catalogue {catalogue.id}: {e}", exc_info=True)
                stats['errors'] += 1
            
            # Принудительная сборка мусора после каждого года
            gc.collect()
        
        # Удаляем временную колонку
        if '_year' in full_df.columns:
            del full_df['_year']
        
        return stats

    def load_csv(self, catalogue):
        file_path = catalogue.catalogue_file.path

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"  ❌ Файл не найден: {file_path}"))
            return None

        df = load_csv_with_strategies(file_path, self.encoding, self.delimiter, self.stdout)
        return df

    def check_required_columns(self, df, required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        return missing

    def print_final_stats(self, stats):
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("📊 ИТОГОВАЯ СТАТИСТИКА"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
        self.stdout.write(f"📁 Обработано каталогов: {stats['catalogues']}")
        self.stdout.write(f"📝 Всего записей обработано: {stats['processed']}")
        self.stdout.write(f"✅ Создано: {stats['created']}")
        self.stdout.write(f"🔄 Обновлено: {stats['updated']}")
        self.stdout.write(f"⏸️  Без изменений: {stats.get('unchanged', 0)}")
        self.stdout.write(f"⏭️  Пропущено всего: {stats['skipped']}")
        self.stdout.write(f"   └─ по дате обновления: {stats.get('skipped_by_date', 0)}")

        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Ошибок: {stats['errors']}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Ошибок: {stats['errors']}"))

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены в БД"))

        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
```


-----

# Файл: management\commands\update_ip.py

```
"""
Команда для обновления данных РИД путем парсинга страниц ФИПС по publication_url.
Поддерживает все типы РИД с соответствующими полями для каждого типа.

Логика работы:
- --force: начинает с начала (обрабатывает все записи подряд)
- --only-actual: обновляет только поле actual по всем записям
- обычный запуск: находит первую запись с пустым abstract и начинает с неё

Мимикрия под реального пользователя:
- Ротация User-Agent (пул современных браузеров)
- Разнообразные Accept-Language заголовки
- Эмуляция полной браузерной сессии
- Умные задержки с длинными паузами
- Случайные вариации в заголовках
"""

import logging
import re
import time
import random
import sys
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models
from django.db.models import Q, F
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType, ProgrammingLanguage, DBMS
from django.conf import settings

logger = logging.getLogger(__name__)


class BlockDetectedException(Exception):
    """Исключение, возникающее при обнаружении блокировки"""
    pass


class Command(BaseCommand):
    help = 'Обновление данных РИД парсингом страниц ФИПС по publication_url'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ip-type',
            type=str,
            choices=[
                'invention', 'utility-model', 'industrial-design',
                'integrated-circuit-topology', 'computer-program', 'database', 'all'
            ],
            default='all',
            help='Тип РИД для обработки (по умолчанию all - все типы)'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Размер пакета для обработки (по умолчанию 100)'
        )
        
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Базовая задержка между запросами в секундах (по умолчанию 2.0)'
        )
        
        parser.add_argument(
            '--random-delay',
            action='store_true',
            default=True,
            help='Использовать случайную задержку (включено по умолчанию)'
        )
        
        parser.add_argument(
            '--max-requests',
            type=int,
            default=None,
            help='Максимальное количество запросов (для тестирования)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Режим проверки без сохранения в БД'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительное обновление с начала (обрабатывает все записи подряд, даже если поля заполнены)'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Таймаут запроса в секундах (по умолчанию 30)'
        )
        
        parser.add_argument(
            '--only-actual',
            action='store_true',
            help='Обновлять только поле actual (статус) по всем записям'
        )
        
        parser.add_argument(
            '--start-from-latest',
            action='store_true',
            default=True,
            help='Начинать с последних по дате регистрации (по умолчанию True)'
        )
        
        parser.add_argument(
            '--start-from-oldest',
            action='store_true',
            help='Начинать с самых старых записей (переопределяет --start-from-latest)'
        )
        
        parser.add_argument(
            '--block-retry-delay',
            type=int,
            default=3600,
            help='Задержка перед повторной попыткой после блокировки в секундах (по умолчанию 3600 - 1 час)'
        )
        
        parser.add_argument(
            '--auto-retry-after-block',
            action='store_true',
            help='Автоматически повторять попытку после блокировки через указанную задержку'
        )
        
        parser.add_argument(
            '--start-from-id',
            type=int,
            help='Начать обработку с конкретного ID (переопределяет автоматическое определение)'
        )
        
        parser.add_argument(
            '--human-mode',
            action='store_true',
            default=True,
            help='Максимальная мимикрия под человека (включено по умолчанию)'
        )
        
        parser.add_argument(
            '--no-human-mode',
            action='store_false',
            dest='human_mode',
            help='Отключить мимикрию под человека (для тестирования)'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Соответствие типов РИД и их слагов
        self.type_slugs = {
            'invention': 'invention',
            'utility-model': 'utility-model',
            'industrial-design': 'industrial-design',
            'integrated-circuit-topology': 'integrated-circuit-topology',
            'computer-program': 'computer-program',
            'database': 'database',
        }
        
        # Карта полей для каждого типа РИД
        self.type_fields_map = {
            'invention': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract', 'is_main': True},
                'claims': {'source': 'parse_claims', 'target': 'claims', 'is_main': True},
                'actual': {'source': 'parse_status', 'target': 'actual'},
            },
            'utility-model': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract', 'is_main': True},
                'claims': {'source': 'parse_claims', 'target': 'claims', 'is_main': True},
                'actual': {'source': 'parse_status', 'target': 'actual'},
            },
            'industrial-design': {
                'actual': {'source': 'parse_status', 'target': 'actual'},
            },
            'integrated-circuit-topology': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract', 'is_main': True},
            },
            'computer-program': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract', 'is_main': True},
                'programming_languages': {'source': 'parse_programming_languages', 'target': 'programming_languages', 'is_m2m': True},
            },
            'database': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract', 'is_main': True},
                'dbms': {'source': 'parse_dbms', 'target': 'dbms', 'is_m2m': True},
            },
        }
        
        # Паттерны для обнаружения блокировки
        self.block_patterns = [
            re.compile(r'Вы заблокированы до\s+(\d{2}\.\d{2}\.\d{4})\s+включительно', re.IGNORECASE),
            re.compile(r'идентификатор(?:ом)? подключения:?\s*(\d+)', re.IGNORECASE),
            re.compile(r'доступ\s+заблокирован', re.IGNORECASE),
            re.compile(r'вы\s+заблокированы', re.IGNORECASE),
            re.compile(r'your\s+access\s+is\s+blocked', re.IGNORECASE),
            re.compile(r'too\s+many\s+requests', re.IGNORECASE),
            re.compile(r'429', re.IGNORECASE),
        ]
        
        # Статистика
        self.stats = {
            'total': 0,
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'actual_updated': 0,
            'blocked': 0,
            'by_type': {},
        }
        
        self.session = None
        self.request_count = 0
        self.block_detected = False
        self.block_info = {}
        self.start_id = None  # ID, с которого начинаем обработку
        
        # ========== НАСТРОЙКИ МИМИКРИИ ==========
        
        # Пул современных User-Agent'ов
        self.user_agents = [
            # Windows + Chrome
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            
            # Windows + Firefox
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            
            # Windows + Edge
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            
            # macOS + Safari
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            
            # Linux + Chrome
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            
            # Мобильные (иногда полезно)
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/121.0 Firefox/121.0',
        ]
        
        # Варианты Accept-Language
        self.accept_languages = [
            'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'ru,en-US;q=0.9,en;q=0.8,uk;q=0.7',
            'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
            'en-US,en;q=0.9,ru;q=0.8',
            'ru,en;q=0.9,uk;q=0.8',
            'ru-RU,ru;q=0.9,en;q=0.5',
            'ru,en;q=0.8',
        ]
        
        # Варианты Accept (иногда браузеры их меняют)
        self.accept_variants = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        ]
        
        # Заголовки Sec-Fetch (браузерные)
        self.sec_fetch_dest = ['document', 'empty', 'iframe']
        self.sec_fetch_mode = ['navigate', 'cors', 'same-origin']

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        self.batch_size = options['batch_size']
        self.delay = options['delay']
        self.random_delay = options['random_delay']
        self.max_requests = options['max_requests']
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.timeout = options['timeout']
        self.only_actual = options['only_actual']
        self.block_retry_delay = options['block_retry_delay']
        self.auto_retry_after_block = options['auto_retry_after_block']
        self.start_from_id = options['start_from_id']
        self.human_mode = options['human_mode']
        
        # Определяем порядок сортировки
        if options['start_from_oldest']:
            self.order_by = 'registration_date'
            self.order_desc = False
            order_text = "от старых к новым"
        else:
            # По умолчанию от новых к старым
            self.order_by = 'registration_date'
            self.order_desc = True
            order_text = "от новых к старым"
        
        ip_type_param = options['ip_type']
        
        self.print_header(order_text)
        
        # Инициализируем сессию с мимикрией
        self.init_session()
        
        # Получаем список типов для обработки
        type_slugs_to_process = self.get_type_slugs(ip_type_param)
        
        # Инициализируем статистику по типам
        for slug in type_slugs_to_process:
            self.stats['by_type'][slug] = {'total': 0, 'success': 0, 'failed': 0, 'actual_updated': 0, 'blocked': 0}
        
        # Основной цикл обработки с поддержкой повторных попыток после блокировки
        try:
            self.run_with_block_handling(type_slugs_to_process)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n\n⏹️ Обработка прервана пользователем"))
            self.print_final_stats()
            sys.exit(1)
        except BlockDetectedException as e:
            self.handle_block_detected(str(e))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n💥 Критическая ошибка: {e}"))
            logger.error(f"Critical error: {e}", exc_info=True)
            self.print_final_stats()
            sys.exit(1)

    def print_header(self, order_text):
        """Вывод заголовка"""
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("🚀 ЗАПУСК ОБНОВЛЕНИЯ ДАННЫХ РИД"))
        self.stdout.write(self.style.SUCCESS("="*80))
        
        if self.only_actual:
            self.stdout.write(self.style.WARNING("\n📌 РЕЖИМ: обновление только поля actual (статус)"))
        
        if self.force:
            self.stdout.write(self.style.WARNING("\n📌 РЕЖИМ: принудительное обновление с начала (--force)"))
        
        self.stdout.write(f"\n📌 Порядок обработки: {order_text}")
        
        if self.human_mode:
            self.stdout.write(f"📌 Мимикрия под человека: ВКЛЮЧЕНА")
            self.stdout.write(f"   • Ротация User-Agent: {len(self.user_agents)} вариантов")
            self.stdout.write(f"   • Умные задержки с длинными паузами")
            self.stdout.write(f"   • Эмуляция браузерной сессии")
        else:
            self.stdout.write(f"📌 Мимикрия под человека: ОТКЛЮЧЕНА")
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД\n"))

    def get_type_slugs(self, ip_type_param):
        """Получение списка слагов типов для обработки"""
        if ip_type_param == 'all':
            type_slugs = list(self.type_slugs.values())
            self.stdout.write(f"📋 Обработка всех типов РИД: {', '.join(type_slugs)}")
            return type_slugs
        else:
            type_slugs = [self.type_slugs[ip_type_param]]
            self.stdout.write(f"📋 Обработка типа РИД: {ip_type_param}")
            return type_slugs

    def run_with_block_handling(self, type_slugs_to_process):
        """Запуск обработки с обработкой блокировок"""
        attempt = 1
        max_attempts = 3 if self.auto_retry_after_block else 1
        
        while attempt <= max_attempts:
            if attempt > 1:
                self.stdout.write(self.style.WARNING(
                    f"\n🔄 Попытка {attempt} после блокировки (через {self.block_retry_delay} сек)"
                ))
                time.sleep(self.block_retry_delay)
            
            try:
                # Получаем queryset для обработки
                queryset = self.get_queryset(type_slugs_to_process)
                self.stats['total'] = queryset.count()
                
                self.stdout.write(f"\n📊 Найдено записей для обработки: {self.stats['total']}")
                
                if self.stats['total'] == 0:
                    self.stdout.write(self.style.WARNING("⚠️ Нет записей для обработки"))
                    return
                
                # Обрабатываем по батчам
                self.process_in_batches(queryset)
                
                # Если дошли сюда без исключения - успешно завершили
                break
                
            except BlockDetectedException as e:
                self.stats['blocked'] += 1
                self.block_detected = True
                
                if attempt < max_attempts:
                    attempt += 1
                    continue
                else:
                    raise

    def init_session(self):
        """Инициализация HTTP-сессии с мимикрией под реальный браузер"""
        self.session = requests.Session()
        
        if not self.human_mode:
            # Режим без мимикрии - минимальные заголовки
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })
            return
        
        # ===== РЕЖИМ ПОЛНОЙ МИМИКРИИ =====
        
        # Устанавливаем начальные заголовки (базовые)
        self.session.headers.update({
            'Accept': random.choice(self.accept_variants),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })
        
        # Устанавливаем случайный User-Agent и Accept-Language
        self.rotate_headers()
        
        # Эмулируем загрузку главной страницы для получения cookies
        self.emulate_browser_session()

    def rotate_headers(self):
        """Ротация заголовков для каждого запроса"""
        if not self.human_mode:
            return
        
        # Случайный User-Agent
        user_agent = random.choice(self.user_agents)
        self.session.headers.update({'User-Agent': user_agent})
        
        # Случайный Accept-Language
        accept_language = random.choice(self.accept_languages)
        self.session.headers.update({'Accept-Language': accept_language})
        
        # Случайный Accept (иногда меняется)
        if random.random() < 0.3:  # 30% запросов
            self.session.headers.update({'Accept': random.choice(self.accept_variants)})
        
        # Случайные Sec-Fetch заголовки (браузерные)
        if random.random() < 0.5:
            self.session.headers.update({
                'Sec-Fetch-Dest': random.choice(self.sec_fetch_dest),
                'Sec-Fetch-Mode': random.choice(self.sec_fetch_mode),
                'Sec-Fetch-Site': random.choice(['same-origin', 'same-site', 'cross-site']),
            })
        
        # Иногда добавляем заголовок DNT (Do Not Track)
        if random.random() < 0.2:
            self.session.headers.update({'DNT': '1'})
        else:
            self.session.headers.pop('DNT', None)

    def emulate_browser_session(self):
        """Эмуляция полной сессии браузера - загрузка главной страницы и получение cookies"""
        if not self.human_mode:
            return
        
        try:
            if self.verbosity >= 2:
                self.stdout.write("   🌐 Эмуляция загрузки главной страницы ФИПС...")
            
            # Небольшая пауза перед первой загрузкой (как человек)
            time.sleep(random.uniform(1, 3))
            
            # Загружаем главную страницу
            main_page_response = self.session.get(
                'https://www1.fips.ru/', 
                timeout=self.timeout,
                allow_redirects=True
            )
            
            # Куки сохранятся автоматически в self.session.cookies
            
            # Небольшая пауза после загрузки главной
            time.sleep(random.uniform(2, 4))
            
            # Иногда загружаем ещё пару страниц для большей естественности
            if random.random() < 0.7:  # 70% случаев
                pages = [
                    'https://www1.fips.ru/about/',
                    'https://www1.fips.ru/activities/',
                    'https://www1.fips.ru/information-systems/',
                    'https://www1.fips.ru/news/',
                ]
                # Загружаем 1-3 случайные страницы
                for _ in range(random.randint(1, 3)):
                    page = random.choice(pages)
                    self.session.get(page, timeout=self.timeout)
                    time.sleep(random.uniform(1, 3))
            
            if self.verbosity >= 2:
                self.stdout.write(f"   ✅ Куки получены: {len(self.session.cookies)} шт.")
                
        except Exception as e:
            if self.verbosity >= 2:
                self.stdout.write(f"   ⚠️ Не удалось загрузить главную страницу: {e}")
            # Продолжаем работу без кук, возможно, они и не нужны

    def apply_delay(self):
        """Умная задержка между запросами с имитацией человеческого поведения"""
        if self.delay <= 0 or self.block_detected:
            return
        
        if not self.human_mode:
            # Простая задержка без мимикрии
            time.sleep(self.delay)
            return
        
        # ===== УМНЫЕ ЗАДЕРЖКИ С МИМИКРИЕЙ =====
        
        # Каждые 30-70 запросов делаем длинную паузу (как будто пользователь отошел)
        if self.request_count % random.randint(30, 70) == 0:
            long_delay = random.uniform(45, 180)  # 45 секунд - 3 минуты
            if self.verbosity >= 1:
                self.stdout.write(f"\n   💤 ДЛИННАЯ ПАУЗА {long_delay:.1f} сек... (после {self.request_count} запросов)")
            time.sleep(long_delay)
            return
        
        # Каждые 10-20 запросов делаем среднюю паузу (изучение страницы)
        if self.request_count % random.randint(10, 20) == 0:
            medium_delay = random.uniform(8, 25)  # 8-25 секунд
            if self.verbosity >= 2:
                self.stdout.write(f"\n   ⏱️ ПАУЗА {medium_delay:.1f} сек (изучение)...")
            time.sleep(medium_delay)
            return
        
        # Обычная задержка с вариациями
        base_delay = self.delay * random.uniform(0.7, 2.5)
        
        # Иногда добавляем "микро-паузы" (как будто пользователь читает)
        extra_delay = 0
        if random.random() < 0.3:  # 30% случаев
            extra_delay = random.uniform(1, 5)
            if self.verbosity >= 3:
                self.stdout.write(f"      🤔 Читает... +{extra_delay:.1f} сек")
        
        # Иногда делаем две короткие паузы подряд (имитация задумчивости)
        if random.random() < 0.1:  # 10% случаев
            if self.verbosity >= 2:
                self.stdout.write("      🤔 Пауза-раздумье...")
            time.sleep(random.uniform(2, 6))
        
        total_delay = base_delay + extra_delay
        time.sleep(total_delay)

    def get_queryset(self, type_slugs):
        """Получение queryset для обработки с умным определением стартовой позиции"""
        # Получаем типы по слагам
        ip_types = IPType.objects.filter(slug__in=type_slugs)
        
        # Базовый queryset
        queryset = IPObject.objects.filter(
            ip_type__in=ip_types,
            publication_url__isnull=False
        ).exclude(
            publication_url=''
        ).select_related('ip_type')
        
        # Определяем стартовую позицию
        if self.start_from_id:
            # Явно указанный ID
            self.start_id = self.start_from_id
            self.stdout.write(self.style.WARNING(
                f"🎯 Старт с явно указанного ID: {self.start_id}"
            ))
            queryset = queryset.filter(id__gte=self.start_id)
        
        elif self.force:
            # Режим force - начинаем с начала, обрабатываем все
            self.stdout.write(self.style.WARNING(
                "🎯 Режим --force: начинаем с начала, обрабатываем все записи"
            ))
            # Ничего не фильтруем дополнительно
        
        elif self.only_actual:
            # Режим only-actual - обновляем статус у всех
            self.stdout.write(self.style.WARNING(
                "🎯 Режим --only-actual: обновляем статус у всех записей"
            ))
            # Ничего не фильтруем, берем все
        
        else:
            # Обычный режим - находим первую запись с пустым abstract
            # (с учетом сортировки от новых к старым)
            self.start_id = self.find_first_empty_abstract(queryset, ip_types)
            
            if self.start_id:
                self.stdout.write(self.style.WARNING(
                    f"🎯 Начинаем с ID {self.start_id} (первая запись с пустым abstract в сортировке от новых к старым)"
                ))
                queryset = queryset.filter(id__gte=self.start_id)
            else:
                self.stdout.write(self.style.SUCCESS(
                    "✅ Все записи имеют заполненный abstract! Обновлять нечего."
                ))
                return IPObject.objects.none()  # Пустой queryset
        
        # Применяем сортировку
        if self.order_by:
            order_field = self.order_by
            if self.order_desc:
                order_field = f'-{order_field}'
            
            queryset = queryset.order_by(order_field)
        
        return queryset

    def find_first_empty_abstract(self, queryset, ip_types):
        """
        Находит первую запись с пустым abstract для типов, у которых abstract является основным полем
        Учитывает сортировку от новых к старым
        """
        # Собираем типы, у которых есть поле abstract как основное
        types_with_abstract = []
        for ip_type in ip_types:
            fields_map = self.type_fields_map.get(ip_type.slug, {})
            for field_key, field_info in fields_map.items():
                if field_info.get('is_main', False) and field_info['target'] == 'abstract':
                    types_with_abstract.append(ip_type)
                    break
        
        if not types_with_abstract:
            self.stdout.write(self.style.WARNING(
                "⚠️ Нет типов РИД, у которых abstract является основным полем"
            ))
            return None
        
        # Определяем порядок сортировки
        order_by = '-registration_date' if self.order_desc else 'registration_date'
        
        # Ищем первую запись с пустым abstract в отсортированном списке
        empty_abstract_qs = IPObject.objects.filter(
            ip_type__in=types_with_abstract,
            publication_url__isnull=False
        ).exclude(
            publication_url=''
        ).filter(
            Q(abstract__isnull=True) | Q(abstract='')
        ).order_by(order_by, 'id')  # Сортируем по дате и ID
        
        first_empty = empty_abstract_qs.first()
        
        if first_empty:
            return first_empty.id
        
        return None

    def process_in_batches(self, queryset):
        """Обработка записей по батчам"""
        total = queryset.count()
        
        # Для тестирования ограничиваем количество запросов
        if self.max_requests and self.max_requests < total:
            self.stdout.write(self.style.WARNING(
                f"\n⏹️ Будет обработано только {self.max_requests} записей из {total} (лимит запросов)"
            ))
            # Получаем первые N записей
            queryset = queryset[:self.max_requests]
            total = self.max_requests
        
        with tqdm(total=total, desc="Обработка записей", unit="зап") as pbar:
            for ip_object in queryset.iterator(chunk_size=self.batch_size):
                # Проверяем лимит запросов
                if self.max_requests and self.request_count >= self.max_requests:
                    self.stdout.write(self.style.WARNING(
                        f"\n⏹️ Достигнут лимит запросов ({self.max_requests})"
                    ))
                    return
                
                # Проверяем, не была ли обнаружена блокировка в предыдущем запросе
                if self.block_detected:
                    self.stdout.write(self.style.ERROR(
                        "\n🚫 Обнаружена блокировка. Остановка обработки."
                    ))
                    return
                
                # Обрабатываем запись
                try:
                    self.process_single_object(ip_object)
                except BlockDetectedException:
                    # Пробрасываем исключение для остановки всего процесса
                    raise
                except Exception as e:
                    # Логируем другие ошибки, но продолжаем
                    self.stats['errors'] += 1
                    if self.verbosity >= 1:
                        self.stdout.write(self.style.ERROR(f"\n❌ Неожиданная ошибка: {e}"))
                    logger.error(f"Unexpected error processing IPObject {ip_object.id}: {e}", exc_info=True)
                
                # Обновляем прогресс
                pbar.update(1)
                pbar.set_postfix({
                    'OK': self.stats['success'],
                    'ACT': self.stats['actual_updated'],
                    'ERR': self.stats['failed'],
                    'BLK': self.stats['blocked'],
                    'REQ': self.request_count
                })
                
                # Задержка между запросами
                self.apply_delay()

    def process_single_object(self, ip_object):
        """Обработка одного объекта РИД"""
        self.stats['processed'] += 1
        type_slug = ip_object.ip_type.slug
        
        self.stats['by_type'][type_slug]['total'] += 1
        
        reg_date = ip_object.registration_date.strftime('%d.%m.%Y') if ip_object.registration_date else 'нет даты'
        
        if self.verbosity >= 2:
            self.stdout.write(f"\n🔍 Обработка ID={ip_object.id}, тип={type_slug}, дата={reg_date}")
            self.stdout.write(f"   URL: {ip_object.publication_url}")
        
        # Проверяем наличие URL
        if not ip_object.publication_url:
            self.stats['skipped'] += 1
            if self.verbosity >= 2:
                self.stdout.write(self.style.WARNING("   ⚠️ Нет publication_url, пропуск"))
            return
        
        # Получаем карту полей для данного типа
        full_fields_map = self.type_fields_map.get(type_slug, {})
        
        # Если режим only_actual, оставляем только поле actual
        if self.only_actual:
            fields_map = {k: v for k, v in full_fields_map.items() if v['target'] == 'actual'}
            if not fields_map:
                # Для типов без поля actual пропускаем
                self.stats['skipped'] += 1
                if self.verbosity >= 2:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Тип {type_slug} не имеет поля actual, пропуск"))
                return
        else:
            fields_map = full_fields_map
        
        if not fields_map:
            self.stats['skipped'] += 1
            if self.verbosity >= 2:
                self.stdout.write(self.style.WARNING(f"   ⚠️ Нет карты полей для типа {type_slug}"))
            return
        
        # В обычном режиме (не force и не only-actual) пропускаем, если abstract уже заполнен
        if not self.force and not self.only_actual:
            # Проверяем, заполнено ли основное поле (abstract)
            if ip_object.abstract and ip_object.abstract.strip():
                if self.verbosity >= 2:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Abstract уже заполнен, пропуск"))
                self.stats['skipped'] += 1
                return
        
        # Ротация заголовков перед запросом
        self.rotate_headers()
        
        # Загружаем страницу
        html_content = self.fetch_page(ip_object.publication_url)
        
        if not html_content:
            self.stats['failed'] += 1
            self.stats['by_type'][type_slug]['failed'] += 1
            return
        
        # Парсим данные
        try:
            parsed_data = self.parse_page(html_content, type_slug, fields_map)
            
            if parsed_data:
                # Обновляем объект
                updated, actual_updated = self.update_object(ip_object, parsed_data, fields_map)
                
                if updated:
                    self.stats['success'] += 1
                    self.stats['by_type'][type_slug]['success'] += 1
                    
                    if actual_updated:
                        self.stats['actual_updated'] += 1
                        self.stats['by_type'][type_slug]['actual_updated'] += 1
                    
                    if self.verbosity >= 2:
                        fields_updated = ', '.join(parsed_data.keys())
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Данные обновлены: {fields_updated}"))
                else:
                    self.stats['skipped'] += 1
                    if self.verbosity >= 2:
                        self.stdout.write("   ℹ️ Нет изменений")
            else:
                self.stats['failed'] += 1
                self.stats['by_type'][type_slug]['failed'] += 1
                
        except Exception as e:
            self.stats['errors'] += 1
            self.stats['failed'] += 1
            self.stats['by_type'][type_slug]['failed'] += 1
            
            if self.verbosity >= 1:
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка парсинга: {e}"))
            
            logger.error(f"Error parsing IPObject {ip_object.id}: {e}", exc_info=True)

    def fetch_page(self, url):
        """Загрузка страницы по URL с детектором блокировки"""
        try:
            self.request_count += 1
            
            # Небольшая случайная задержка перед запросом (как будто пользователь нажимает ссылку)
            if self.human_mode and random.random() < 0.3:
                click_delay = random.uniform(0.3, 1.5)
                time.sleep(click_delay)
            
            response = self.session.get(url, timeout=self.timeout)
            
            # Проверяем HTTP статус на блокировку
            if response.status_code == 429:
                self.detect_block(response.text, url, status_code=429)
            
            response.encoding = 'windows-1251'  # ФИПС использует windows-1251
            
            if response.status_code == 200:
                # Проверяем содержимое на признаки блокировки
                self.check_for_block(response.text, url)
                
                if self.verbosity >= 3:
                    self.stdout.write(f"   📥 Загружено {len(response.text)} символов")
                return response.text
            else:
                if self.verbosity >= 2:
                    self.stdout.write(self.style.ERROR(f"   ❌ HTTP {response.status_code}"))
                return None
                
        except requests.exceptions.Timeout:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(f"   ⏰ Таймаут"))
            return None
        except requests.exceptions.ConnectionError:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(f"   🔌 Ошибка соединения"))
            return None
        except BlockDetectedException:
            # Пробрасываем исключение о блокировке
            raise
        except Exception as e:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка: {e}"))
            return None

    def check_for_block(self, html_content, url):
        """Проверка HTML-содержимого на наличие признаков блокировки"""
        if not html_content:
            return
        
        # Проверяем по всем паттернам
        for pattern in self.block_patterns:
            match = pattern.search(html_content)
            if match:
                self.detect_block(html_content, url, pattern_match=match)
                return

    def detect_block(self, html_content, url, status_code=None, pattern_match=None):
        """
        Обнаружение блокировки и генерация исключения
        """
        block_info = {
            'url': url,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status_code': status_code,
            'request_count': self.request_count,
        }
        
        # Пытаемся извлечь дату блокировки
        date_pattern = re.compile(r'Вы заблокированы до\s+(\d{2}\.\d{2}\.\d{4})\s+включительно', re.IGNORECASE)
        date_match = date_pattern.search(html_content)
        if date_match:
            block_info['block_until'] = date_match.group(1)
        
        # Пытаемся извлечь ID подключения
        id_pattern = re.compile(r'идентификатор(?:ом)? подключения:?\s*(\d+)', re.IGNORECASE)
        id_match = id_pattern.search(html_content)
        if id_match:
            block_info['connection_id'] = id_match.group(1)
        
        self.block_info = block_info
        self.block_detected = True
        self.stats['blocked'] += 1
        
        # Формируем сообщение о блокировке
        message = self.format_block_message(block_info)
        
        # Выводим сообщение
        self.stdout.write(self.style.ERROR(f"\n{'='*80}"))
        self.stdout.write(self.style.ERROR("🚫 ОБНАРУЖЕНА БЛОКИРОВКА"))
        self.stdout.write(self.style.ERROR(f"{'='*80}"))
        self.stdout.write(self.style.ERROR(message))
        self.stdout.write(self.style.ERROR(f"{'='*80}\n"))
        
        # Логируем
        logger.warning(f"Block detected: {block_info}")
        
        # Генерируем исключение
        raise BlockDetectedException(message)

    def format_block_message(self, block_info):
        """Форматирование сообщения о блокировке"""
        lines = []
        lines.append(f"🔸 URL: {block_info['url']}")
        lines.append(f"🔸 Время: {block_info['timestamp']}")
        lines.append(f"🔸 Выполнено запросов до блокировки: {block_info['request_count']}")
        
        if block_info.get('status_code'):
            lines.append(f"🔸 HTTP статус: {block_info['status_code']}")
        
        if block_info.get('block_until'):
            lines.append(f"🔸 Заблокирован до: {block_info['block_until']} включительно")
            
            # Рассчитываем оставшееся время
            try:
                block_date = datetime.strptime(block_info['block_until'], '%d.%m.%Y').date()
                today = date.today()
                days_left = (block_date - today).days
                if days_left > 0:
                    lines.append(f"🔸 Осталось дней: {days_left}")
            except:
                pass
        
        if block_info.get('connection_id'):
            lines.append(f"🔸 ID подключения: {block_info['connection_id']}")
            lines.append(f"🔸 Для разблокировки напишите в техподдержку с указанием этого ID")
        
        return '\n'.join(lines)

    def handle_block_detected(self, message):
        """Обработка обнаруженной блокировки"""
        self.stdout.write(self.style.ERROR("\n" + "="*80))
        self.stdout.write(self.style.ERROR("🚫 РАБОТА ПРЕРВАНА ИЗ-ЗА БЛОКИРОВКИ"))
        self.stdout.write(self.style.ERROR("="*80))
        self.stdout.write(self.style.ERROR(message))
        
        if self.auto_retry_after_block:
            self.stdout.write(self.style.WARNING(
                f"\n🔄 Автоматический повтор через {self.block_retry_delay} сек не удался (превышено количество попыток)"
            ))
        
        self.stdout.write(self.style.WARNING("\n📌 Рекомендации:"))
        self.stdout.write("   1. Увеличьте задержку между запросами (--delay 3-5)")
        self.stdout.write("   2. Используйте случайную задержку (--random-delay включен по умолчанию)")
        self.stdout.write("   3. Уменьшите количество запросов (--max-requests)")
        self.stdout.write("   4. Подождите указанное время до разблокировки")
        
        self.print_final_stats()
        sys.exit(1)

    def parse_page(self, html, type_slug, fields_map):
        """Парсинг страницы в соответствии с типом РИД"""
        soup = BeautifulSoup(html, 'html.parser')
        result = {}
        
        for field_key, field_info in fields_map.items():
            source_method = field_info['source']
            
            if hasattr(self, source_method):
                value = getattr(self, source_method)(soup, type_slug)
                
                if value is not None and value != '':
                    result[field_info['target']] = {
                        'value': value,
                        'is_m2m': field_info.get('is_m2m', False)
                    }
        
        return result if result else None

    def parse_abstract(self, soup, type_slug):
        """Парсинг реферата (общий для всех типов)"""
        abs_div = soup.find('div', id='Abs')
        
        if abs_div:
            abs_text = abs_div.get_text(strip=True)
            if 'Реферат:' in abs_text:
                abs_text = abs_text.split('Реферат:', 1)[-1].strip()
            return abs_text
        
        return None

    def parse_claims(self, soup, type_slug):
        """Парсинг формулы изобретения/полезной модели"""
        # Для изобретений и полезных моделей
        formula_start = soup.find('p', class_='TitCla')
        
        if formula_start:
            formula_text = formula_start.get_text(strip=True)
            
            # Проверяем, что это формула изобретения или полезной модели
            if ('Формула изобретения' in formula_text or 
                'Формула полезной модели' in formula_text):
                
                # Собираем всю формулу
                formula_content = []
                next_elem = formula_start.find_next_sibling()
                
                while next_elem and not (
                    hasattr(next_elem, 'name') and 
                    next_elem.name == 'a' and 
                    'ClEnd' in next_elem.get('href', '')
                ):
                    if hasattr(next_elem, 'get_text'):
                        text = next_elem.get_text(strip=True)
                        if text:
                            formula_content.append(text)
                    next_elem = next_elem.find_next_sibling()
                
                if formula_content:
                    return '\n'.join(formula_content)
        
        return None

    def parse_status(self, soup, type_slug):
        """Парсинг статуса для определения actual"""
        status_rows = soup.find_all('tr')
        
        for row in status_rows:
            status_label = row.find('td', id='StatusL')
            if status_label and 'Статус:' in status_label.get_text():
                status_value = row.find('td', id='StatusR')
                if status_value:
                    status_text = status_value.get_text(strip=True).lower()
                    
                    # Проверяем наличие слова "действует" в любом контексте
                    if re.search(r'действует', status_text):
                        return True
                    else:
                        return False
        
        return None

    def parse_programming_languages(self, soup, type_slug):
        """Парсинг языков программирования для программ ЭВМ"""
        b_tag = soup.find('b', string=re.compile(r'Язык программирования:', re.IGNORECASE))
        
        if b_tag:
            parent = b_tag.parent
            if parent:
                full_text = parent.get_text()
                quoted = re.findall(r'"([^"]*)"', full_text)
                if quoted:
                    languages_str = quoted[0]
                    languages = [lang.strip() for lang in languages_str.split(',')]
                    return languages
        
        return None

    def parse_dbms(self, soup, type_slug):
        """Парсинг СУБД для баз данных"""
        b_tag = soup.find('b', string=re.compile(r'Вид и версия системы управления базой данных:', re.IGNORECASE))
        
        if b_tag:
            parent = b_tag.parent
            if parent:
                full_text = parent.get_text()
                quoted = re.findall(r'"([^"]*)"', full_text)
                if quoted:
                    dbms_str = quoted[0]
                    dbms_list = [db.strip() for db in dbms_str.split(',')]
                    return dbms_list
        
        return None

    def update_object(self, ip_object, parsed_data, fields_map):
        """Обновление объекта РИД"""
        if self.dry_run:
            if self.verbosity >= 2:
                self.stdout.write("   📝 DRY-RUN: данные для обновления:")
                for target_field, field_data in parsed_data.items():
                    new_value = field_data['value']
                    current_value = getattr(ip_object, target_field)
                    
                    if field_data.get('is_m2m', False):
                        current = list(getattr(ip_object, target_field).all())
                        self.stdout.write(f"      {target_field}: {current} -> {new_value}")
                    else:
                        self.stdout.write(f"      {target_field}: '{current_value}' -> '{new_value}'")
            return True, 'actual' in parsed_data
        
        updated = False
        actual_updated = False
        
        with transaction.atomic():
            for target_field, field_data in parsed_data.items():
                value = field_data['value']
                is_m2m = field_data.get('is_m2m', False)
                
                if is_m2m:
                    if target_field == 'programming_languages':
                        updated |= self.update_m2m_field(
                            ip_object, 
                            ProgrammingLanguage, 
                            'programming_languages', 
                            value
                        )
                    elif target_field == 'dbms':
                        updated |= self.update_m2m_field(
                            ip_object, 
                            DBMS, 
                            'dbms', 
                            value
                        )
                else:
                    current_value = getattr(ip_object, target_field)
                    
                    if self.force or current_value != value:
                        setattr(ip_object, target_field, value)
                        updated = True
                        
                        if target_field == 'actual':
                            actual_updated = True
            
            if updated:
                ip_object.save(update_fields=list(parsed_data.keys()))
        
        return updated, actual_updated

    def update_m2m_field(self, ip_object, model_class, field_name, values):
        """Обновление ManyToMany поля"""
        if not values:
            return False
        
        manager = getattr(ip_object, field_name)
        
        objects_to_add = []
        for value in values:
            if isinstance(value, str) and value.strip():
                obj, created = model_class.objects.get_or_create(name=value.strip())
                objects_to_add.append(obj)
        
        if objects_to_add:
            if self.force:
                manager.clear()
                manager.add(*objects_to_add)
                return True
            else:
                existing = set(manager.all())
                new_objects = [obj for obj in objects_to_add if obj not in existing]
                if new_objects:
                    manager.add(*new_objects)
                    return True
        
        return False

    def print_final_stats(self):
        """Вывод итоговой статистики"""
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("📊 ИТОГОВАЯ СТАТИСТИКА"))
        self.stdout.write(self.style.SUCCESS("="*80))
        
        self.stdout.write(f"📁 Всего записей: {self.stats['total']}")
        self.stdout.write(f"📝 Обработано: {self.stats['processed']}")
        self.stdout.write(f"✅ Успешно обновлено: {self.stats['success']}")
        
        if self.stats['actual_updated'] > 0:
            self.stdout.write(f"🔄 Обновлено поле actual: {self.stats['actual_updated']}")
        
        if self.stats['blocked'] > 0:
            self.stdout.write(self.style.ERROR(f"🚫 Обнаружено блокировок: {self.stats['blocked']}"))
        
        self.stdout.write(f"❌ Неудачно: {self.stats['failed']}")
        self.stdout.write(f"⏭️  Пропущено: {self.stats['skipped']}")
        
        if self.stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"💥 Ошибок: {self.stats['errors']}"))
        
        self.stdout.write(f"📡 Выполнено запросов: {self.request_count}")
        
        if self.start_id:
            self.stdout.write(f"🎯 Стартовая позиция: ID {self.start_id}")
        
        # Статистика по типам
        if any(stats['total'] > 0 for stats in self.stats['by_type'].values()):
            self.stdout.write(self.style.SUCCESS("\n📊 ПО ТИПАМ РИД:"))
            for type_slug, stats in self.stats['by_type'].items():
                if stats['total'] > 0:
                    success_rate = (stats['success'] / stats['total']) * 100 if stats['total'] > 0 else 0
                    actual_info = f", actual={stats['actual_updated']}" if stats['actual_updated'] > 0 else ""
                    blocked_info = f", блок={stats['blocked']}" if stats['blocked'] > 0 else ""
                    self.stdout.write(
                        f"   {type_slug}: всего={stats['total']}, "
                        f"✅={stats['success']}, ❌={stats['failed']}{actual_info}{blocked_info}, "
                        f"({success_rate:.1f}%)"
                    )
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены в БД"))
        
        if self.block_detected:
            self.stdout.write(self.style.ERROR("\n🚫 РАБОТА ПРЕРВАНА ИЗ-ЗА БЛОКИРОВКИ"))
            if self.block_info:
                self.stdout.write(self.style.ERROR(self.format_block_message(self.block_info)))
        
        self.stdout.write(self.style.SUCCESS("="*80))
```


-----

# Файл: management\commands\__init__.py

```

```


-----

# Файл: management\parsers\base.py

```
"""
Базовый класс для всех парсеров каталогов ФИПС
Поддерживает параметр year для обработки по годам
"""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import gc

from django.db import models
from django.utils.text import slugify
import pandas as pd
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from core.models import Person, Organization, Country

from .processors import (
    RussianTextProcessor,
    OrganizationNormalizer,
    PersonNameFormatter,
    RIDNameFormatter,
    EntityTypeDetector
)

from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class BaseFIPSParser:
    """Базовый класс для всех парсеров каталогов ФИПС"""

    def __init__(self, command):
        self.command = command
        self.stdout = command.stdout
        self.style = command.style

        # Инициализация процессоров
        self.processor = RussianTextProcessor()
        self.org_normalizer = OrganizationNormalizer()
        self.type_detector = EntityTypeDetector()
        self.person_formatter = PersonNameFormatter()
        self.rid_formatter = RIDNameFormatter()

        # Кэши для оптимизации
        self.country_cache = {}
        self.person_cache = {}
        self.organization_cache = {}
        self.foiv_cache = {}
        self.rf_rep_cache = {}
        self.city_cache = {}
        self.activity_type_cache = {}
        self.ceo_position_cache = {}

    def get_ip_type(self):
        """Должен быть переопределен в дочерних классах"""
        raise NotImplementedError

    def get_required_columns(self):
        """Возвращает список обязательных колонок"""
        raise NotImplementedError

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        raise NotImplementedError

    def clean_string(self, value):
        """Очистка строкового значения"""
        if pd.isna(value) or value is None:
            return ''
        value = str(value).strip()
        if value in ['', 'None', 'null', 'NULL', 'nan']:
            return ''
        return value

    def parse_date(self, value):
        """Парсинг даты из строки"""
        if pd.isna(value) or not value:
            return None

        date_str = str(value).strip()
        if not date_str:
            return None

        for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except (ValueError, TypeError):
                continue

        try:
            return pd.to_datetime(date_str).date()
        except (ValueError, TypeError):
            return None

    def parse_bool(self, value):
        """Парсинг булевого значения"""
        if pd.isna(value) or not value:
            return False
        value = str(value).lower().strip()
        return value in ['1', 'true', 'yes', 'да', 'действует', 't', '1.0', 'активен']

    def get_or_create_country(self, code):
        """Получение страны по коду"""
        if not code or pd.isna(code):
            return None

        code = str(code).upper().strip()
        if len(code) != 2:
            return None

        if code in self.country_cache:
            return self.country_cache[code]

        try:
            country = Country.objects.filter(code=code).first()
            if country:
                self.country_cache[code] = country
                return country

            country = Country.objects.filter(code_alpha3=code).first()
            if country:
                self.country_cache[code] = country
                return country

            return None

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка поиска страны {code}: {e}"))
            return None

    def parse_authors(self, authors_str):
        """
        Парсинг строки с авторами
        Возвращает список словарей с данными авторов
        """
        if pd.isna(authors_str) or not authors_str:
            return []

        authors_str = str(authors_str)
        authors_list = re.split(r'[\n,]\s*', authors_str)

        result = []
        for author in authors_list:
            author = author.strip()
            if not author or author == '""' or author == 'null':
                continue

            author = author.strip('"')
            author = re.sub(r'\s*\([A-Z]{2}\)', '', author)
            author = self.person_formatter.format(author)

            parts = author.split()

            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1] if len(parts) > 1 else ''
                middle_name = parts[2] if len(parts) > 2 else ''

                first_name_clean = first_name.replace('.', '')
                middle_name_clean = middle_name.replace('.', '')

                result.append({
                    'last_name': last_name,
                    'first_name': first_name_clean,
                    'middle_name': middle_name_clean,
                    'full_name': author,
                })
            else:
                result.append({
                    'last_name': author,
                    'first_name': '',
                    'middle_name': '',
                    'full_name': author,
                })

        return result

    def parse_patent_holders(self, holders_str):
        """
        Парсинг строки с патентообладателями
        Возвращает список названий
        """
        if pd.isna(holders_str) or not holders_str:
            return []

        holders_str = str(holders_str)
        holders_list = re.split(r'[\n]\s*', holders_str)

        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None':
                continue

            holder = re.sub(r'\s*\([A-Z]{2}\)', '', holder)
            result.append(holder)

        return result

    def find_or_create_person(self, person_data):
        """Поиск или создание физического лица"""
        cache_key = f"{person_data['last_name']}|{person_data['first_name']}|{person_data['middle_name']}"

        if cache_key in self.person_cache:
            return self.person_cache[cache_key]

        persons = Person.objects.filter(
            last_name=person_data['last_name'],
            first_name=person_data['first_name']
        )

        if person_data['middle_name']:
            persons = persons.filter(middle_name=person_data['middle_name'])

        if persons.exists():
            person = persons.first()
            self.person_cache[cache_key] = person
            return person

        try:
            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
            new_id = max_id + 1

            if 'full_name' in person_data:
                full_name = person_data['full_name']
            else:
                full_name_parts = [person_data['last_name'], person_data['first_name']]
                if person_data['middle_name']:
                    full_name_parts.append(person_data['middle_name'])
                full_name = ' '.join(full_name_parts)
                full_name = self.person_formatter.format(full_name)

            # Генерируем уникальный slug
            base_slug = slugify(f"{person_data['last_name']} {person_data['first_name']} {person_data['middle_name']}".strip())
            if not base_slug:
                base_slug = 'person'

            unique_slug = base_slug
            counter = 1
            while Person.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            person = Person.objects.create(
                ceo_id=new_id,
                ceo=full_name,
                last_name=person_data['last_name'],
                first_name=person_data['first_name'],
                middle_name=person_data['middle_name'],
                slug=unique_slug
            )
            self.person_cache[cache_key] = person
            return person
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Person: {e}"))
            return None

    def find_or_create_person_from_name(self, full_name):
        """Поиск или создание физического лица по полному имени"""
        if pd.isna(full_name) or not full_name:
            return None

        full_name = str(full_name).strip().strip('"')
        full_name = self.person_formatter.format(full_name)

        if full_name in self.person_cache:
            return self.person_cache[full_name]

        parts = full_name.split()

        if len(parts) >= 2:
            last_name = parts[0]
            first_name = parts[1] if len(parts) > 1 else ''
            middle_name = parts[2] if len(parts) > 2 else ''

            first_name_clean = first_name.replace('.', '')
            middle_name_clean = middle_name.replace('.', '')

            person_data = {
                'last_name': last_name,
                'first_name': first_name_clean,
                'middle_name': middle_name_clean,
                'full_name': full_name,
            }
        else:
            person_data = {
                'last_name': full_name,
                'first_name': '',
                'middle_name': '',
                'full_name': full_name,
            }

        return self.find_or_create_person(person_data)

    def find_similar_organization(self, org_name):
        """Усиленный поиск похожей организации"""
        if pd.isna(org_name) or not org_name:
            return None

        org_name = str(org_name).strip().strip('"')

        # Стратегия 1: Прямое совпадение
        direct_match = Organization.objects.filter(
            models.Q(name=org_name) |
            models.Q(full_name=org_name) |
            models.Q(short_name=org_name)
        ).first()
        if direct_match:
            return direct_match

        # Нормализуем название для поиска
        norm_data = self.org_normalizer.normalize_for_search(org_name)
        normalized = norm_data['normalized']
        keywords = norm_data['keywords']

        # Стратегия 2: Поиск по ключевым словам
        for keyword in keywords:
            if len(keyword) >= 3:
                similar = Organization.objects.filter(
                    models.Q(name__icontains=keyword) |
                    models.Q(full_name__icontains=keyword) |
                    models.Q(short_name__icontains=keyword)
                ).first()
                if similar:
                    return similar

        # Стратегия 3: Поиск по первым 30 символам
        if len(normalized) > 30:
            prefix = normalized[:30]
            similar = Organization.objects.filter(
                models.Q(name__icontains=prefix) |
                models.Q(full_name__icontains=prefix) |
                models.Q(short_name__icontains=prefix)
            ).first()
            if similar:
                return similar

        # Стратегия 4: Поиск по отдельным словам
        words = org_name.split()
        for word in words:
            if len(word) > 4:
                similar = Organization.objects.filter(
                    models.Q(name__icontains=word) |
                    models.Q(full_name__icontains=word)
                ).first()
                if similar:
                    return similar

        return None

    def find_or_create_organization(self, org_name):
        """Поиск или создание организации с сохранением оригинального названия"""
        if pd.isna(org_name) or not org_name:
            return None

        org_name = str(org_name).strip().strip('"')

        if not org_name or org_name == 'null' or org_name == 'None':
            return None

        # Проверяем кэш
        if org_name in self.organization_cache:
            return self.organization_cache[org_name]

        # Ищем похожие
        similar = self.find_similar_organization(org_name)
        if similar:
            self.organization_cache[org_name] = similar
            return similar

        # Не нашли - создаем новую с оригинальным названием
        try:
            max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
            new_id = max_id + 1

            # Генерируем slug из оригинального названия
            base_slug = slugify(org_name[:50])
            if not base_slug:
                base_slug = 'organization'

            unique_slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            # Сохраняем оригинальное название без изменений
            org = Organization.objects.create(
                organization_id=new_id,
                name=org_name,
                full_name=org_name,
                short_name=org_name[:500] if len(org_name) > 500 else org_name,
                slug=unique_slug,
                register_opk=False,
                strategic=False,
            )

            self.organization_cache[org_name] = org
            return org
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Organization: {e}"))
            return None

    # =========================================================================
    # МЕТОДЫ ДЛЯ МАССОВОГО СОЗДАНИЯ ЛЮДЕЙ
    # =========================================================================

    def _create_persons_bulk(self, persons_df: pd.DataFrame) -> Dict[str, Person]:
        """
        Пакетное создание людей из DataFrame с индикацией прогресса
        
        Args:
            persons_df: DataFrame с колонкой 'entity_name'
            
        Returns:
            Словарь {имя: объект Person}
        """
        person_map = {}
        
        if persons_df.empty:
            self.stdout.write("      Нет людей для обработки")
            return person_map
        
        all_names = persons_df['entity_name'].tolist()
        total_names = len(all_names)
        
        self.stdout.write(f"      Всего уникальных людей для обработки: {total_names}")
        
        # ШАГ 1: Поиск существующих людей
        self.stdout.write(f"      Поиск существующих людей в БД...")
        
        name_to_parts = self._extract_name_parts(all_names)
        existing_persons = self._find_existing_persons(name_to_parts)
        
        # ШАГ 2: Определяем новых людей
        valid_names = list(name_to_parts.keys())
        new_names = [name for name in valid_names if name not in existing_persons]
        new_count = len(new_names)
        
        self.stdout.write(f"      Новых людей для создания: {new_count}")
        
        # ШАГ 3: Создаем новых людей
        if new_names:
            new_persons_map = self._create_new_persons(new_names)
            person_map.update(new_persons_map)
        
        # ШАГ 4: Добавляем существующих людей в маппинг
        person_map.update(existing_persons)
        
        self.stdout.write(f"      ✅ Обработано людей: {len(person_map)}")
        
        return person_map

    def _extract_name_parts(self, names: List[str]) -> Dict[str, Tuple[str, str, str]]:
        """
        Извлечение частей ФИО из списка имен
        
        Returns:
            Словарь {полное_имя: (фамилия, имя, отчество)}
        """
        name_to_parts = {}
        for name in names:
            if pd.isna(name) or not name:
                continue
            name = str(name).strip()
            if not name:
                continue
            
            parts = name.split()
            if len(parts) >= 2:
                last = parts[0]
                first = parts[1]
                middle = parts[2] if len(parts) > 2 else ''
                name_to_parts[name] = (last, first, middle)
        
        return name_to_parts

    def _find_existing_persons(self, name_to_parts: Dict[str, Tuple[str, str, str]]) -> Dict[str, Person]:
        """
        Поиск существующих людей в БД
        
        Returns:
            Словарь {имя: объект Person}
        """
        existing_persons = {}
        found_count = 0
        batch_size = 100
        all_names_list = list(name_to_parts.keys())
        
        for i in range(0, len(all_names_list), batch_size):
            batch_names = all_names_list[i:i+batch_size]
            
            # Строим условия поиска
            name_conditions = models.Q()
            batch_name_to_parts = {}
            
            for name in batch_names:
                last, first, middle = name_to_parts[name]
                batch_name_to_parts[name] = (last, first, middle)
                
                if middle:
                    name_conditions |= models.Q(
                        last_name=last, 
                        first_name=first, 
                        middle_name=middle
                    )
                else:
                    name_conditions |= models.Q(
                        last_name=last, 
                        first_name=first
                    ) & (models.Q(middle_name='') | models.Q(middle_name__isnull=True))
            
            # Ищем людей
            for person in Person.objects.filter(name_conditions).only(
                'ceo_id', 'last_name', 'first_name', 'middle_name', 'ceo', 'slug'
            ):
                for name, (last, first, middle) in batch_name_to_parts.items():
                    if (person.last_name == last and 
                        person.first_name == first and 
                        (not middle or person.middle_name == middle)):
                        existing_persons[name] = person
                        self.person_cache[name] = person
                        found_count += 1
                        break
            
            if (i + len(batch_names)) % 500 == 0 or (i + len(batch_names)) >= len(all_names_list):
                self.stdout.write(f"         Обработано {i + len(batch_names)}/{len(all_names_list)} имен")
        
        self.stdout.write(f"      Найдено существующих: {found_count}")
        return existing_persons

    def _create_new_persons(self, new_names: List[str]) -> Dict[str, Person]:
        """
        Создание новых людей
        
        Returns:
            Словарь {имя: объект Person}
        """
        self.stdout.write(f"      Подготовка данных для создания...")
        
        # Получаем все существующие slugs
        existing_slugs = set(Person.objects.values_list('slug', flat=True))
        self.stdout.write(f"         Существующих slug-ов в БД: {len(existing_slugs)}")
        
        people_to_create = []
        
        for name in new_names:
            if pd.isna(name) or not name:
                continue
            
            name = str(name).strip()
            parts = name.split()
            
            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1]
                middle_name = parts[2] if len(parts) > 2 else ''
                
                # Формируем базовый slug
                name_parts_list = [last_name, first_name]
                if middle_name:
                    name_parts_list.append(middle_name)
                
                base_slug = slugify(' '.join(name_parts_list))
                if not base_slug:
                    base_slug = 'person'
                
                # Генерируем уникальный slug
                unique_slug, existing_slugs = self._generate_unique_slug(base_slug, existing_slugs)
                
                # Создаем объект без ID (ID будет назначен при bulk_create)
                person = Person(
                    ceo=name,
                    last_name=last_name,
                    first_name=first_name,
                    middle_name=middle_name or '',
                    slug=unique_slug
                )
                people_to_create.append(person)
        
        # Создаем людей
        return self._bulk_create_persons(people_to_create, len(new_names))

    def _generate_unique_slug(self, base_slug: str, existing_slugs: set) -> Tuple[str, set]:
        """
        Генерация уникального slug
        
        Returns:
            Tuple[уникальный_slug, обновленное_множество_slugs]
        """
        unique_slug = base_slug
        counter = 1
        while unique_slug in existing_slugs:
            unique_slug = f"{base_slug}-{counter}"
            counter += 1
        
        existing_slugs.add(unique_slug)
        return unique_slug, existing_slugs

    def _bulk_create_persons(self, people_to_create: List[Person], total_count: int) -> Dict[str, Person]:
        """
        Массовое создание людей с обработкой ошибок
        
        Returns:
            Словарь {имя: объект Person}
        """
        if not people_to_create:
            return {}
        
        self.stdout.write(f"      Создание людей пачками по 500...")
        
        BATCH_SIZE = 500
        created_count = 0
        created_map = {}
        
        for i in range(0, len(people_to_create), BATCH_SIZE):
            batch = people_to_create[i:i+BATCH_SIZE]
            
            # Получаем актуальный max_id перед каждой пачкой
            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
            next_id = max_id + 1
            
            # Назначаем ID для текущей пачки
            for j, person in enumerate(batch):
                person.ceo_id = next_id + j
            
            # Фильтруем дубликаты в пачке
            batch = self._filter_duplicate_persons(batch)
            if not batch:
                continue
            
            # Пробуем создать пачкой
            try:
                Person.objects.bulk_create(batch, batch_size=BATCH_SIZE, ignore_conflicts=True)
                created_count += len(batch)
                self.stdout.write(self.style.SUCCESS(f"         ✅ Создана пачка из {len(batch)} человек"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"         Ошибка при создании пачки: {e}"))
                created_count += self._create_persons_one_by_one(batch)
            
            if created_count % 5000 == 0 or created_count >= total_count:
                percent = (created_count / total_count) * 100 if total_count > 0 else 0
                self.stdout.write(f"         Прогресс: {created_count}/{total_count} ({percent:.1f}%)")
        
        # Получаем созданных людей для маппинга
        if created_count > 0:
            created_names = [p.ceo for p in people_to_create[:created_count]]
            created_map = self._fetch_created_persons(created_names)
        
        return created_map

    def _filter_duplicate_persons(self, batch: List[Person]) -> List[Person]:
        """
        Фильтрация дубликатов в пачке по ceo_id и slug
        """
        batch_ceo_ids = [p.ceo_id for p in batch]
        batch_slugs = [p.slug for p in batch]
        
        existing_by_ceo = set(Person.objects.filter(ceo_id__in=batch_ceo_ids).values_list('ceo_id', flat=True))
        existing_by_slug = set(Person.objects.filter(slug__in=batch_slugs).values_list('slug', flat=True))
        
        if existing_by_ceo or existing_by_slug:
            self.stdout.write(self.style.WARNING(f"         Найдены дубликаты в пачке:"))
            if existing_by_ceo:
                self.stdout.write(self.style.WARNING(f"            по ceo_id: {list(existing_by_ceo)[:5]}..."))
            if existing_by_slug:
                self.stdout.write(self.style.WARNING(f"            по slug: {list(existing_by_slug)[:5]}..."))
            
            batch = [p for p in batch 
                    if p.ceo_id not in existing_by_ceo 
                    and p.slug not in existing_by_slug]
        
        return batch

    def _create_persons_one_by_one(self, batch: List[Person]) -> int:
        """
        Создание людей по одному в случае ошибки пачки
        """
        created = 0
        for person in batch:
            for attempt in range(10):
                try:
                    # Получаем свежий max_id перед каждой попыткой
                    current_max = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
                    person.ceo_id = current_max + 1
                    
                    # Проверяем и обновляем slug при необходимости
                    if Person.objects.filter(slug=person.slug).exists():
                        base_slug = person.slug.split('-')[0]
                        counter = 1
                        new_slug = f"{base_slug}-{counter}"
                        while Person.objects.filter(slug=new_slug).exists():
                            counter += 1
                            new_slug = f"{base_slug}-{counter}"
                        person.slug = new_slug
                    
                    person.save()
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"            ✅ Создан: {person.ceo}"))
                    break
                except Exception as e:
                    if attempt == 9:
                        self.stdout.write(self.style.ERROR(f"            ❌ Не удалось создать {person.ceo}: {e}"))
                    continue
        return created

    def _fetch_created_persons(self, names: List[str]) -> Dict[str, Person]:
        """
        Получение созданных людей из БД для маппинга
        """
        person_map = {}
        for batch in batch_iterator(names, 1000):
            for person in Person.objects.filter(ceo__in=batch).only('ceo_id', 'ceo', 'slug'):
                person_map[person.ceo] = person
                self.person_cache[person.ceo] = person
        return person_map

    # =========================================================================
    # МЕТОДЫ ДЛЯ МАССОВОГО СОЗДАНИЯ ОРГАНИЗАЦИЙ
    # =========================================================================

    def _create_organizations_bulk(self, orgs_df: pd.DataFrame) -> Dict[str, Organization]:
        """
        Пакетное создание организаций из DataFrame с индикацией прогресса
        
        Args:
            orgs_df: DataFrame с колонкой 'entity_name'
            
        Returns:
            Словарь {название: объект Organization}
        """
        org_map = {}
        
        if orgs_df.empty:
            self.stdout.write("      Нет организаций для обработки")
            return org_map
        
        all_names = orgs_df['entity_name'].tolist()
        total_names = len(all_names)
        
        self.stdout.write(f"      Всего уникальных организаций для обработки: {total_names}")
        
        # ШАГ 1: Поиск существующих организаций
        self.stdout.write(f"      Поиск существующих организаций в БД...")
        
        existing_orgs = self._find_existing_organizations(all_names)
        
        # ШАГ 2: Определяем новые организации
        new_names = [name for name in all_names if name not in existing_orgs]
        new_count = len(new_names)
        
        self.stdout.write(f"      Новых организаций для создания: {new_count}")
        
        # ШАГ 3: Создаем новые организации
        if new_names:
            new_orgs_map = self._create_new_organizations(new_names)
            org_map.update(new_orgs_map)
        
        # ШАГ 4: Добавляем существующие организации
        org_map.update(existing_orgs)
        
        self.stdout.write(f"      ✅ Обработано организаций: {len(org_map)}")
        
        return org_map

    def _find_existing_organizations(self, names: List[str]) -> Dict[str, Organization]:
        """
        Поиск существующих организаций в БД
        """
        existing_orgs = {}
        batch_size = 100
        
        for i in range(0, len(names), batch_size):
            batch_names = names[i:i+batch_size]
            
            for org in Organization.objects.filter(name__in=batch_names).only('organization_id', 'name', 'slug'):
                existing_orgs[org.name] = org
                self.organization_cache[org.name] = org
            
            if (i + len(batch_names)) % 500 == 0 or (i + len(batch_names)) >= len(names):
                self.stdout.write(f"         Обработано {i + len(batch_names)}/{len(names)} названий")
        
        self.stdout.write(f"      Найдено существующих: {len(existing_orgs)}")
        return existing_orgs

    def _create_new_organizations(self, new_names: List[str]) -> Dict[str, Organization]:
        """
        Создание новых организаций
        """
        self.stdout.write(f"      Подготовка данных для создания...")
        
        max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
        
        # Получаем все существующие slugs
        existing_slugs = set(Organization.objects.values_list('slug', flat=True))
        self.stdout.write(f"      Всего существующих slug: {len(existing_slugs)}")
        
        orgs_to_create = []
        used_slugs_in_batch = set()
        
        for name in new_names:
            base_slug = slugify(name[:50]) or 'organization'
            unique_slug = base_slug
            counter = 1
            
            # Проверяем И существующие slugs, И уже использованные в этом батче
            while unique_slug in existing_slugs or unique_slug in used_slugs_in_batch:
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            used_slugs_in_batch.add(unique_slug)
            existing_slugs.add(unique_slug)
            
            org = Organization(
                organization_id=max_id + len(orgs_to_create) + 1,
                name=name,
                full_name=name,
                short_name=name[:500] if len(name) > 500 else name,
                slug=unique_slug,
                register_opk=False,
                strategic=False,
            )
            orgs_to_create.append(org)
        
        # Создаем организации
        return self._bulk_create_organizations(orgs_to_create, len(new_names))

    def _bulk_create_organizations(self, orgs_to_create: List[Organization], total_count: int) -> Dict[str, Organization]:
        """
        Массовое создание организаций с обработкой ошибок
        """
        org_map = {}
        batch_size = 500
        created_count = 0
        
        for batch in batch_iterator(orgs_to_create, batch_size):
            try:
                # Пробуем создать пачкой с ignore_conflicts
                Organization.objects.bulk_create(batch, batch_size=batch_size, ignore_conflicts=True)
                created_count += len(batch)
            except Exception as e:
                self.stdout.write(f"         Ошибка при создании батча: {e}")
                # В случае ошибки создаем по одному
                for org in batch:
                    try:
                        org.save()
                        created_count += 1
                    except Exception as e2:
                        self.stdout.write(f"         Не удалось создать организацию {org.name}: {e2}")
            
            if created_count % 5000 == 0 or created_count == total_count:
                percent = (created_count / total_count) * 100 if total_count > 0 else 0
                self.stdout.write(f"         Создано {created_count}/{total_count} ({percent:.1f}%)")
        
        # Получаем созданные организации для маппинга
        if created_count > 0:
            created_names = [o.name for o in orgs_to_create[:created_count]]
            org_map = self._fetch_created_organizations(created_names)
        
        return org_map

    def _fetch_created_organizations(self, names: List[str]) -> Dict[str, Organization]:
        """
        Получение созданных организаций из БД для маппинга
        """
        org_map = {}
        for batch in batch_iterator(names, 1000):
            for org in Organization.objects.filter(name__in=batch).only('organization_id', 'name', 'slug'):
                org_map[org.name] = org
                self.organization_cache[org.name] = org
        return org_map

    # =========================================================================
    # МЕТОДЫ ДЛЯ РАБОТЫ СО СВЯЗЯМИ (ОБЩИЕ ДЛЯ ВСЕХ ПАРСЕРОВ)
    # =========================================================================

    def _process_relations_dataframe(self, relations_data: List[Dict], reg_to_ip: Dict):
        """
        Обработка всех связей через единый DataFrame
        Этот метод может быть переопределен в дочерних классах при необходимости
        """
        if not relations_data:
            self.stdout.write("   Нет данных для обработки связей")
            return

        self.stdout.write("   Создание DataFrame связей")
        df_relations = pd.DataFrame(relations_data)
        
        self.stdout.write(f"   Всего записей связей: {len(df_relations)}")
        self.stdout.write(f"   Уникальных регистрационных номеров: {df_relations['reg_number'].nunique()}")

        self.stdout.write("   Добавление ID объектов")
        df_relations['ip_id'] = df_relations['reg_number'].map(reg_to_ip)

        missing_ip = df_relations['ip_id'].isna().sum()
        if missing_ip > 0:
            self.stdout.write(self.style.WARNING(f"   ⚠️ Пропущено {missing_ip} связей с отсутствующими ID объектов"))
            df_relations = df_relations.dropna(subset=['ip_id']).copy()
        
        df_relations['ip_id'] = df_relations['ip_id'].astype(int)

        # Определение типов для правообладателей
        self.stdout.write("   Определение типов сущностей через Natasha")
        
        unique_entities = df_relations[['entity_name', 'entity_type']].drop_duplicates()
        holders_to_check = unique_entities[unique_entities['entity_type'].isna()]['entity_name'].tolist()

        if holders_to_check:
            self.stdout.write(f"   Определение типов для {len(holders_to_check)} правообладателей")
            entity_type_map = self.type_detector.detect_type_batch(holders_to_check)

            mask = df_relations['entity_type'].isna()
            df_relations.loc[mask, 'entity_type'] = \
                df_relations.loc[mask, 'entity_name'].map(entity_type_map)

        type_stats = df_relations['entity_type'].value_counts().to_dict()
        self.stdout.write(f"   Распределение типов: люди={type_stats.get('person', 0)}, "
                         f"организации={type_stats.get('organization', 0)}")

        # Группировка по сущностям
        unique_entities = df_relations[['entity_name', 'entity_type']].drop_duplicates()
        
        persons_df = unique_entities[unique_entities['entity_type'] == 'person']
        orgs_df = unique_entities[unique_entities['entity_type'] == 'organization']

        person_map = {}
        if not persons_df.empty:
            self.stdout.write(f"   Обработка {len(persons_df)} уникальных людей")
            person_map = self._create_persons_bulk(persons_df)

        org_map = {}
        if not orgs_df.empty:
            self.stdout.write(f"   Обработка {len(orgs_df)} уникальных организаций")
            org_map = self._create_organizations_bulk(orgs_df)

        # Подготовка связей
        self.stdout.write("   Подготовка связей для вставки в БД")

        authors_df = df_relations[df_relations['relation_type'] == 'author'].copy()
        holders_df = df_relations[df_relations['relation_type'] == 'holder'].copy()

        # Авторы
        author_relations = self._prepare_author_relations(authors_df, person_map)
        
        # Правообладатели (люди и организации)
        holder_person_relations, holder_org_relations = self._prepare_holder_relations(
            holders_df, person_map, org_map
        )

        # Создание связей
        self._create_all_relations(author_relations, holder_person_relations, holder_org_relations)

        self.stdout.write(self.style.SUCCESS("   ✅ Обработка всех связей завершена"))

    def _prepare_author_relations(self, authors_df: pd.DataFrame, person_map: Dict) -> List[Tuple[int, int]]:
        """Подготовка связей авторов"""
        if authors_df.empty:
            return []
        
        person_id_map = {name: p.ceo_id for name, p in person_map.items()}
        authors_df['person_id'] = authors_df['entity_name'].map(person_id_map)
        authors_df = authors_df.dropna(subset=['person_id'])
        authors_df['person_id'] = authors_df['person_id'].astype(int)
        
        authors_unique = authors_df[['ip_id', 'person_id']].drop_duplicates()
        relations = [(row['ip_id'], row['person_id']) for _, row in authors_unique.iterrows()]
        
        self.stdout.write(f"   Подготовлено {len(relations)} уникальных связей авторов")
        return relations

    def _prepare_holder_relations(self, holders_df: pd.DataFrame, person_map: Dict, org_map: Dict) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Подготовка связей правообладателей"""
        person_relations = []
        org_relations = []

        if holders_df.empty:
            return person_relations, org_relations

        # Правообладатели-люди
        holders_persons = holders_df[holders_df['entity_type'] == 'person'].copy()
        if not holders_persons.empty:
            person_id_map = {name: p.ceo_id for name, p in person_map.items()}
            holders_persons['person_id'] = holders_persons['entity_name'].map(person_id_map)
            holders_persons = holders_persons.dropna(subset=['person_id'])
            holders_persons['person_id'] = holders_persons['person_id'].astype(int)
            
            holders_persons_unique = holders_persons[['ip_id', 'person_id']].drop_duplicates()
            person_relations = [(row['ip_id'], row['person_id']) for _, row in holders_persons_unique.iterrows()]
            self.stdout.write(f"   Подготовлено {len(person_relations)} связей правообладателей-людей")

        # Правообладатели-организации
        holders_orgs = holders_df[holders_df['entity_type'] == 'organization'].copy()
        if not holders_orgs.empty:
            org_id_map = {name: o.organization_id for name, o in org_map.items()}
            holders_orgs['org_id'] = holders_orgs['entity_name'].map(org_id_map)
            holders_orgs = holders_orgs.dropna(subset=['org_id'])
            holders_orgs['org_id'] = holders_orgs['org_id'].astype(int)
            
            holders_orgs_unique = holders_orgs[['ip_id', 'org_id']].drop_duplicates()
            org_relations = [(row['ip_id'], row['org_id']) for _, row in holders_orgs_unique.iterrows()]
            self.stdout.write(f"   Подготовлено {len(org_relations)} связей правообладателей-организаций")

        return person_relations, org_relations

    def _create_all_relations(self, author_relations: List[Tuple[int, int]], 
                             holder_person_relations: List[Tuple[int, int]], 
                             holder_org_relations: List[Tuple[int, int]]):
        """Создание всех типов связей"""
        if author_relations:
            self.stdout.write("   Создание связей авторов")
            ip_ids = list(set(ip_id for ip_id, _ in author_relations))
            with tqdm(total=len(ip_ids), desc="   Удаление старых связей авторов", unit="ip") as pbar:
                self._delete_author_relations(ip_ids, pbar)
            
            with tqdm(total=len(author_relations), desc="   Создание новых связей авторов", unit="св") as pbar:
                self._create_author_relations(author_relations, pbar)

        if holder_person_relations:
            self.stdout.write("   Создание связей правообладателей (люди)")
            ip_ids = list(set(ip_id for ip_id, _ in holder_person_relations))
            with tqdm(total=len(ip_ids), desc="   Удаление старых связей", unit="ip") as pbar:
                self._delete_holder_person_relations(ip_ids, pbar)
            
            with tqdm(total=len(holder_person_relations), desc="   Создание новых связей", unit="св") as pbar:
                self._create_holder_person_relations(holder_person_relations, pbar)

        if holder_org_relations:
            self.stdout.write("   Создание связей правообладателей (организации)")
            ip_ids = list(set(ip_id for ip_id, _ in holder_org_relations))
            with tqdm(total=len(ip_ids), desc="   Удаление старых связей", unit="ip") as pbar:
                self._delete_holder_org_relations(ip_ids, pbar)
            
            with tqdm(total=len(holder_org_relations), desc="   Создание новых связей", unit="св") as pbar:
                self._create_holder_org_relations(holder_org_relations, pbar)

    # Методы для удаления связей
    def _delete_author_relations(self, ip_ids: List[int], pbar):
        """Удаление связей авторов"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.authors.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    def _delete_holder_person_relations(self, ip_ids: List[int], pbar):
        """Удаление связей правообладателей-людей"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.owner_persons.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    def _delete_holder_org_relations(self, ip_ids: List[int], pbar):
        """Удаление связей правообладателей-организаций"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.owner_organizations.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    # Методы для создания связей
    def _create_author_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей авторов"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.authors.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in batch
            ]
            IPObject.authors.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))

    def _create_holder_person_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей правообладателей-людей"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.owner_persons.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in batch
            ]
            IPObject.owner_persons.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))

    def _create_holder_org_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей правообладателей-организаций"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.owner_organizations.through(
                    ipobject_id=ip_id,
                    organization_id=org_id
                )
                for ip_id, org_id in batch
            ]
            IPObject.owner_organizations.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))
```


-----

# Файл: management\parsers\computer_program.py

```
"""
Парсер для программ для ЭВМ с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import re

import pandas as pd
from django.db import models, transaction
from django.utils.text import slugify
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from core.models import Organization

from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class ComputerProgramParser(BaseFIPSParser):
    """
    Парсер для программ для ЭВМ с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'computer-program'"""
        return IPType.objects.filter(slug='computer-program').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'program name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('creation_year', obj.creation_year, new_data.get('creation_year')),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг программ для ЭВМ{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'computer-program' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('program name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Программа для ЭВМ №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    
                    creation_year = None
                    creation_year_str = row.get('creation year')
                    if not pd.isna(creation_year_str) and creation_year_str:
                        try:
                            creation_year = int(float(creation_year_str))
                        except (ValueError, TypeError):
                            pass
                    
                    if not creation_year and application_date:
                        creation_year = application_date.year
                    elif not creation_year and registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'creation_year': creation_year,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self._parse_program_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Правообладатели
                    holders_str = row.get('right holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self._parse_right_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing computer program {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг программ для ЭВМ{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _parse_program_authors(self, authors_str: str) -> List[Dict]:
        """
        Парсинг строки с авторами для программ для ЭВМ
        """
        if pd.isna(authors_str) or not authors_str:
            return []

        authors_str = str(authors_str)
        authors_list = re.split(r'[\n]\s*', authors_str)

        result = []
        for author in authors_list:
            author = author.strip()
            if not author or author == '""' or author == 'null':
                continue

            author = author.strip('"')
            author = re.sub(r'\s*\([A-Z]{2}\)$', '', author)
            author = self.person_formatter.format(author)

            parts = author.split()

            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1] if len(parts) > 1 else ''
                middle_name = parts[2] if len(parts) > 2 else ''

                first_name_clean = first_name.replace('.', '')
                middle_name_clean = middle_name.replace('.', '')

                result.append({
                    'last_name': last_name,
                    'first_name': first_name_clean,
                    'middle_name': middle_name_clean,
                    'full_name': author,
                })
            else:
                result.append({
                    'last_name': author,
                    'first_name': '',
                    'middle_name': '',
                    'full_name': author,
                })

        return result

    def _parse_right_holders(self, holders_str: str) -> List[str]:
        """
        Парсинг строки с правообладателями для программ для ЭВМ
        """
        if pd.isna(holders_str) or not holders_str:
            return []
        
        holders_str = str(holders_str)
        holders_list = re.split(r'[\n]\s*', holders_str)
        
        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None' or holder.lower() == 'нет':
                continue
            holder = re.sub(r'\s*\([A-Z]{2}\)$', '', holder)
            result.append(holder)
        
        return result

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\database.py

```
"""
Парсер для баз данных с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import re

import pandas as pd
from django.db import models, transaction
from django.utils.text import slugify
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from core.models import Organization

from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class DatabaseParser(BaseFIPSParser):
    """
    Парсер для баз данных с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'database'"""
        return IPType.objects.filter(slug='database').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'db name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('expiration_date', obj.expiration_date, new_data.get('expiration_date')),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('creation_year', obj.creation_year, new_data.get('creation_year')),
            ('publication_year', obj.publication_year, new_data.get('publication_year')),
            ('update_year', obj.update_year, new_data.get('update_year')),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг баз данных{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'database' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('db name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"База данных №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    
                    creation_year = None
                    creation_year_str = row.get('creation year')
                    if not pd.isna(creation_year_str) and creation_year_str:
                        try:
                            creation_year = int(float(creation_year_str))
                        except (ValueError, TypeError):
                            pass
                    
                    publication_year = None
                    publication_year_str = row.get('publication year')
                    if not pd.isna(publication_year_str) and publication_year_str:
                        try:
                            publication_year = int(float(publication_year_str))
                        except (ValueError, TypeError):
                            pass
                    
                    update_year = None
                    update_year_str = row.get('update year')
                    if not pd.isna(update_year_str) and update_year_str:
                        try:
                            update_year = int(float(update_year_str))
                        except (ValueError, TypeError):
                            pass
                    
                    if not creation_year and application_date:
                        creation_year = application_date.year
                    elif not creation_year and registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'creation_year': creation_year,
                        'publication_year': publication_year,
                        'update_year': update_year,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self._parse_database_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Правообладатели
                    holders_str = row.get('right holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self._parse_right_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing database {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг баз данных{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _parse_database_authors(self, authors_str: str) -> List[Dict]:
        """
        Парсинг строки с авторами для баз данных
        """
        if pd.isna(authors_str) or not authors_str:
            return []

        authors_str = str(authors_str)
        authors_list = re.split(r'[\n]\s*', authors_str)

        result = []
        for author in authors_list:
            author = author.strip()
            if not author or author == '""' or author == 'null':
                continue

            author = author.strip('"')
            author = re.sub(r'\s*\([A-Z]{2}\)$', '', author)
            author = self.person_formatter.format(author)

            parts = author.split()

            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1] if len(parts) > 1 else ''
                middle_name = parts[2] if len(parts) > 2 else ''

                first_name_clean = first_name.replace('.', '')
                middle_name_clean = middle_name.replace('.', '')

                result.append({
                    'last_name': last_name,
                    'first_name': first_name_clean,
                    'middle_name': middle_name_clean,
                    'full_name': author,
                })
            else:
                result.append({
                    'last_name': author,
                    'first_name': '',
                    'middle_name': '',
                    'full_name': author,
                })

        return result

    def _parse_right_holders(self, holders_str: str) -> List[str]:
        """
        Парсинг строки с правообладателями для баз данных
        """
        if pd.isna(holders_str) or not holders_str:
            return []
        
        holders_str = str(holders_str)
        holders_list = re.split(r'[\n]\s*', holders_str)
        
        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None' or holder.lower() == 'нет':
                continue
            holder = re.sub(r'\s*\([A-Z]{2}\)$', '', holder)
            result.append(holder)
        
        return result

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\industrial_design.py

```
"""
Парсер для промышленных образцов с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

import pandas as pd
from django.db import models, transaction
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class IndustrialDesignParser(BaseFIPSParser):
    """
    Парсер для промышленных образцов с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'industrial-design'"""
        return IPType.objects.filter(slug='industrial-design').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'industrial design name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('patent_starting_date', obj.patent_starting_date, new_data['patent_starting_date']),
            ('expiration_date', obj.expiration_date, new_data['expiration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('abstract', obj.abstract, new_data['abstract']),
            ('creation_year', obj.creation_year, new_data['creation_year']),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг промышленных образцов{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'industrial-design' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('industrial design name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Промышленный образец №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    patent_starting_date = self.parse_date(row.get('patent starting date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    
                    abstract = ''

                    creation_year = None
                    if application_date:
                        creation_year = application_date.year
                    elif registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'patent_starting_date': patent_starting_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'abstract': abstract,
                        'creation_year': creation_year,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self.parse_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Патентообладатели
                    holders_str = row.get('patent holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self.parse_patent_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing industrial design {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            # Используем метод базового класса
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг промышленных образцов{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\integrated_circuit.py

```
"""
Парсер для топологий интегральных микросхем с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import re

import pandas as pd
from django.db import models, transaction
from django.utils.text import slugify
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType, Person
from core.models import Organization, Country

from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class IntegratedCircuitTopologyParser(BaseFIPSParser):
    """
    Парсер для топологий интегральных микросхем с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'integrated-circuit-topology'"""
        return IPType.objects.filter(slug='integrated-circuit-topology').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'microchip name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('expiration_date', obj.expiration_date, new_data['expiration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('creation_year', obj.creation_year, new_data['creation_year']),
            ('first_usage_date', obj.first_usage_date, new_data.get('first_usage_date')),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг топологий интегральных микросхем{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'integrated-circuit-topology' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        first_usage_countries_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('microchip name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Топология ИМС №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    
                    first_usage_date = self.parse_date(row.get('first usage date'))
                    
                    creation_year = None
                    if application_date:
                        creation_year = application_date.year
                    elif registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'creation_year': creation_year,
                        'first_usage_date': first_usage_date,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self.parse_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Правообладатели
                    holders_str = row.get('right holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self._parse_right_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                    # Страны первого использования
                    countries_str = row.get('first usage countries')
                    if not pd.isna(countries_str) and countries_str and countries_str.lower() != 'нет':
                        countries = self._parse_first_usage_countries(countries_str)
                        for country_code in countries:
                            first_usage_countries_data.append({
                                'reg_number': reg_num,
                                'country_code': country_code
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing integrated circuit topology {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        # =====================================================================
        # ШАГ 7: Обработка стран первого использования
        # =====================================================================
        if first_usage_countries_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка стран первого использования")
            self._process_first_usage_countries(first_usage_countries_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг топологий интегральных микросхем{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _parse_right_holders(self, holders_str: str) -> List[str]:
        """
        Парсинг строки с правообладателями для топологий ИМС
        """
        if pd.isna(holders_str) or not holders_str:
            return []
        
        holders_str = str(holders_str)
        holders_list = re.split(r'[\n]\s*', holders_str)
        
        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None' or holder.lower() == 'нет':
                continue
            holder = re.sub(r'\s*\([A-Z]{2}\)$', '', holder)
            result.append(holder)
        
        return result

    def _parse_first_usage_countries(self, countries_str: str) -> List[str]:
        """
        Парсинг строки со странами первого использования
        """
        if pd.isna(countries_str) or not countries_str:
            return []
        
        countries_str = str(countries_str)
        if countries_str.lower() == 'нет':
            return []
        
        countries = re.split(r'[,\s]+', countries_str)
        
        result = []
        country_map = {
            'РФ': 'RU',
            'Россия': 'RU',
            'Российская Федерация': 'RU',
            'RU': 'RU',
            'RUS': 'RU',
        }
        
        for country in countries:
            country = country.strip()
            if not country:
                continue
            
            if country in country_map:
                result.append(country_map[country])
            elif len(country) == 2 and country.isupper():
                result.append(country)
            else:
                country_obj = Country.objects.filter(name__icontains=country).first()
                if country_obj:
                    result.append(country_obj.code)
                else:
                    self.stdout.write(self.style.WARNING(f"      ⚠️ Не удалось определить код страны: {country}"))
        
        return list(set(result))

    def _process_first_usage_countries(self, countries_data: List[Dict], reg_to_ip: Dict):
        """
        Обработка связей со странами первого использования
        """
        if not countries_data:
            return
        
        self.stdout.write("   Подготовка связей со странами первого использования")
        
        reg_to_countries = defaultdict(set)
        for item in countries_data:
            ip_id = reg_to_ip.get(item['reg_number'])
            if ip_id:
                reg_to_countries[ip_id].add(item['country_code'])
        
        if not reg_to_countries:
            return
        
        country_codes = set()
        for countries in reg_to_countries.values():
            country_codes.update(countries)
        
        country_map = {}
        for code in country_codes:
            country = self.get_or_create_country(code)
            if country:
                country_map[code] = country
        
        ip_ids = list(reg_to_countries.keys())
        
        # Удаляем старые связи
        with tqdm(total=len(ip_ids), desc="   Удаление старых связей со странами", unit="ip") as pbar:
            delete_batch_size = 500
            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ids = ip_ids[i:i+delete_batch_size]
                IPObject.first_usage_countries.through.objects.filter(
                    ipobject_id__in=batch_ids
                ).delete()
                pbar.update(len(batch_ids))
        
        # Создаем новые связи
        through_objs = []
        for ip_id, country_codes in reg_to_countries.items():
            for code in country_codes:
                country = country_map.get(code)
                if country:
                    through_objs.append(
                        IPObject.first_usage_countries.through(
                            ipobject_id=ip_id,
                            country_id=country.id
                        )
                    )
        
        if through_objs:
            with tqdm(total=len(through_objs), desc="   Создание связей со странами", unit="св") as pbar:
                create_batch_size = 2000
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.first_usage_countries.through.objects.bulk_create(
                        batch, batch_size=create_batch_size, ignore_conflicts=True
                    )
                    pbar.update(len(batch))
        
        self.stdout.write("   ✅ Обработка стран первого использования завершена")

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\invention.py

```
"""
Парсер для изобретений с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

import pandas as pd
from django.db import models, transaction
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class InventionParser(BaseFIPSParser):
    """
    Парсер для изобретений с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'invention'"""
        return IPType.objects.filter(slug='invention').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'invention name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('patent_starting_date', obj.patent_starting_date, new_data['patent_starting_date']),
            ('expiration_date', obj.expiration_date, new_data['expiration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('abstract', obj.abstract, new_data['abstract']),
            ('claims', obj.claims, new_data['claims']),
            ('creation_year', obj.creation_year, new_data['creation_year']),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг изобретений{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'invention' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    name = self.clean_string(row.get('invention name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Изобретение №{reg_num}"

                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    patent_starting_date = self.parse_date(row.get('patent starting date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    abstract = self.clean_string(row.get('abstract'))
                    claims = self.clean_string(row.get('claims'))

                    creation_year = None
                    if application_date:
                        creation_year = application_date.year
                    elif registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'patent_starting_date': patent_starting_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'abstract': abstract,
                        'claims': claims,
                        'creation_year': creation_year,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self.parse_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Патентообладатели
                    holders_str = row.get('patent holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self.parse_patent_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing invention {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг изобретений{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\utility_model.py

```
"""
Парсер для полезных моделей с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

import pandas as pd
from django.db import models, transaction
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class UtilityModelParser(BaseFIPSParser):
    """
    Парсер для полезных моделей с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'utility-model'"""
        return IPType.objects.filter(slug='utility-model').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'utility model name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('patent_starting_date', obj.patent_starting_date, new_data['patent_starting_date']),
            ('expiration_date', obj.expiration_date, new_data['expiration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('abstract', obj.abstract, new_data['abstract']),
            ('claims', obj.claims, new_data['claims']),
            ('creation_year', obj.creation_year, new_data['creation_year']),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг полезных моделей{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'utility-model' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('utility model name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Полезная модель №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    patent_starting_date = self.parse_date(row.get('patent starting date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    
                    abstract = self.clean_string(row.get('abstract', ''))
                    claims = self.clean_string(row.get('claims', ''))

                    creation_year = None
                    if application_date:
                        creation_year = application_date.year
                    elif registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'patent_starting_date': patent_starting_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'abstract': abstract,
                        'claims': claims,
                        'creation_year': creation_year,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self.parse_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Патентообладатели
                    holders_str = row.get('patent holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self.parse_patent_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing utility model {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг полезных моделей{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\__init__.py

```
"""
Пакет с парсерами для различных типов РИД
"""

from .invention import InventionParser
from .utility_model import UtilityModelParser
from .industrial_design import IndustrialDesignParser
from .integrated_circuit import IntegratedCircuitTopologyParser
from .computer_program import ComputerProgramParser
from .database import DatabaseParser

# Импортируем процессоры из подпакета processors
from .processors import (
    RussianTextProcessor,
    OrganizationNormalizer,
    PersonNameFormatter,
    RIDNameFormatter,
    EntityTypeDetector
)

__all__ = [
    'InventionParser',
    'UtilityModelParser',
    'IndustrialDesignParser',
    'IntegratedCircuitTopologyParser',
    'ComputerProgramParser',
    'DatabaseParser',
    'RussianTextProcessor',
    'OrganizationNormalizer',
    'PersonNameFormatter',
    'RIDNameFormatter',
    'EntityTypeDetector',
]
```


-----

# Файл: management\parsers\processors\entity_detector.py

```
"""
Детектор типов сущностей с использованием Natasha и кэшированием
"""

# ИСПРАВЛЕНО: импортируем из текущего пакета (.text_processor)
from .text_processor import RussianTextProcessor


class EntityTypeDetector:
    """
    Детектор типов сущностей с использованием Natasha и кэшированием
    Определяет, является ли текст именем человека или названием организации
    """

    def __init__(self, cache_size: int = 50000):
        self.processor = RussianTextProcessor()
        # Кэш для результатов, чтобы не вызывать Natasha повторно
        self.cache = {}
        self.cache_size = cache_size
        self.cache_hits = 0
        self.cache_misses = 0

    def detect_type(self, text: str) -> str:
        """
        Определение типа сущности с использованием Natasha

        Args:
            text: Название сущности (ФИО или название организации)

        Returns:
            'person' или 'organization'
        """
        if not text or len(text) < 2:
            return 'organization'

        # Проверяем кэш
        if text in self.cache:
            self.cache_hits += 1
            return self.cache[text]

        self.cache_misses += 1

        # Используем процессор с Natasha для определения
        # is_person() внутри использует NER и другие методы Natasha
        if self.processor.is_person(text):
            result = 'person'
        else:
            result = 'organization'

        # Кэшируем результат с контролем размера
        self._add_to_cache(text, result)

        return result

    def detect_type_batch(self, texts: list) -> dict:
        """
        Пакетное определение типов для списка текстов

        Args:
            texts: Список текстов для анализа

        Returns:
            Словарь {текст: тип}
        """
        result = {}

        # Сначала проверяем кэш
        to_process = []
        for text in texts:
            if text in self.cache:
                result[text] = self.cache[text]
                self.cache_hits += 1
            else:
                to_process.append(text)
                self.cache_misses += 1

        # Обрабатываем новые тексты
        for text in to_process:
            if self.processor.is_person(text):
                result[text] = 'person'
            else:
                result[text] = 'organization'
            self._add_to_cache(text, result[text])

        return result

    def _add_to_cache(self, text: str, result: str):
        """
        Добавление результата в кэш с контролем размера
        """
        if len(self.cache) >= self.cache_size:
            # Очищаем 20% самых старых записей
            items = list(self.cache.items())
            self.cache = dict(items[-int(self.cache_size * 0.8):])

        self.cache[text] = result

    def get_cache_stats(self) -> dict:
        """
        Статистика кэша для отладки
        """
        total = self.cache_hits + self.cache_misses
        return {
            'size': len(self.cache),
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_ratio': self.cache_hits / total if total > 0 else 0
        }

    def clear_cache(self):
        """Очистка кэша для освобождения памяти"""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
```


-----

# Файл: management\parsers\processors\organization.py

```
"""
Нормализация названий организаций (только для поиска, не для сохранения)
"""

import re
from typing import Dict, Any

import pandas as pd

from core.models import OrganizationNormalizationRule

# ИСПРАВЛЕНО: импортируем из текущего пакета (.text_processor)
from .text_processor import RussianTextProcessor


class OrganizationNormalizer:
    """Нормализация названий организаций (только для поиска, не для сохранения)"""

    def __init__(self):
        self.rules_cache = None
        self.processor = RussianTextProcessor()
        self.load_rules()

    def load_rules(self):
        """Загрузка правил из БД"""
        try:
            rules = OrganizationNormalizationRule.objects.all().order_by('priority')
            self.rules_cache = [
                {
                    'original': rule.original_text.lower(),
                    'replacement': rule.replacement_text.lower(),
                    'type': rule.rule_type,
                    'priority': rule.priority
                }
                for rule in rules
            ]
        except Exception as e:
            self.rules_cache = []
            # Логирование ошибки, но не падаем

    def normalize_for_search(self, name: str) -> Dict[str, Any]:
        """
        Нормализация названия ТОЛЬКО для поиска дубликатов
        Само название остается как в CSV
        """
        if pd.isna(name) or not name:
            return {'normalized': '', 'keywords': [], 'original': name}

        original = str(name).strip()
        name_lower = original.lower()

        # Применяем правила из БД для нормализации
        normalized = name_lower
        if self.rules_cache:
            for rule in self.rules_cache:
                try:
                    if rule['type'] == 'ignore':
                        pattern = r'\b' + re.escape(rule['original']) + r'\b'
                        normalized = re.sub(pattern, '', normalized)
                    else:
                        pattern = r'\b' + re.escape(rule['original']) + r'\b'
                        normalized = re.sub(pattern, rule['replacement'], normalized)
                except Exception:
                    continue

        # Убираем кавычки и знаки препинания для поиска
        normalized = re.sub(r'["\'«»„“”]', '', normalized)
        normalized = re.sub(r'[^\w\s-]', ' ', normalized)
        normalized = ' '.join(normalized.split())

        # Извлекаем ключевые слова для поиска
        keywords = []

        # Слова в кавычках
        quoted = re.findall(r'"([^"]+)"', original)
        for q in quoted:
            words = q.lower().split()
            keywords.extend([w for w in words if len(w) > 3])

        # Аббревиатуры
        abbrs = re.findall(r'\b[А-ЯЁA-Z]{2,}\b', original)
        keywords.extend([a.lower() for a in abbrs if len(a) >= 2])

        # Коды (ИНН, ОГРН и т.д.)
        codes = re.findall(r'\b\d{10,}\b', original)
        keywords.extend(codes)

        return {
            'normalized': normalized,
            'keywords': list(set(keywords)),
            'original': original,
        }

    def format_organization_name(self, name: str) -> str:
        """Возвращает оригинальное название без изменений"""
        return name

```


-----

# Файл: management\parsers\processors\person.py

```
"""
Форматирование имен людей
"""
from .text_processor import RussianTextProcessor


class PersonNameFormatter:
    """Форматирование имен людей"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def format(self, name: str) -> str:
        """Форматирование ФИО"""
        return self.processor.format_person_name(name)

```


-----

# Файл: management\parsers\processors\rid.py

```
"""
Форматирование названий РИД
"""

from .text_processor import RussianTextProcessor


class RIDNameFormatter:
    """Форматирование названий РИД"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def format(self, text: str) -> str:
        """Форматирование названия РИД"""
        if not text or not isinstance(text, str):
            return text

        if len(text.strip()) <= 1:
            return text

        # Приводим к нижнему регистру и делаем первую букву заглавной
        words = text.lower().split()
        if words:
            words[0] = words[0][0].upper() + words[0][1:]
        return ' '.join(words)

```


-----

# Файл: management\parsers\processors\text_processor.py

```
"""
Процессор для русских текстов с использованием natasha
"""

from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,
    Doc,
    NamesExtractor
)


class RussianTextProcessor:
    """
    Процессор для русских текстов с использованием natasha
    """

    # Список римских цифр
    ROMAN_NUMERALS = {
        'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
        'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
        'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXX', 'XL', 'L', 'LX', 'XC',
        'C', 'CD', 'D', 'DC', 'CM', 'M'
    }

    # Аббревиатуры для поиска организаций
    ORG_ABBR = {
        'ООО', 'ЗАО', 'ОАО', 'АО', 'ПАО', 'НАО',
        'ФГУП', 'ФГБУ', 'ФГАОУ', 'ФГАУ', 'ФГКУ',
        'НИИ', 'КБ', 'ОКБ', 'СКБ', 'ЦКБ', 'ПКБ',
        'НПО', 'НПП', 'НПФ', 'НПЦ', 'НИЦ',
        'МУП', 'ГУП', 'ИЧП', 'ТОО', 'АОЗТ', 'АООТ',
        'РФ', 'РАН', 'СО РАН', 'УрО РАН', 'ДВО РАН',
        'МГУ', 'СПбГУ', 'МФТИ', 'МИФИ', 'МГТУ', 'МАИ',
        'ЛТД', 'ИНК', 'КО', 'ГМБХ', 'АГ', 'СА', 'НВ', 'БВ', 'СЕ',
        'Ко', 'Ltd', 'Inc', 'GmbH', 'AG', 'SA', 'NV', 'BV', 'SE',
    }

    def __init__(self):
        # Инициализация компонентов natasha
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.emb = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(self.emb)
        self.syntax_parser = NewsSyntaxParser(self.emb)
        self.ner_tagger = NewsNERTagger(self.emb)
        self.names_extractor = NamesExtractor(self.morph_vocab)

        # Кэши для производительности
        self.doc_cache = {}
        self.morph_cache = {}

        # Добавляем римские цифры в аббревиатуры
        self.ORG_ABBR.update(self.ROMAN_NUMERALS)

    def get_doc(self, text: str) -> Doc:
        """Получение или создание документа с кэшированием"""
        if not text:
            return None

        if text in self.doc_cache:
            return self.doc_cache[text]

        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        doc.parse_syntax(self.syntax_parser)
        doc.tag_ner(self.ner_tagger)

        # Лемматизация
        for token in doc.tokens:
            token.lemmatize(self.morph_vocab)

        for span in doc.spans:
            span.normalize(self.morph_vocab)

        self.doc_cache[text] = doc
        return doc

    def is_roman_numeral(self, text: str) -> bool:
        """Проверка на римскую цифру"""
        if not text:
            return False
        clean_text = text.strip('.,;:!?()').upper()
        return clean_text in self.ROMAN_NUMERALS

    def is_abbr(self, text: str) -> bool:
        """Проверка на аббревиатуру организации"""
        if not text:
            return False
        clean_text = text.strip('.,;:!?()').upper()
        return clean_text in self.ORG_ABBR

    def is_person(self, text: str) -> bool:
        """Определение, является ли текст ФИО человека"""
        if not text or len(text) < 6:
            return False

        # Если есть явные признаки организации
        if any(ind in text for ind in self.ORG_ABBR if len(ind) > 2):
            return False

        org_indicators = ['Общество', 'Компания', 'Корпорация', 'Завод',
                         'Институт', 'Университет', 'Академия', 'Лаборатория',
                         'Фирма', 'Центр']

        if any(ind.lower() in text.lower() for ind in org_indicators):
            return False

        # Проверка через NER
        doc = self.get_doc(text)
        if doc and doc.spans:
            for span in doc.spans:
                if span.type == 'PER':
                    return True

        # Паттерны ФИО
        words = text.split()
        if 2 <= len(words) <= 4:
            name_like = 0
            for word in words:
                clean = word.rstrip('.,')
                if clean and clean[0].isupper() and len(clean) > 1:
                    name_like += 1
            return name_like >= len(words) - 1

        return False

    def extract_person_parts(self, text: str) -> dict:
        """Извлечение частей ФИО с помощью natasha"""
        matches = list(self.names_extractor(text))
        if matches:
            fact = matches[0].fact
            parts = []
            if fact.last:
                parts.append(fact.last)
            if fact.first:
                parts.append(fact.first)
            if fact.middle:
                parts.append(fact.middle)

            return {
                'last': fact.last or '',
                'first': fact.first or '',
                'middle': fact.middle or '',
                'full': ' '.join(parts)
            }

        # Fallback: ручной парсинг
        return self._parse_name_manually(text)

    def _parse_name_manually(self, text: str) -> dict:
        """Ручной парсинг имени"""
        words = text.split()

        if len(words) == 3:
            return {
                'last': words[0],
                'first': words[1],
                'middle': words[2],
                'full': text
            }
        elif len(words) == 2:
            return {
                'last': words[0],
                'first': words[1],
                'middle': '',
                'full': text
            }
        else:
            return {
                'last': text,
                'first': '',
                'middle': '',
                'full': text
            }

    def format_person_name(self, name: str) -> str:
        """Форматирование ФИО человека"""
        if not name:
            return name

        parts = self.extract_person_parts(name)
        if parts.get('full'):
            return parts['full']

        return name

```


-----

# Файл: management\parsers\processors\__init__.py

```
from .text_processor import RussianTextProcessor
from .organization import OrganizationNormalizer
from .person import PersonNameFormatter
from .rid import RIDNameFormatter
from .entity_detector import EntityTypeDetector

__all__ = [
    'RussianTextProcessor',
    'OrganizationNormalizer',
    'PersonNameFormatter',
    'RIDNameFormatter',
    'EntityTypeDetector',
]
```


-----

# Файл: management\utils\csv_loader.py

```
"""
Утилиты для загрузки CSV файлов
"""

import pandas as pd


def load_csv_with_strategies(file_path, encoding, delimiter, stdout=None):
    """
    Загрузка CSV с несколькими стратегиями
    """
    strategies = [
        {'encoding': encoding, 'delimiter': delimiter, 'skipinitialspace': True},
        {'encoding': 'cp1251', 'delimiter': delimiter, 'skipinitialspace': True},
        {'encoding': 'utf-8', 'delimiter': ';', 'skipinitialspace': True},
        {'encoding': 'cp1251', 'delimiter': ';', 'skipinitialspace': True},
        {'encoding': 'utf-8', 'delimiter': '\t', 'skipinitialspace': True},
    ]

    for strategy in strategies:
        try:
            df = pd.read_csv(file_path, **strategy, dtype=str, keep_default_na=False)
            if stdout:
                stdout.write(f"  ✅ Успешно загружено с параметрами: {strategy}")

            df.columns = [col.strip().strip('\ufeff').strip('"') for col in df.columns]
            return df
        except Exception:
            continue

    raise Exception("Не удалось загрузить CSV ни одной стратегией")

```


-----

# Файл: management\utils\filters.py

```
"""
Утилиты для фильтрации DataFrame
Поддерживают фильтрацию по диапазону лет
"""

from datetime import datetime
import pandas as pd


def filter_by_registration_year(df, min_year, stdout=None, max_year=None):
    """
    Фильтрация DataFrame по году регистрации с поддержкой диапазона
    
    Args:
        df: DataFrame для фильтрации
        min_year: минимальный год
        stdout: поток вывода
        max_year: максимальный год (опционально)
    """
    def extract_year(date_str):
        try:
            if pd.isna(date_str) or not date_str:
                return None

            date_str = str(date_str).strip()
            if not date_str:
                return None

            for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str, fmt).year
                except (ValueError, TypeError):
                    continue

            try:
                return pd.to_datetime(date_str).year
            except (ValueError, TypeError):
                return None
        except:
            return None

    if stdout:
        stdout.write("  🔍 Фильтрация по году регистрации...")

    if 'registration date' not in df.columns:
        if stdout:
            stdout.write("  ⚠️ Колонка 'registration date' не найдена, пропускаем фильтрацию по году")
        return df

    df['_year'] = df['registration date'].apply(extract_year)

    if stdout:
        # Фильтруем None значения для статистики
        valid_years = df['_year'].dropna()
        if not valid_years.empty:
            years_dist = valid_years.value_counts().sort_index()
            years_list = list(years_dist.items())
            if len(years_list) > 0:
                stdout.write(f"     Диапазон годов: {years_list[0][0]:.0f} - {years_list[-1][0]:.0f}")

    # Применяем фильтр по годам
    condition = df['_year'] >= min_year
    if max_year:
        condition &= df['_year'] <= max_year
    
    filtered_df = df[condition].copy() if '_year' in df.columns else df.copy()
    
    if '_year' in filtered_df.columns:
        filtered_df.drop('_year', axis=1, inplace=True)

    return filtered_df


def filter_by_actual(df, stdout=None):
    """
    Фильтрация DataFrame по активности (actual = True)
    """
    def parse_actual(value):
        if pd.isna(value) or not value:
            return False
        value = str(value).lower().strip()
        return value in ['1', 'true', 'yes', 'да', 'действует', 't', '1.0', 'активен']

    if 'actual' not in df.columns:
        if stdout:
            stdout.write("  ⚠️ Колонка 'actual' не найдена, пропускаем фильтрацию по активности")
        return df

    df['_actual'] = df['actual'].apply(parse_actual)
    filtered_df = df[df['_actual'] == True].copy()
    filtered_df.drop('_actual', axis=1, inplace=True)

    return filtered_df


def apply_filters(df, min_year, only_active, stdout=None, max_year=None):
    """
    Применение всех фильтров к DataFrame
    
    Args:
        df: DataFrame для фильтрации
        min_year: минимальный год
        only_active: фильтровать только активные
        stdout: поток вывода
        max_year: максимальный год (опционально)
    """
    original_count = len(df)

    if min_year is not None:
        df = filter_by_registration_year(df, min_year, stdout, max_year)

    if only_active:
        df = filter_by_actual(df, stdout)

    filtered_count = len(df)
    if stdout and filtered_count < original_count:
        stdout.write(f"  🔍 Фильтрация: {original_count} → {filtered_count} записей")

    return df
```


-----

# Файл: management\utils\progress.py

```
"""
Утилиты для отображения прогресс-баров
Вынесены отдельно для переиспользования в других парсерах
"""

import sys
from tqdm import tqdm
from contextlib import contextmanager
from typing import Optional, Iterable, Iterator, Any


class ProgressManager:
    """
    Менеджер для работы с прогресс-барами
    Все прогресс-бары отображаются в одной строке (как в оригинальном tqdm)
    """
    
    def __init__(self, enabled: bool = True, file=sys.stdout):
        self.enabled = enabled
        self.file = file
        self._current_bar = None  # Текущий активный прогресс-бар
    
    @contextmanager
    def task(self, description: str, total: Optional[int] = None, unit: str = "элем"):
        """
        Контекстный менеджер для задачи с прогресс-баром
        Все задачи используют одну строку (предыдущая закрывается)
        """
        # Если есть предыдущий бар, закрываем его
        if self._current_bar is not None:
            self._current_bar.close()
        
        # Создаем новый прогресс-бар
        bar = tqdm(
            total=total,
            desc=description,
            unit=unit,
            file=self.file,
            leave=False,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
        
        self._current_bar = bar
        
        try:
            yield bar
        finally:
            bar.close()
            self._current_bar = None
            print(file=self.file)
    
    @contextmanager
    def subtask(self, description: str, total: Optional[int] = None, unit: str = "элем"):
        """Алиас для task (для обратной совместимости)"""
        with self.task(description, total, unit) as bar:
            yield bar
    
    def step(self, message: str):
        """Вывод сообщения о шаге (всегда с новой строки)"""
        if self._current_bar is not None:
            self._current_bar.write(f"🔹 {message}")
        else:
            print(f"🔹 {message}", file=self.file)

    def success(self, message: str):
        """Вывод сообщения об успехе"""
        if self._current_bar is not None:
            self._current_bar.write(f"✅ {message}")
        else:
            print(f"✅ {message}", file=self.file)

    def warning(self, message: str):
        """Вывод предупреждения"""
        if self._current_bar is not None:
            self._current_bar.write(f"⚠️ {message}")
        else:
            print(f"⚠️ {message}", file=self.file)

    def error(self, message: str):
        """Вывод ошибки"""
        if self._current_bar is not None:
            self._current_bar.write(f"❌ {message}")
        else:
            print(f"❌ {message}", file=self.file)


def batch_iterator(iterable, batch_size: int):
    """Разбивает итерируемый объект на батчи"""
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
```


-----

# Файл: management\utils\__init__.py

```
"""
Утилиты для парсеров
"""

from .csv_loader import load_csv_with_strategies
from .filters import apply_filters
from .progress import ProgressManager, batch_iterator

__all__ = [
    'load_csv_with_strategies',
    'apply_filters',
    'ProgressManager',
    'batch_iterator',
]
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
    
    parsed_date = models.DateTimeField(
        verbose_name='Дата парсинга',
        help_text='Дата и время, когда каталог был обработан парсером',
        blank=True,
        null=True,
        db_index=True
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
from core.models.models_foiv import FOIV, RFRepresentative
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

# Файл: templates\intellectual_property\ipobject_list.html

```
{# templates/intellectual_property/ipobject_list.html #}
{% extends 'layout/base.html' %}
{% load static %}
{% load common_tags %}

{% block title %}
  Реестр РИД - IntellectPool
{% endblock %}

{% block extra_css %}
  {# Дополнительные стили уже в main.scss, но можно добавить специфичные #}
  <style>
    /* Микро-оптимизации для конкретной страницы */
    .filter-badge {
      display: inline-block;
      width: 8px;
      height: 8px;
      background-color: var(--bs-danger);
      border-radius: 50%;
      margin-left: 5px;
    }
  </style>
{% endblock %}

{% block content %}
  <div class="container-fluid py-4">
    {# Заголовок страницы #}
    <div class="row mb-4">
      <div class="col d-flex justify-content-between align-items-center">
        <h1 class="h2 fw-bold">
          <i class="bi bi-file-earmark-text me-2 text-primary"></i>
          Реестр результатов интеллектуальной деятельности
        </h1>
        <div>
          <span class="badge bg-primary bg-opacity-10 text-primary p-2" data-ip-stats><i class="bi bi-database me-1"></i>Записей: {{ page_obj.paginator.count }}</span>
        </div>
      </div>
    </div>

    {# Блок фильтрации #}
    <div class="row mb-4">
      <div class="col">
        <div class="card shadow-sm border-0">
          <div class="card-header bg-light py-2 d-flex justify-content-between align-items-center">
            <h6 class="mb-0"><i class="bi bi-funnel me-2"></i>Фильтры</h6>
            <small class="text-muted"><i class="bi bi-keyboard me-1"></i>Ctrl+F — поиск, Esc — сброс</small>
          </div>
          <div class="card-body py-3">
            <form method="get" id="filter-form">
              <div class="row g-2">
                <div class="col-md-4">
                  <label class="small fw-bold text-muted mb-1">Наименование РИД</label>
                  {{ filter.form.name }}
                </div>
                <div class="col-md-3">
                  <label class="small fw-bold text-muted mb-1">Рег. номер</label>
                  {{ filter.form.registration_number }}
                </div>
                <div class="col-md-3">
                  <label class="small fw-bold text-muted mb-1">Вид РИД</label>
                  {{ filter.form.ip_type }}
                </div>
                <div class="col-md-2">
                  <label class="small fw-bold text-muted mb-1">Статус</label>
                  {{ filter.form.actual }}
                </div>
              </div>
              <div class="row mt-3">
                <div class="col d-flex gap-2">
                  <button type="submit" class="btn btn-sm btn-primary"><i class="bi bi-search me-1"></i>Применить</button>
                  <a href="?" class="btn btn-sm btn-outline-secondary"><i class="bi bi-eraser me-1"></i>Сброс</a>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>

    {# Инструменты таблицы #}
    <div class="row mb-3">
      <div class="col">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#columnSelector"><i class="bi bi-layout-three-columns me-1"></i>Настройка колонок</button>
          </div>
          <div class="text-muted small">
            <i class="bi bi-arrow-left-right me-1"></i>Горизонтальная прокрутка
          </div>
        </div>
      </div>
    </div>

    {# Панель выбора колонок #}
    <div class="collapse mb-3" id="columnSelector">
      <div class="card card-body bg-light">
        <div class="row g-2" id="columnToggle">
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="type" id="colType" checked />
              <label class="form-check-label" for="colType">Вид РИД</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="name" id="colName" checked />
              <label class="form-check-label" for="colName">Наименование</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="year" id="colYear" checked />
              <label class="form-check-label" for="colYear">Год создания</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="regDate" id="colRegDate" checked />
              <label class="form-check-label" for="colRegDate">Дата регистрации</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="owners" id="colOwners" checked />
              <label class="form-check-label" for="colOwners">Правообладатели</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="docType" id="colDocType" checked />
              <label class="form-check-label" for="colDocType">Вид документа</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="docNumber" id="colDocNumber" checked />
              <label class="form-check-label" for="colDocNumber">Номер документа</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="authors" id="colAuthors" checked />
              <label class="form-check-label" for="colAuthors">Авторы</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="abstract" id="colAbstract" checked />
              <label class="form-check-label" for="colAbstract">Реферат</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="status" id="colStatus" checked />
              <label class="form-check-label" for="colStatus">Статус</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="lang" id="colLang" checked />
              <label class="form-check-label" for="colLang">Языки</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="db" id="colDb" checked />
              <label class="form-check-label" for="colDb">СУБД</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="claims" id="colClaims" checked />
              <label class="form-check-label" for="colClaims">Формула</label>
            </div>
          </div>
          <div class="col-md-3">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="expiry" id="colExpiry" checked />
              <label class="form-check-label" for="colExpiry">Срок действия</label>
            </div>
          </div>
        </div>
      </div>
    </div>

    {# Контейнер таблицы #}
    <div class="row">
      <div class="col">
        <div class="ip-table-container">
          <div class="table-responsive">
            <table class="table table-sm table-hover align-middle mb-0" id="ipTable">
              <thead>
                <tr>
                  <th data-column="type">Вид РИД</th>
                  <th data-column="name">Наименование РИД</th>
                  <th data-column="year">Год</th>
                  <th data-column="regDate">Дата рег.</th>
                  <th data-column="owners">Правообладатели</th>
                  <th data-column="docType">Вид док.</th>
                  <th data-column="docNumber">Номер док.</th>
                  <th data-column="docDate">Дата док.</th>
                  <th data-column="appDate">Дата заявки</th>
                  <th data-column="authors">Авторы</th>
                  <th data-column="abstract">Реферат</th>
                  <th data-column="status">Статус</th>
                  <th data-column="statusDate">Дата статуса</th>
                  <th data-column="lang">Языки</th>
                  <th data-column="db">СУБД</th>
                  <th data-column="claims">Формула</th>
                  <th data-column="expiry">Срок</th>
                </tr>
              </thead>
              <tbody>
                {% for ip in ip_objects %}
                  {% include 'intellectual_property/components/ip_table_row.html' with ip=ip %}
                {% empty %}
                  <tr>
                    <td colspan="23" class="text-center text-muted py-5">
                      <i class="bi bi-inbox display-4 d-block mb-3 opacity-50"></i>
                      <span class="h5">Записей не найдено</span>
                      <p class="text-muted mt-2">Попробуйте изменить параметры фильтрации</p>
                    </td>
                  </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    {# Пагинация #}
    {% if page_obj.paginator.num_pages > 1 %}
      <div class="row mt-4">
        <div class="col">
          <div class="ip-pagination">
            <nav aria-label="Навигация по страницам">
              <ul class="pagination justify-content-center">
                {% if page_obj.has_previous %}
                  <li class="page-item">
                    <a class="page-link" href="?{% query_transform request page=1 %}" aria-label="Первая"><i class="bi bi-chevron-double-left"></i></a>
                  </li>
                  <li class="page-item">
                    <a class="page-link" href="?{% query_transform request page=page_obj.previous_page_number %}" aria-label="Предыдущая"><i class="bi bi-chevron-left"></i></a>
                  </li>
                {% endif %}

                {% for num in page_obj.paginator.page_range %}
                  {% if page_obj.number == num %}
                    <li class="page-item active">
                      <span class="page-link">{{ num }}</span>
                    </li>
                  {% elif num > page_obj.number|add:'-3' and num < page_obj.number|add:'3' %}
                    <li class="page-item">
                      <a class="page-link" href="?{% query_transform request page=num %}">{{ num }}</a>
                    </li>
                  {% endif %}
                {% endfor %}

                {% if page_obj.has_next %}
                  <li class="page-item">
                    <a class="page-link" href="?{% query_transform request page=page_obj.next_page_number %}" aria-label="Следующая"><i class="bi bi-chevron-right"></i></a>
                  </li>
                  <li class="page-item">
                    <a class="page-link" href="?{% query_transform request page=page_obj.paginator.num_pages %}" aria-label="Последняя"><i class="bi bi-chevron-double-right"></i></a>
                  </li>
                {% endif %}
              </ul>
            </nav>
          </div>
        </div>
      </div>
    {% endif %}
  </div>
{% endblock %}

{% block extra_js %}
  <script>
    // Дополнительная инициализация для страницы РИД
    document.addEventListener('DOMContentLoaded', function () {
      // Обновление статистики после загрузки
      if (typeof updateIPTableStats === 'function') {
        updateIPTableStats()
      }
    })
  </script>
{% endblock %}

```


-----

# Файл: templates\intellectual_property\components\ip_table.html

```
{% load static %}
{% load common_tags %}

<div class="mb-3">
  <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#columnSelector"><i class="bi bi-layout-three-columns me-1"></i>Настройка колонок</button>
</div>

<div class="collapse mb-3" id="columnSelector">
  <div class="card card-body bg-light">
    <div class="row g-2" id="columnToggle">
      <div class="col-md-3">
        <div class="form-check">
          <input class="form-check-input" type="checkbox" value="type" id="colType" checked />
          <label class="form-check-label" for="colType">Вид РИД</label>
        </div>
      </div>
      <div class="col-md-3">
        <div class="form-check">
          <input class="form-check-input" type="checkbox" value="name" id="colName" checked />
          <label class="form-check-label" for="colName">Наименование</label>
        </div>
      </div>
      <!-- Добавьте остальные колонки по аналогии -->
    </div>
  </div>
</div>

<div class="table-responsive">
  <table class="table table-sm table-hover align-middle mb-0" id="ipTable" style="font-size: 0.85rem;">
    <thead class="table-light">
      <tr>
        <th data-column="type">Вид РИД</th>
        <th data-column="name">Наименование РИД</th>
        <th data-column="year">Год</th>
        <th data-column="regDate">Дата рег.</th>
        <th data-column="owners">Правообладатели</th>
        <th data-column="rightsRF">Права РФ</th>
        <th data-column="docType">Вид док.</th>
        <th data-column="docNumber">Номер док.</th>
        <th data-column="docDate">Дата док.</th>
        <th data-column="appDate">Дата заявки</th>
        <th data-column="authors">Авторы</th>
        <th data-column="secret">Секретность</th>
        <th data-column="licensees">Лицензиаты</th>
        <th data-column="abstract">Реферат</th>
        <th data-column="contacts">Контакты</th>
        <th data-column="status">Статус</th>
        <th data-column="statusDate">Дата статуса</th>
        <th data-column="lang">Языки</th>
        <th data-column="db">СУБД</th>
        <th data-column="volume">Объем</th>
        <th data-column="claims">Формула</th>
        <th data-column="cited">Цитируемые</th>
        <th data-column="expiry">Срок</th>
      </tr>
    </thead>
    <tbody>
      {% for ip in ip_objects %}
        {% include 'intellectual_property/components/ip_table_row.html' with ip=ip %}
      {% empty %}
        <tr>
          <td colspan="23" class="text-center text-muted py-4">
            <i class="bi bi-inbox me-2"></i>Записей не найдено
          </td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% block extra_js %}
  <script src="{% static 'intellectual_property/js/ip_table.js' %}"></script>
{% endblock %}

```


-----

# Файл: templates\intellectual_property\components\ip_table_row.html

```
{# templates/intellectual_property/components/ip_table_row.html #}
{% load static %}
{% load common_tags %}

<tr style="font-size: 0.9rem;">
  <!-- Вид РИД -->
  <td data-column="type">
    <span class="badge bg-light text-dark border" style="font-size: 0.75rem; font-weight: normal; white-space: normal; text-align: left;">{{ ip.ip_type.name|default:'. . .'|truncatechars:25|typus }}</span>
  </td>

  <!-- Наименование РИД с тултипом -->
  <td data-column="name">
    <span title="{{ ip.name|typus }}" style="cursor: help;">{{ ip.name|truncatechars:45|typus }}</span>
  </td>

  <!-- Год создания -->
  <td data-column="year" class="text-center">
    {% if ip.creation_year %}
      <span class="badge bg-secondary bg-opacity-10 text-dark">{{ ip.creation_year }}</span>
    {% else %}
      . . .
    {% endif %}
  </td>

  <!-- Дата регистрации -->
  <td data-column="regDate" class="text-center small">
    {% if ip.registration_date %}
      {{ ip.registration_date|date:'d.m.Y' }}
    {% else %}
      . . .
    {% endif %}
  </td>

  <!-- Правообладатели -->
  <td data-column="owners" style="max-width: 200px;">
    {% with persons=ip.owner_persons.all orgs=ip.owner_organizations.all %}
      {% if persons or orgs %}
        {% for org in orgs|slice:':1' %}
          <span class="d-inline-block" title="{{ org.name }}">
            <i class="bi bi-building text-primary me-1" style="font-size: 0.75rem;"></i>
            {{ org.short_name|default:org.name|truncatechars:25 }}
          </span>
        {% endfor %}

        {% if persons and orgs %}
          <span class="text-muted mx-1">;</span>
        {% endif %}

        {% for person in persons|slice:':1' %}
          <span class="d-inline-block" title="{{ person.get_full_name }}">
            <i class="bi bi-person text-success me-1" style="font-size: 0.75rem;"></i>
            {{ person.get_short_name }}
          </span>
        {% endfor %}

        {% with total=persons|length|add:orgs|length %}
          {% if total > 1 %}
            <span class="text-muted small ms-1">+{{ total|add:'-1' }}</span>
          {% endif %}
        {% endwith %}
      {% else %}
        . . .
      {% endif %}
    {% endwith %}
  </td>

  <!-- Вид охранного документа -->
  <td data-column="docType">
    <span class="small text-muted">{{ ip.ip_type.protection_document_type.name|default:'. . .'|truncatechars:15|typus }}</span>
  </td>

  <!-- Номер охранного документа + ссылка -->
  <td data-column="docNumber">
    {% if ip.publication_url %}
      <a href="{{ ip.publication_url }}" target="_blank" class="text-decoration-none" title="Открыть в реестре ФИПС">
        <i class="bi bi-box-arrow-up-right me-1" style="font-size: 0.7rem;"></i>
        {{ ip.registration_number|default:'. . .'|truncatechars:12 }}
      </a>
    {% else %}
      {{ ip.registration_number|default:'. . .' }}
    {% endif %}
  </td>

  <!-- Дата охранного документа -->
  <td data-column="docDate" class="text-center small">{{ ip.registration_date|date:'d.m.Y'|default:'. . .' }}</td>

  <!-- Дата подачи заявки -->
  <td data-column="appDate" class="text-center small">{{ ip.application_date|date:'d.m.Y'|default:'. . .' }}</td>

  <!-- Авторы -->
  <td data-column="authors" style="max-width: 150px;">
    {% with authors=ip.authors.all %}
      {% if authors %}
        {% for author in authors|slice:':1' %}
          <span title="{{ author.get_full_name }}">
            <i class="bi bi-pencil-square text-secondary me-1" style="font-size: 0.7rem;"></i>
            {{ author.get_short_name }}
          </span>
        {% endfor %}
        {% if authors|length > 1 %}
          <span class="text-muted small ms-1">+{{ authors|length|add:'-1' }}</span>
        {% endif %}
      {% else %}
        . . .
      {% endif %}
    {% endwith %}
  </td>

  <!-- Реферат (иконка с поповером) -->
  <td data-column="abstract" class="text-center">
    {% if ip.abstract %}
      <i class="bi bi-file-text text-info" style="cursor: help; font-size: 1rem;" data-bs-toggle="popover" data-bs-trigger="hover focus" title="Реферат" data-bs-content="{{ ip.abstract|truncatechars:300 }}"></i>
    {% else %}
      . . .
    {% endif %}
  </td>

  <!-- Статус -->
  <td data-column="status" class="text-center">
    {% if ip.actual %}
      <span class="badge bg-success" style="font-size: 0.7rem;">Действует</span>
    {% else %}
      <span class="badge bg-secondary" style="font-size: 0.7rem;">Не действует</span>
    {% endif %}
  </td>

  <!-- Дата изменения статуса -->
  <td data-column="statusDate" class="text-center small">{{ ip.updated_at|date:'d.m.Y'|default:'. . .' }}</td>

  <!-- Языки программирования -->
  <td data-column="lang" class="text-center">
    {% with langs=ip.programming_languages.all %}
      {% if langs %}
        <i class="bi bi-code-square text-primary" style="cursor: help; font-size: 1rem;" data-bs-toggle="popover" data-bs-trigger="hover focus" title="Языки программирования" data-bs-content="{{ langs|join:', ' }}"></i>
      {% else %}
        . . .
      {% endif %}
    {% endwith %}
  </td>

  <!-- СУБД -->
  <td data-column="db" class="text-center">
    {% with dbs=ip.dbms.all %}
      {% if dbs %}
        <i class="bi bi-database text-warning" style="cursor: help; font-size: 1rem;" data-bs-toggle="popover" data-bs-trigger="hover focus" title="СУБД" data-bs-content="{{ dbs|join:', ' }}"></i>
      {% else %}
        . . .
      {% endif %}
    {% endwith %}
  </td>

  <!-- Формула -->
  <td data-column="claims" class="text-center">
    {% if ip.claims %}
      <i class="bi bi-file-earmark-text text-secondary" style="cursor: help; font-size: 1rem;" data-bs-toggle="popover" data-bs-trigger="hover focus" title="Формула" data-bs-content="{{ ip.claims|truncatechars:300 }}"></i>
    {% else %}
      . . .
    {% endif %}
  </td>

  <!-- Срок действия -->
  <td data-column="expiry" class="text-center small">
    {% if ip.expiration_date %}
      <span class="{% if ip.is_expired %}
          
          
          text-danger


        {% else %}
          
          
          text-success


        {% endif %}">
        {{ ip.expiration_date|date:'d.m.Y' }}
      </span>
    {% else %}
      . . .
    {% endif %}
  </td>
</tr>

```


-----

# Файл: views\views_ip_list.py

```
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.core.paginator import Paginator
from django.db import models
import django_filters

from intellectual_property.models import (
    IPObject, Person, Organization, ProgrammingLanguage, 
    DBMS, OperatingSystem, Country, AdditionalPatent, IPImage
)
from intellectual_property.filters import IPObjectFilter

__all__ = (
    'IPObjectListView',
)


class IPObjectListView(LoginRequiredMixin, ListView):
    """Представление для отображения списка РИД."""
    model = IPObject
    template_name = 'intellectual_property/ipobject_list.html'
    context_object_name = 'ip_objects'
    paginate_by = 50

    def get_queryset(self):
        """
        Оптимизация запросов: select_related и prefetch_related для связанных полей.
        """
        queryset = super().get_queryset().select_related(
            'ip_type',
            'ip_type__protection_document_type',
            'paris_convention_priority_country',
        ).prefetch_related(
            # Для авторов
            Prefetch('authors', 
                    queryset=Person.objects.all().only(
                        'ceo_id', 'last_name', 'first_name', 'middle_name', 'ceo'
                    )),
            # Для правообладателей (физ. лица)
            Prefetch('owner_persons', 
                    queryset=Person.objects.all().only(
                        'ceo_id', 'last_name', 'first_name', 'middle_name', 'ceo'
                    )),
            # Для правообладателей (организации)
            Prefetch('owner_organizations', 
                    queryset=Organization.objects.all().only(
                        'organization_id', 'name', 'short_name', 'full_name'
                    )),
            # Для языков программирования
            Prefetch('programming_languages', 
                    queryset=ProgrammingLanguage.objects.all().only('id', 'name')),
            # Для СУБД
            Prefetch('dbms', 
                    queryset=DBMS.objects.all().only('id', 'name')),
            # Для операционных систем
            Prefetch('operating_systems', 
                    queryset=OperatingSystem.objects.all().only('id', 'name')),
            # Для стран первого использования
            Prefetch('first_usage_countries', 
                    queryset=Country.objects.all().only('id', 'name', 'code')),
            # Для дополнительных патентов
            Prefetch('additional_patents', 
                    queryset=AdditionalPatent.objects.all().only('id', 'patent_number', 'patent_date')),
            # Для изображений
            Prefetch('images', 
                    queryset=IPImage.objects.all().only('id', 'image', 'title', 'is_main')),
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем базовый queryset
        base_queryset = self.get_queryset()
        
        # Применяем фильтр
        ip_filter = IPObjectFilter(self.request.GET, queryset=base_queryset)
        filtered_qs = ip_filter.qs
        
        # Пагинация
        paginator = Paginator(filtered_qs, self.paginate_by)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context['filter'] = ip_filter
        context['object_list'] = page_obj.object_list
        context['page_obj'] = page_obj
        context['paginator'] = paginator
        
        return context
```


-----

# Файл: views\__init__.py

```

```
