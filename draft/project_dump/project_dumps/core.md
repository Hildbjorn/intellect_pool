# Файл: apps.py

```
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'База знаний'

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


# Маршруты бвзф знаний
urlpatterns = [
]
```


-----

# Файл: __init__.py

```

```


-----

# Файл: admin\admin_app.py

```
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

# Кастомизация заголовков и подписей админки
admin.site.site_header = _('База данных РИД')
admin.site.site_title = _('Администрирование РИД')
admin.site.index_title = _('Панель управления')

# Дополнительные настройки для улучшения интерфейса
admin.site.enable_nav_sidebar = True  # Включаем боковую навигацию
```


-----

# Файл: admin\admin_geo.py

```
from django.contrib import admin
from django.utils.html import format_html
from core.models.models_geo import District, Region, City
from common.admin_utils import AdminDisplayMixin


@admin.register(District)
class DistrictAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для федеральных округов
    """
    search_fields = ['district', 'district_short']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('district_id', 'district', 'district_short', 'slug')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['district', 'district_short', 'regions_count', 'created_at_display']
    
    def regions_count(self, obj):
        count = obj.regions.count()
        url = f"/admin/core/region/?district__id__exact={obj.district_id}"
        return format_html('<a href="{}">{} регионов</a>', url, count)
    regions_count.short_description = 'Регионов'
    regions_count.admin_order_field = 'regions__count'


@admin.register(Region)
class RegionAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для регионов
    """
    list_filter = ['district']
    search_fields = ['title']
    autocomplete_fields = ['district']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('region_id', 'title', 'district', 'slug')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['title', 'district', 'cities_count', 'created_at_display']
    
    def cities_count(self, obj):
        count = obj.cities.count()
        url = f"/admin/core/city/?region__id__exact={obj.region_id}"
        return format_html('<a href="{}">{} городов</a>', url, count)
    cities_count.short_description = 'Городов'
    cities_count.admin_order_field = 'cities__count'


@admin.register(City)
class CityAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для городов
    """
    list_filter = ['region', 'region__district']
    search_fields = ['city']
    autocomplete_fields = ['region']
    readonly_fields = ['slug', 'created_at', 'updated_at', 'coordinates_display']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('city_id', 'city', 'region', 'slug')
        }),
        ('Координаты', {
            'fields': ('latitude', 'longitude', 'coordinates_display'),
            'classes': ('wide',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['city', 'region', 'coordinates_display', 'created_at_display']
    
    def coordinates_display(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '<span style="white-space: nowrap;">{}°, {}°</span><br>'
                '<a href="https://maps.google.com/?q={},{}" target="_blank" '
                'style="background-color: #f0f0f0; padding: 2px 6px; border-radius: 3px; '
                'text-decoration: none; font-size: 0.9em;">'
                '<i class="fas fa-map-marker-alt"></i> Открыть на карте</a>',
                round(obj.latitude, 6), round(obj.longitude, 6),
                obj.latitude, obj.longitude
            )
        return '-'
    coordinates_display.short_description = 'Координаты'
```


-----

# Файл: admin\admin_industry.py

```
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from core.models.models_industry import Industry
from common.admin_utils import AdminDisplayMixin


@admin.register(Industry)
class IndustryAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для отраслей промышленности
    """
    search_fields = ['industry']
    readonly_fields = ['slug', 'created_at', 'updated_at', 'organizations_count']
    fieldsets = (
        ('Основная информация', {
            'fields': ('industry_id', 'industry', 'slug')
        }),
        ('Статистика', {
            'fields': ('organizations_count',),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['industry', 'organizations_count', 'created_at_display', 'updated_at_display']
    
    def get_queryset(self, request):
        """Оптимизация запросов с подсчетом организаций"""
        return super().get_queryset(request).annotate(
            org_count=Count('organizations')
        )

    def organizations_count(self, obj):
        count = getattr(obj, 'org_count', obj.organizations.count())
        if count:
            url = f"{reverse('admin:core_organization_changelist')}?industry__id__exact={obj.industry_id}"
            return format_html(
                '<a href="{}" style="font-weight: bold;">{} предприятий</a>',
                url, count
            )
        return format_html('<span style="color: #999;">0 предприятий</span>')
    organizations_count.short_description = 'Организации'
    organizations_count.admin_order_field = 'org_count'
```


-----

# Файл: admin\admin_organization.py

```
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from core.models.models_organization import ActivityType, CeoPosition, Organization
from common.admin_utils import AdminDisplayMixin


@admin.register(ActivityType)
class ActivityTypeAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для типов деятельности
    """
    search_fields = ['activity_type']
    readonly_fields = ['created_at', 'updated_at', 'organizations_count']
    fieldsets = (
        ('Основная информация', {
            'fields': ('activity_type_id', 'activity_type')
        }),
        ('Статистика', {
            'fields': ('organizations_count',),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['activity_type', 'organizations_count', 'created_at_display']
    
    def get_queryset(self, request):
        """Оптимизация запросов с подсчетом организаций"""
        return super().get_queryset(request).annotate(
            org_count=Count('organizations')
        )

    def organizations_count(self, obj):
        count = getattr(obj, 'org_count', obj.organizations.count())
        if count:
            url = f"{reverse('admin:core_organization_changelist')}?activity_type__id__exact={obj.activity_type_id}"
            return format_html(
                '<a href="{}" style="font-weight: bold;">{} предприятий</a>',
                url, count
            )
        return format_html('<span style="color: #999;">0 предприятий</span>')
    organizations_count.short_description = 'Предприятий'
    organizations_count.admin_order_field = 'org_count'


@admin.register(CeoPosition)
class CeoPositionAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для должностей руководителей
    """
    search_fields = ['ceo_position']
    readonly_fields = ['created_at', 'updated_at', 'organizations_count']
    fieldsets = (
        ('Основная информация', {
            'fields': ('ceo_position_id', 'ceo_position')
        }),
        ('Статистика', {
            'fields': ('organizations_count',),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['ceo_position', 'organizations_count', 'created_at_display']
    
    def get_queryset(self, request):
        """Оптимизация запросов с подсчетом организаций"""
        return super().get_queryset(request).annotate(
            org_count=Count('organizations')
        )

    def organizations_count(self, obj):
        count = getattr(obj, 'org_count', obj.organizations.count())
        if count:
            url = f"{reverse('admin:core_organization_changelist')}?ceo_position__id__exact={obj.ceo_position_id}"
            return format_html(
                '<a href="{}" style="font-weight: bold;">{} предприятий</a>',
                url, count
            )
        return format_html('<span style="color: #999;">0 предприятий</span>')
    organizations_count.short_description = 'Предприятий'
    organizations_count.admin_order_field = 'org_count'


@admin.register(Organization)
class OrganizationAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для организаций (основная модель)
    """
    list_filter = [
        'industry',
        'activity_type',
        'city__region',
        'register_opk',
        'strategic',
    ]
    
    search_fields = [
        'name',
        'full_name',
        'short_name',
        'okpo',
        'inn',
        'ogrn',
        'address'
    ]
    
    autocomplete_fields = [
        'city',
        'industry',
        'activity_type',
        'ceo_position',
        'ceo',
        'holding_1',
        'holding_2',
        'holding_3'
    ]
    
    readonly_fields = [
        'slug',
        'created_at',
        'updated_at',
        'hierarchy_display',
        'get_full_address',
        'checko_link_display'  # Добавляем в readonly_fields для детальной страницы
    ]
    
    fieldsets = (
        ('🏢 Основная информация', {
            'fields': (
                'organization_id',
                'name',
                ('full_name', 'short_name'),
                'slug'
            )
        }),
        ('🔢 Коды и идентификаторы', {
            'fields': (
                ('okpo', 'ogrn'),
                ('inn', 'kpp'),
                'okato',
                'gisp_catalogue_id',
                'checko_link_display'  # Добавляем ссылку на Чекко в этот блок
            ),
            'classes': ('wide',)
        }),
        ('🏭 Классификация', {
            'fields': (
                'industry',
                'activity_type',
                'activity_description'
            )
        }),
        ('📌 Статусы', {
            'fields': (
                ('register_opk', 'strategic')
            ),
            'classes': ('wide',)
        }),
        ('📍 Местоположение', {
            'fields': (
                'city',
                'address',
                'get_full_address',
                'url'
            ),
            'classes': ('wide',)
        }),
        ('🏛️ Холдинги', {
            'fields': (
                'holding_1',
                'holding_2',
                'holding_3',
                'hierarchy_display'
            ),
            'classes': ('wide',)
        }),
        ('👔 Руководство', {
            'fields': (
                'ceo_position',
                'ceo'
            )
        }),
        ('📞 Контакты', {
            'fields': (
                'email',
                'phone'
            )
        }),
        ('⚙️ Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['short_name', 'city_info', 'industry_info', 'ceo_info', 
                'strategic_badge', 'register_opk_badge', 'checko_link']  # Добавляем ссылку на Чекко
    
    def get_queryset(self, request):
        """Оптимизация запросов с select_related"""
        return super().get_queryset(request).select_related(
            'city',
            'city__region',
            'industry',
            'activity_type',
            'ceo_position',
            'ceo',
            'holding_1',
            'holding_2',
            'holding_3'
        )

    def city_info(self, obj):
        if obj.city:
            city_name = obj.city.city
            region_name = obj.city.region.title if obj.city.region else ''
            return format_html(
                '{}<br><small style="color: #666;">{}</small>',
                city_name,
                region_name
            )
        return '-'
    city_info.short_description = 'Город'
    city_info.admin_order_field = 'city__city'

    def industry_info(self, obj):
        if obj.industry:
            return format_html(
                '<span title="{}">{}</span>',
                obj.activity_description or '',
                obj.industry
            )
        return '-'
    industry_info.short_description = 'Отрасль'
    industry_info.admin_order_field = 'industry__industry'

    def ceo_info(self, obj):
        if obj.ceo:
            ceo_short = obj.ceo.get_short_name()
            if obj.ceo_position:
                return format_html(
                    '{}<br><small style="color: #666;">{}</small>',
                    ceo_short,
                    obj.ceo_position
                )
            return ceo_short
        return '-'
    ceo_info.short_description = 'Руководитель'
    ceo_info.admin_order_field = 'ceo__last_name'

    def strategic_badge(self, obj):
        if obj.strategic:
            return format_html(
                '<span style="background-color: #28a745; padding: 3px 7px; '
                'border-radius: 10px; color: #fff; font-weight: bold; white-space: nowrap;">★ Стратег.</span>'
            )
        return '-'
    strategic_badge.short_description = 'Стратегическое'
    strategic_badge.admin_order_field = 'strategic'

    def register_opk_badge(self, obj):
        if obj.register_opk:
            return format_html(
                '<span style="background-color: #17a2b8; padding: 3px 7px; '
                'border-radius: 10px; color: #fff; font-weight: bold; white-space: nowrap;">✅ Реестр ОПК</span>'
            )
        return '-'
    register_opk_badge.short_description = 'Реестр ОПК'
    register_opk_badge.admin_order_field = 'register_opk'

    def hierarchy_display(self, obj):
        """Отображение иерархии холдингов"""
        hierarchy = []
        if obj.holding_3:
            hierarchy.append(f"Уровень 3: {obj.holding_3.name}")
        if obj.holding_2:
            hierarchy.append(f"Уровень 2: {obj.holding_2.name}")
        if obj.holding_1:
            hierarchy.append(f"Уровень 1: {obj.holding_1.name}")
        
        if hierarchy:
            return format_html(
                '<div style="line-height: 1.6;">{}</div>',
                '<br>'.join(hierarchy)
            )
        return "Не входит в холдинги"
    hierarchy_display.short_description = 'Иерархия холдингов'

    def get_full_address(self, obj):
        """Формирует полный адрес с городом и регионом"""
        parts = []
        if obj.city:
            if obj.city.region:
                parts.append(obj.city.region.title)
            parts.append(f"г. {obj.city.city}")
        if obj.address:
            parts.append(obj.address)
        
        if parts:
            return ', '.join(parts)
        return '-'
    get_full_address.short_description = 'Полный адрес'

    def checko_link(self, obj):
        """Создает ссылку на страницу организации на портале Чекко"""
        if obj.ogrn:
            url = f"https://checko.ru/company/{obj.ogrn}"
            return format_html(
                '<a href="{}" target="_blank" style="display: inline-block; background-color: #007bff; color: #fff; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 0.85em; white-space: nowrap;">🔍 Чекко</a>',
                url
            )
        return format_html('<span style="color: #999;">—</span>')
    checko_link.short_description = 'Чекко'

    def checko_link_display(self, obj):
        """Отображение ссылки на Чекко в детальной странице"""
        if obj.ogrn:
            url = f"https://checko.ru/company/{obj.ogrn}"
            return format_html(
                '<a href="{}" target="_blank" style="display: inline-block; background-color: #007bff; color: #fff; padding: 5px 12px; border-radius: 4px; text-decoration: none; font-weight: bold;white-space: nowrap;">🔍 Открыть на Чекко</a>',
                url
            )
        return "ОГРН не указан"
    checko_link_display.short_description = 'Ссылка на Чекко'

    # Кастомные действия
    actions = ['mark_as_strategic', 'mark_as_opk', 'export_selected']

    @admin.action(description='✅ Отметить как стратегические')
    def mark_as_strategic(self, request, queryset):
        updated = queryset.update(strategic=True)
        self.message_user(request, f'{updated} организаций отмечены как стратегические')

    @admin.action(description='✅ Включить в реестр ОПК')
    def mark_as_opk(self, request, queryset):
        updated = queryset.update(register_opk=True)
        self.message_user(request, f'{updated} организаций включены в реестр ОПК')

    @admin.action(description='📤 Экспортировать выбранные')
    def export_selected(self, request, queryset):
        """Простой экспорт в CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="organizations.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Название', 'ИНН', 'ОГРН', 'Город', 
            'Отрасль', 'Руководитель', 'Телефон', 'Email', 'Ссылка Чекко'
        ])
        
        for org in queryset.select_related('city', 'industry', 'ceo'):
            checko_url = f"https://checko.ru/company/{org.ogrn}" if org.ogrn else ''
            writer.writerow([
                org.organization_id,
                org.name,
                org.inn or '',
                org.ogrn or '',
                org.city.city if org.city else '',
                org.industry.industry if org.industry else '',
                org.ceo.get_short_name() if org.ceo else '',
                org.phone or '',
                org.email or '',
                checko_url
            ])
        
        return response
```


-----

# Файл: admin\admin_person.py

```
from django.contrib import admin
from core.models.models_person import Person
from common.admin_utils import AdminDisplayMixin


@admin.register(Person)
class PersonAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для руководителей (физических лиц)
    С поддержкой двусторонней синхронизации ФИО
    """
    list_filter = ['organizations__industry']
    search_fields = [
        'last_name', 
        'first_name', 
        'middle_name', 
        'ceo'
    ]
    readonly_fields = [
        'slug', 
        'created_at', 
        'updated_at', 
        'get_initials_display',
        'get_full_name_display',
        'get_short_name_display'
    ]
    
    fieldsets = (
        ('👤 Основная информация', {
            'fields': (
                'ceo_id',
                ('last_name', 'first_name', 'middle_name'),
                'ceo',
                ('get_full_name_display', 'get_short_name_display', 'get_initials_display'),
                'slug'
            ),
            'description': 'Заполните либо составные поля, либо полное ФИО — они синхронизируются автоматически'
        }),
        ('⚙️ Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['get_full_name_display', 'get_short_name_display', 'created_at_display']
    
    def get_full_name_display(self, obj):
        return obj.get_full_name()
    get_full_name_display.short_description = 'Полное ФИО'
    get_full_name_display.admin_order_field = 'ceo'

    def get_short_name_display(self, obj):
        return obj.get_short_name()
    get_short_name_display.short_description = 'Сокращенно'

    def get_initials_display(self, obj):
        return obj.get_initials()
    get_initials_display.short_description = 'Инициалы'
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

# Файл: models\models_geo.py

```
from django.db import models
from django.utils.text import slugify
from common.utils import TextUtils


class District(models.Model):
    """
    Федеральный округ
    """
    district_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID округа'
    )
    district = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Федеральный округ'
    )
    district_short = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Аббревиатура',
        help_text='Например: ЦФО, СЗФО'
    )
    slug = models.SlugField(
        max_length=120,
        unique=True,
        verbose_name='URL-идентификатор',
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Федеральный округ'
        verbose_name_plural = 'Федеральные округа'
        ordering = ['district']

    def __str__(self):
        return f"{self.district} ({self.district_short})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.district)[:120]
        super().save(*args, **kwargs)


class Region(models.Model):
    """
    Регион/область/республика/край
    """
    region_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID региона'
    )
    title = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Регион'
    )
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name='regions',
        verbose_name='Федеральный округ',
        db_column='district_id'
    )
    slug = models.SlugField(
        max_length=120,
        unique=True,
        verbose_name='URL-идентификатор',
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:120]
        super().save(*args, **kwargs)


class City(models.Model):
    """
    Город/населенный пункт
    """
    city_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='ID города'
    )
    city = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name='Город'
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name='cities',
        verbose_name='Регион',
        db_column='region_id'
    )
    latitude = models.FloatField(
        verbose_name='Широта',
        blank=True,
        null=True
    )
    longitude = models.FloatField(
        verbose_name='Долгота',
        blank=True,
        null=True
    )
    slug = models.SlugField(
        max_length=170,
        unique=True,
        verbose_name='URL-идентификатор',
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'
        ordering = ['city']
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['region', 'city']),
        ]

    def __str__(self):
        return f"{self.city}, {self.region.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.city}-{self.region_id}")
            self.slug = TextUtils.unique_slugify(
                City,
                base_slug,
                slug_field='slug'
            )[:170]
        super().save(*args, **kwargs)

    def get_coordinates(self):
        """Возвращает кортеж (широта, долгота)"""
        if self.latitude and self.longitude:
            return (self.latitude, self.longitude)
        return None
```


-----

# Файл: models\models_industry.py

```
from django.db import models
from django.utils.text import slugify


class Industry(models.Model):
    """
    Отрасль промышленности (например: Авиационная, Судостроительная и т.д.)
    """
    industry_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID отрасли'
    )
    industry = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Отрасль'
    )
    slug = models.SlugField(
        max_length=120,
        unique=True,
        verbose_name='URL-идентификатор',
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Отрасль промышленности'
        verbose_name_plural = 'Отрасли промышленности'
        ordering = ['industry']

    def __str__(self):
        return self.industry

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.industry)[:120]
        super().save(*args, **kwargs)
```


-----

# Файл: models\models_organization.py

```
from django.db import models
from django.utils.text import slugify
from core.models.models_geo import City
from core.models.models_industry import Industry
from core.models.models_person import Person
from common.utils import TextUtils


class ActivityType(models.Model):
    """
    Тип деятельности предприятия (Промышленное, Научное, Прочее)
    """
    activity_type_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID типа деятельности'
    )
    activity_type = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Тип деятельности'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Тип деятельности'
        verbose_name_plural = 'Типы деятельности'
        ordering = ['activity_type_id']

    def __str__(self):
        return self.activity_type


class CeoPosition(models.Model):
    """
    Должность руководителя (Генеральный директор, Директор и т.д.)
    """
    ceo_position_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID должности'
    )
    ceo_position = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Должность'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Должность руководителя'
        verbose_name_plural = 'Должности руководителей'
        ordering = ['ceo_position_id']

    def __str__(self):
        return self.ceo_position


class Organization(models.Model):
    """
    Предприятие/организация (основная модель)
    """
    organization_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='ID организации'
    )
    
    # Коды и идентификаторы
    okpo = models.CharField(
        max_length=20,
        verbose_name='ОКПО',
        blank=True,
        null=True,
        db_index=True
    )
    ogrn = models.CharField(
        max_length=20,
        verbose_name='ОГРН',
        blank=True,
        null=True,
        db_index=True
    )
    inn = models.CharField(
        max_length=20,
        verbose_name='ИНН',
        blank=True,
        null=True,
        db_index=True
    )
    kpp = models.CharField(
        max_length=20,
        verbose_name='КПП',
        blank=True,
        null=True
    )
    okato = models.CharField(
        max_length=20,
        verbose_name='ОКАТО',
        blank=True,
        null=True
    )
    
    # Названия
    name = models.CharField(
        max_length=500,
        verbose_name='Краткое название',
        help_text='Название как в первой колонке'
    )
    full_name = models.TextField(
        verbose_name='Полное название',
        blank=True,
        null=True
    )
    short_name = models.CharField(
        max_length=500,
        verbose_name='Сокращенное название',
        blank=True,
        null=True
    )
    
    # Связи
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='Город',
        db_column='city_id',
        null=True,
        blank=True
    )
    address = models.TextField(
        verbose_name='Адрес',
        blank=True,
        null=True
    )
    url = models.URLField(
        max_length=500,
        verbose_name='Сайт',
        blank=True,
        null=True
    )
    
    # Холдинги (самоссылающиеся связи)
    holding_1 = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='subsidiaries_1',
        verbose_name='Холдинг 1 уровня',
        null=True,
        blank=True,
        db_column='holding_1_id'
    )
    holding_2 = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='subsidiaries_2',
        verbose_name='Холдинг 2 уровня',
        null=True,
        blank=True,
        db_column='holding_2_id'
    )
    holding_3 = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='subsidiaries_3',
        verbose_name='Холдинг 3 уровня',
        null=True,
        blank=True,
        db_column='holding_3_id'
    )
    
    # Классификаторы
    industry = models.ForeignKey(
        Industry,
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='Отрасль',
        db_column='industry_id',
        null=True,
        blank=True
    )
    activity_type = models.ForeignKey(
        ActivityType,
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='Тип деятельности',
        db_column='activity_type_id',
        null=True,
        blank=True
    )
    activity_description = models.TextField(
        verbose_name='Описание деятельности',
        blank=True,
        null=True
    )
    
    # Регистрационные флаги
    register_opk = models.BooleanField(
        default=False,
        verbose_name='Реестр ОПК',
        help_text='Находится в реестре организаций ОПК',
        db_index=True
    )
    strategic = models.BooleanField(
        default=False,
        verbose_name='Стратегическое предприятие',
        help_text='Входит в перечень стратегических предприятий (Распоряжение Правительства РФ)',
        db_index=True
    )
    
    # Контактная информация
    email = models.EmailField(
        max_length=200,
        verbose_name='Email',
        blank=True,
        null=True
    )
    phone = models.CharField(
        max_length=200,
        verbose_name='Телефон',
        blank=True,
        null=True
    )
    
    # Руководство
    ceo_position = models.ForeignKey(
        CeoPosition,
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='Должность руководителя',
        db_column='ceo_position_id',
        null=True,
        blank=True
    )
    ceo = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='Руководитель',
        db_column='ceo_id',
        null=True,
        blank=True
    )
    
    # Дополнительные идентификаторы
    gisp_catalogue_id = models.CharField(
        max_length=50,
        verbose_name='ID каталога ГИСП',
        blank=True,
        null=True,
        db_index=True
    )
    
    # Системные поля
    slug = models.SlugField(
        max_length=520,
        unique=True,
        verbose_name='URL-идентификатор',
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['city', 'industry']),
            models.Index(fields=['register_opk']),
            models.Index(fields=['strategic']),
            models.Index(fields=['okpo']),
            models.Index(fields=['inn']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = TextUtils.unique_slugify(
                Organization,
                slugify(self.name)[:500],
                slug_field='slug'
            )[:520]
        super().save(*args, **kwargs)

    def get_full_hierarchy(self):
        """Возвращает полную иерархию холдингов"""
        hierarchy = []
        if self.holding_3:
            hierarchy.append(str(self.holding_3))
        if self.holding_2:
            hierarchy.append(str(self.holding_2))
        if self.holding_1:
            hierarchy.append(str(self.holding_1))
        hierarchy.append(str(self))
        return " → ".join(hierarchy)

    def get_strategic_status_display(self):
        """Возвращает статус стратегического предприятия"""
        if self.strategic_1009:
            return "Стратегическое (1009-р)"
        elif self.strategic:
            return "Стратегическое"
        return "Не стратегическое"
```


-----

# Файл: models\models_person.py

```
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from common.utils import TextUtils


class Person(models.Model):
    """
    Физическое лицо (руководитель предприятия)
    С двусторонней синхронизацией полей ФИО
    """
    ceo_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='ID руководителя'
    )
    ceo = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='ФИО полностью',
        help_text='Фамилия Имя Отчество (заполняется автоматически или вручную)',
        blank=True,
        null=True
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name='Фамилия',
        db_index=True,
        blank=True,
        null=True
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name='Имя',
        db_index=True,
        blank=True,
        null=True
    )
    middle_name = models.CharField(
        max_length=100,
        verbose_name='Отчество',
        blank=True,
        null=True
    )
    slug = models.SlugField(
        max_length=220,
        unique=True,
        verbose_name='URL-идентификатор',
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Руководитель'
        verbose_name_plural = 'Руководители'
        ordering = ['last_name', 'first_name', 'middle_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['ceo']),
        ]

    def __str__(self):
        return self.get_full_name()

    def clean(self):
        """Валидация данных"""
        super().clean()
        
        # Проверяем, что хотя бы одна группа полей заполнена
        if not self.ceo and not (self.last_name or self.first_name):
            raise ValidationError(
                'Необходимо заполнить либо поле "ФИО полностью", '
                'либо поля "Фамилия" и "Имя"'
            )

    def _parse_full_name(self):
        """Разбирает полное ФИО на составные части"""
        if not self.ceo:
            return
        
        # Убираем лишние пробелы
        full_name = ' '.join(self.ceo.strip().split())
        parts = full_name.split()
        
        if len(parts) >= 1:
            self.last_name = parts[0]
        if len(parts) >= 2:
            self.first_name = parts[1]
        if len(parts) >= 3:
            # Объединяем остаток в отчество (на случай, если отчество составное)
            self.middle_name = ' '.join(parts[2:])
        else:
            self.middle_name = None

    def _build_full_name(self):
        """Собирает полное ФИО из составных частей"""
        parts = []
        if self.last_name:
            parts.append(self.last_name.strip())
        if self.first_name:
            parts.append(self.first_name.strip())
        if self.middle_name:
            parts.append(self.middle_name.strip())
        
        if parts:
            self.ceo = ' '.join(parts)
        else:
            self.ceo = None

    def save(self, *args, **kwargs):
        """
        Переопределенный save с двусторонней синхронизацией:
        1. Если есть ceo, но нет составных частей - разбираем ceo
        2. Если есть составные части, но нет ceo - собираем ceo
        3. Если есть и то и другое - проверяем соответствие
        4. Если заполнены оба набора, но они не соответствуют друг другу - приоритет у составных частей
        """
        # Очищаем строки от лишних пробелов
        if self.ceo:
            self.ceo = ' '.join(self.ceo.strip().split())
        if self.last_name:
            self.last_name = self.last_name.strip()
        if self.first_name:
            self.first_name = self.first_name.strip()
        if self.middle_name:
            self.middle_name = self.middle_name.strip()

        # Случай 1: Заполнено только полное ФИО
        if self.ceo and not (self.last_name or self.first_name):
            self._parse_full_name()
        
        # Случай 2: Заполнены только составные части
        elif (self.last_name or self.first_name) and not self.ceo:
            self._build_full_name()
        
        # Случай 3: Заполнены оба набора - проверяем соответствие
        elif self.ceo and (self.last_name or self.first_name):
            # Временно собираем ФИО из составных частей для сравнения
            temp_parts = []
            if self.last_name:
                temp_parts.append(self.last_name)
            if self.first_name:
                temp_parts.append(self.first_name)
            if self.middle_name:
                temp_parts.append(self.middle_name)
            
            constructed_ceo = ' '.join(temp_parts) if temp_parts else None
            
            # Если собранное ФИО отличается от сохраненного,
            # приоритет у составных частей
            if constructed_ceo and constructed_ceo != self.ceo:
                self.ceo = constructed_ceo

        # Генерируем slug, если его нет
        if not self.slug:
            # Для slug используем составные части или разбираем ceo
            if self.last_name and self.first_name:
                base = f"{self.last_name}-{self.first_name}"
                if self.middle_name:
                    base += f"-{self.middle_name}"
            elif self.ceo:
                # Разбираем ceo для slug
                temp_parts = self.ceo.split()
                base = '-'.join(temp_parts)
            else:
                base = f"person-{self.ceo_id}"
            
            self.slug = TextUtils.unique_slugify(
                Person,
                slugify(base)[:200],
                slug_field='slug'
            )[:220]

        super().save(*args, **kwargs)

    def get_short_name(self):
        """Возвращает сокращенное ФИО (Иванов И.И.)"""
        if self.last_name:
            short = self.last_name
            if self.first_name:
                short += f" {self.first_name[0]}."
            if self.middle_name:
                short += f" {self.middle_name[0]}."
            return short
        elif self.ceo:
            # Если нет составных частей, но есть ceo - пробуем разобрать на лету
            parts = self.ceo.split()
            if len(parts) >= 1:
                short = parts[0]
                if len(parts) >= 2:
                    short += f" {parts[1][0]}."
                if len(parts) >= 3:
                    short += f" {parts[2][0]}."
                return short
        return self.ceo or ""

    def get_full_name(self):
        """Возвращает полное ФИО"""
        if self.ceo:
            return self.ceo
        return self._build_full_name() or ""

    def get_initials(self):
        """Возвращает инициалы (И.И. Иванов)"""
        initials = []
        if self.first_name:
            initials.append(self.first_name[0].upper())
        if self.middle_name:
            initials.append(self.middle_name[0].upper())
        
        if initials and self.last_name:
            return f"{'.'.join(initials)}. {self.last_name}"
        elif self.ceo:
            parts = self.ceo.split()
            if len(parts) >= 3:
                return f"{parts[1][0]}.{parts[2][0]}. {parts[0]}"
            elif len(parts) == 2:
                return f"{parts[1][0]}. {parts[0]}"
            return parts[0]
        return ""
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

# Файл: views\views_page_not_found.py

```
from django.shortcuts import render


__all__ = (
    'page_not_found_view',
)


def page_not_found_view(request, exception):
   """
   Функция обработки ошибки 404 (страница не найдена).
   """
   return render(request, '404.html', status=404)
```


-----

# Файл: views\__init__.py

```
import os
import glob

# Автоматически импортируем все views из файлов в папке
views_files = glob.glob(os.path.dirname(__file__) + "/*.py")
for module in views_files:
    if not module.endswith('__init__.py'):
        module_name = os.path.basename(module)[:-3]
        exec(f"from .{module_name} import *")
```
