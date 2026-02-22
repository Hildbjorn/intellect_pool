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

# Файл: admin\admin_foiv.py

```
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from core.models.models_foiv import FOIV, FOIVType


@admin.register(FOIVType)
class FOIVTypeAdmin(admin.ModelAdmin):
    """
    Админка для типов ФОИВ
    """
    list_display = (
        'foiv_type_id',
        'foiv_type',
        'foiv_type_short',
        'foiv_count',
        'created_at'
    )
    list_display_links = ('foiv_type_id', 'foiv_type')
    search_fields = ('foiv_type', 'foiv_type_short')
    list_filter = ('created_at',)
    ordering = ('foiv_type_id',)
    
    def get_queryset(self, request):
        """Оптимизация запросов с подсчетом количества ФОИВ"""
        return super().get_queryset(request).annotate(
            foiv_count=Count('foivs')
        )
    
    def foiv_count(self, obj):
        """Количество ФОИВ данного типа"""
        count = getattr(obj, 'foiv_count', 0)
        url = reverse('admin:core_foiv_changelist') + f'?foiv_type__id__exact={obj.foiv_type_id}'
        return format_html('<a href="{}">{} органов</a>', url, count)
    foiv_count.short_description = 'Количество ФОИВ'
    foiv_count.admin_order_field = 'foiv_count'


@admin.register(FOIV)
class FOIVAdmin(admin.ModelAdmin):
    """
    Админка для федеральных органов исполнительной власти
    """
    list_display = (
        'sequence_number',
        'short_name_colored',
        'foiv_type',
        'okogu_code',
        'parent_foiv_link',
        'head_info',
        'subordinate_count',
        'is_active',
        'updated_at'
    )
    list_display_links = ('short_name_colored',)
    
    list_filter = (
        'foiv_type',
        'is_active',
        ('parent_foiv', admin.RelatedOnlyFieldListFilter),
        'created_at',
        'updated_at'
    )
    
    search_fields = (
        'short_name',
        'full_name',
        'okogu_code',
        'slug',
        'description'
    )
    
    readonly_fields = (
        'created_at',
        'updated_at',
        'hierarchy_display',
        'subordinate_tree'
    )
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'sequence_number',
                ('short_name', 'full_name'),
                'name_for_sort',
                'slug',
                ('foiv_type', 'okogu_code'),
                'is_active'
            )
        }),
        ('Иерархия', {
            'fields': (
                'parent_foiv',
                'hierarchy_display',
                'subordinate_tree'
            ),
            'classes': ('collapse',)
        }),
        ('Руководство', {
            'fields': (
                ('head_position', 'head'),
            )
        }),
        ('Контакты', {
            'fields': (
                'address',
                'city',
                ('phone', 'email'),
                'website'
            ),
            'classes': ('wide',)
        }),
        ('Дополнительно', {
            'fields': (
                'foundation_date',
                'description'
            ),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    autocomplete_fields = ['parent_foiv', 'head', 'city']
    raw_id_fields = ['head', 'city']
    list_per_page = 25
    save_on_top = True
    actions = ['make_active', 'make_inactive']
    
    # Кастомные методы для отображения
    
    def short_name_colored(self, obj):
        """
        Цветное отображение краткого названия в зависимости от типа
        """
        colors = {
            'Министерство': '#1e3c72',  # темно-синий
            'Федеральная служба': '#2e7d32',  # темно-зеленый
            'Федеральное агентство': '#b85e00'  # оранжево-коричневый
        }
        color = colors.get(str(obj.foiv_type), '#333333')
        
        # Добавляем иконку для неактивных
        if not obj.is_active:
            return format_html(
                '<span style="color: #999; text-decoration: line-through;">{}</span>',
                obj.short_name
            )
        
        return format_html(
            '<span style="color: {}; font-weight: 500;">{}</span>',
            color,
            obj.short_name
        )
    short_name_colored.short_description = 'Краткое наименование'
    short_name_colored.admin_order_field = 'short_name'
    
    def parent_foiv_link(self, obj):
        """
        Ссылка на вышестоящий ФОИВ
        """
        if obj.parent_foiv:
            url = reverse('admin:core_foiv_change', args=[obj.parent_foiv.pk])
            return format_html(
                '<a href="{}">{} [{}]</a>',
                url,
                obj.parent_foiv.short_name,
                obj.parent_foiv.okogu_code
            )
        return format_html('<span style="color: #999;">—</span>')
    parent_foiv_link.short_description = 'Вышестоящий орган'
    parent_foiv_link.admin_order_field = 'parent_foiv__short_name'
    
    def head_info(self, obj):
        """
        Информация о руководителе
        """
        if obj.head:
            url = reverse('admin:core_person_change', args=[obj.head.pk])
            position = f"<br><small>{obj.head_position or 'Должность не указана'}</small>"
            return format_html(
                '<a href="{}">{}</a>{}',
                url,
                obj.head,
                position
            )
        elif obj.head_position:
            return format_html(
                '<span style="color: #666;">{}</span>',
                obj.head_position
            )
        return format_html('<span style="color: #999;">—</span>')
    head_info.short_description = 'Руководитель'
    
    def subordinate_count(self, obj):
        """
        Количество подчиненных органов
        """
        count = obj.subordinate_foivs.count()
        if count > 0:
            url = reverse('admin:core_foiv_changelist') + f'?parent_foiv__id__exact={obj.pk}'
            return format_html(
                '<a href="{}" style="font-weight: 500;">{} подчиненных</a>',
                url,
                count
            )
        return format_html('<span style="color: #999;">0</span>')
    subordinate_count.short_description = 'Подчиненные'
    subordinate_count.admin_order_field = 'subordinate_foivs__count'
    
    def hierarchy_display(self, obj):
        """
        Отображение полной иерархии
        """
        if obj.pk:
            return format_html(
                '<div style="background: #f8f9fa; padding: 10px; border-radius: 4px;">'
                '<strong>Иерархия подчинения:</strong><br>{}'
                '</div>',
                obj.get_full_hierarchy()
            )
        return '-'
    hierarchy_display.short_description = 'Иерархия'
    
    def subordinate_tree(self, obj):
        """
        Древовидное отображение подчиненных органов
        """
        if obj.pk:
            subordinates = obj.subordinate_foivs.all().order_by('sequence_number')
            if subordinates:
                html = ['<div style="background: #f8f9fa; padding: 10px; border-radius: 4px;">']
                html.append('<strong>Подчиненные органы:</strong><ul style="margin-top: 5px;">')
                
                for sub in subordinates:
                    sub_url = reverse('admin:core_foiv_change', args=[sub.pk])
                    html.append(
                        f'<li>'
                        f'<a href="{sub_url}">{sub.short_name}</a> '
                        f'<span style="color: #666;">[{sub.okogu_code}]</span>'
                        f'</li>'
                    )
                    
                    # Добавляем подчиненных второго уровня
                    sub_subordinates = sub.subordinate_foivs.all().order_by('sequence_number')[:5]
                    if sub_subordinates:
                        html.append('<ul style="margin-left: 20px;">')
                        for sub_sub in sub_subordinates:
                            sub_sub_url = reverse('admin:core_foiv_change', args=[sub_sub.pk])
                            html.append(
                                f'<li>'
                                f'<a href="{sub_sub_url}">{sub_sub.short_name}</a> '
                                f'<span style="color: #999;">[{sub_sub.okogu_code}]</span>'
                                f'</li>'
                            )
                        if sub.subordinate_foivs.count() > 5:
                            html.append('<li><em>...</em></li>')
                        html.append('</ul>')
                
                html.append('</ul></div>')
                return format_html(''.join(html))
        return '-'
    subordinate_tree.short_description = 'Дерево подчиненных'
    
    # Actions
    
    def make_active(self, request, queryset):
        """Активировать выбранные ФОИВ"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано {updated} органов')
    make_active.short_description = 'Активировать выбранные органы'
    
    def make_inactive(self, request, queryset):
        """Деактивировать выбранные ФОИВ"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано {updated} органов')
    make_inactive.short_description = 'Деактивировать выбранные органы'
    
    # Переопределение queryset для оптимизации
    
    def get_queryset(self, request):
        """Оптимизация запросов с предзагрузкой связанных объектов"""
        return super().get_queryset(request).select_related(
            'foiv_type', 'parent_foiv', 'head', 'city'
        ).prefetch_related(
            'subordinate_foivs'
        ).annotate(
            subordinate_foivs_count=Count('subordinate_foivs', distinct=True)
        )
    
    # Сохранение с автоматической генерацией полей
    
    def save_model(self, request, obj, form, change):
        """Переопределение сохранения с сообщением"""
        super().save_model(request, obj, form, change)
        if not change:
            self.message_user(
                request,
                f'Орган "{obj.short_name}" успешно создан. Код ОКОГУ: {obj.okogu_code}',
                level='SUCCESS'
            )
    
    # Поиск
    
    def get_search_results(self, request, queryset, search_term):
        """Улучшенный поиск"""
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        
        # Добавляем поиск по коду ОКОГУ с частичным совпадением
        if search_term.isdigit():
            queryset |= self.model.objects.filter(okogu_code__icontains=search_term)
        
        return queryset, use_distinct


class FOIVInline(admin.TabularInline):
    """
    Inline для отображения подчиненных ФОИВ в админке вышестоящего органа
    """
    model = FOIV
    fk_name = 'parent_foiv'
    fields = ['sequence_number', 'short_name', 'okogu_code', 'foiv_type', 'is_active']
    readonly_fields = ['sequence_number', 'short_name', 'okogu_code', 'foiv_type']
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = 'Подчиненный орган'
    verbose_name_plural = 'Подчиненные органы'
    
    def has_add_permission(self, request, obj=None):
        return False
    
```


-----

# Файл: admin\admin_geo.py

```
from django.contrib import admin
from django.utils.html import format_html
from core.models.models_geo import Country, District, Region, City
from common.admin_utils import AdminDisplayMixin


@admin.register(Country)
class CountryAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для стран (ISO 3166)
    """
    search_fields = ['name', 'name_en', 'code', 'code_alpha3']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'name_en', 'code', 'code_alpha3')
        }),
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['name', 'code', 'code_alpha3', 'name_en']


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

# Файл: admin\admin_it.py

```
from django.contrib import admin
from core.models.models_it import ProgrammingLanguage, DBMS, OperatingSystem
from common.admin_utils import AdminDisplayMixin


@admin.register(ProgrammingLanguage)
class ProgrammingLanguageAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для языков программирования
    """
    list_display = ['name', 'id']
    search_fields = ['name']
    readonly_fields = ['id']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name',)
        }),
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['name', 'id']


@admin.register(DBMS)
class DBMSAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для систем управления базами данных
    """
    list_display = ['name', 'id']
    search_fields = ['name']
    readonly_fields = ['id']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name',)
        }),
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['name', 'id']


@admin.register(OperatingSystem)
class OperatingSystemAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для операционных систем
    """
    list_display = ['name', 'id']
    search_fields = ['name']
    readonly_fields = ['id']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name',)
        }),
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['name', 'id']
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

# Файл: fixtures\foiv_data.json

```
[
  {
    "model": "core.FOIVType",
    "pk": 1,
    "fields": {
      "foiv_type": "Министерство",
      "foiv_type_short": "Министерство",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIVType",
    "pk": 2,
    "fields": {
      "foiv_type": "Федеральная служба",
      "foiv_type_short": "Служба",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIVType",
    "pk": 3,
    "fields": {
      "foiv_type": "Федеральное агентство",
      "foiv_type_short": "Агентство",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 1,
    "fields": {
      "sequence_number": 1,
      "short_name": "Минпромторг России",
      "full_name": "Министерство промышленности и торговли Российской Федерации",
      "okogu_code": "1323500",
      "slug": "minpromtorg",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://minpromtorg.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 2,
    "fields": {
      "sequence_number": 2,
      "short_name": "Росстандарт",
      "full_name": "Федеральное агентство по техническому регулированию и метрологии",
      "okogu_code": "1323565",
      "slug": "rostekhregulirovanie",
      "foiv_type": 3,
      "parent_foiv": 1,
      "website": "https://www.rst.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 3,
    "fields": {
      "sequence_number": 3,
      "short_name": "Минпросвещения России",
      "full_name": "Министерство просвещения Российской Федерации",
      "okogu_code": "1323600",
      "slug": "minprosvet",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://edu.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 4,
    "fields": {
      "sequence_number": 4,
      "short_name": "Минвостокразвития России",
      "full_name": "Министерство Российской Федерации по развитию Дальнего Востока и Арктики",
      "okogu_code": "1323700",
      "slug": "minvostokrazvitiya",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://minvr.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 5,
    "fields": {
      "sequence_number": 5,
      "short_name": "Минсельхоз России",
      "full_name": "Министерство сельского хозяйства Российской Федерации",
      "okogu_code": "1325000",
      "slug": "mcx",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://mcx.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 6,
    "fields": {
      "sequence_number": 6,
      "short_name": "Россельхознадзор",
      "full_name": "Федеральная служба по ветеринарному и фитосанитарному надзору",
      "okogu_code": "1325005",
      "slug": "fsvps",
      "foiv_type": 2,
      "parent_foiv": 5,
      "website": "https://fsvps.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 7,
    "fields": {
      "sequence_number": 7,
      "short_name": "Росрыболовство",
      "full_name": "Федеральное агентство по рыболовству",
      "okogu_code": "1325060",
      "slug": "fish.gov",
      "foiv_type": 3,
      "parent_foiv": 5,
      "website": "http://fish.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 8,
    "fields": {
      "sequence_number": 8,
      "short_name": "Минспорт России",
      "full_name": "Министерство спорта Российской Федерации",
      "okogu_code": "1325500",
      "slug": "minsport",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://minsport.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 9,
    "fields": {
      "sequence_number": 9,
      "short_name": "Минстрой России",
      "full_name": "Министерство строительства и жилищно-коммунального хозяйства Российской Федерации",
      "okogu_code": "1325800",
      "slug": "minstroyrf",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://minstroyrf.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 10,
    "fields": {
      "sequence_number": 10,
      "short_name": "Минтранс России",
      "full_name": "Министерство транспорта Российской Федерации",
      "okogu_code": "1326000",
      "slug": "mintrans",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://mintrans.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 11,
    "fields": {
      "sequence_number": 11,
      "short_name": "Ространснадзор",
      "full_name": "Федеральная служба по надзору в сфере транспорта",
      "okogu_code": "1326030",
      "slug": "rostransnadzor",
      "foiv_type": 2,
      "parent_foiv": 10,
      "website": "https://rostransnadzor.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 12,
    "fields": {
      "sequence_number": 12,
      "short_name": "Росавиация",
      "full_name": "Федеральное агентство воздушного транспорта",
      "okogu_code": "1326055",
      "slug": "favt",
      "foiv_type": 3,
      "parent_foiv": 10,
      "website": "https://favt.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 13,
    "fields": {
      "sequence_number": 13,
      "short_name": "Росавтодор",
      "full_name": "Федеральное дорожное агентство",
      "okogu_code": "1326060",
      "slug": "rosavtodor",
      "foiv_type": 3,
      "parent_foiv": 10,
      "website": "https://rosavtodor.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 14,
    "fields": {
      "sequence_number": 14,
      "short_name": "Росжелдор",
      "full_name": "Федеральное агентство железнодорожного транспорта",
      "okogu_code": "1326065",
      "slug": "roszeldor",
      "foiv_type": 3,
      "parent_foiv": 10,
      "website": "https://roszeldor.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 15,
    "fields": {
      "sequence_number": 15,
      "short_name": "Росморречфлот",
      "full_name": "Федеральное агентство морского и речного транспорта",
      "okogu_code": "1326080",
      "slug": "morflot",
      "foiv_type": 3,
      "parent_foiv": 10,
      "website": "https://morflot.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 16,
    "fields": {
      "sequence_number": 16,
      "short_name": "Минтруд России",
      "full_name": "Министерство труда и социальной защиты Российской Федерации",
      "okogu_code": "1326500",
      "slug": "mintrud",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://mintrud.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 17,
    "fields": {
      "sequence_number": 17,
      "short_name": "Роструд",
      "full_name": "Федеральная служба по труду и занятости",
      "okogu_code": "1326510",
      "slug": "rostrud",
      "foiv_type": 2,
      "parent_foiv": 16,
      "website": "https://rostrud.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 18,
    "fields": {
      "sequence_number": 18,
      "short_name": "Минфин России",
      "full_name": "Министерство финансов Российской Федерации",
      "okogu_code": "1327000",
      "slug": "minfin",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://minfin.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 19,
    "fields": {
      "sequence_number": 19,
      "short_name": "ФНС России",
      "full_name": "Федеральная налоговая служба",
      "okogu_code": "1327010",
      "slug": "nalog",
      "foiv_type": 2,
      "parent_foiv": 18,
      "website": "https://nalog.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 20,
    "fields": {
      "sequence_number": 20,
      "short_name": "Федеральная пробирная палата",
      "full_name": "Федеральная пробирная палата (федеральная служба)",
      "okogu_code": "1327013",
      "slug": "assay.gov",
      "foiv_type": 2,
      "parent_foiv": 18,
      "website": "https://probpalata.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 21,
    "fields": {
      "sequence_number": 21,
      "short_name": "Росалкогольтабакконтроль",
      "full_name": "Федеральная служба по контролю за алкогольным и табачным рынками",
      "okogu_code": "1327015",
      "slug": "fsar",
      "foiv_type": 2,
      "parent_foiv": 18,
      "website": "https://fsrar.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 22,
    "fields": {
      "sequence_number": 22,
      "short_name": "ФТС России",
      "full_name": "Федеральная таможенная служба",
      "okogu_code": "1327020",
      "slug": "customs",
      "foiv_type": 2,
      "parent_foiv": 18,
      "website": "https://customs.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 23,
    "fields": {
      "sequence_number": 23,
      "short_name": "Казначейство России",
      "full_name": "Федеральное казначейство (федеральная служба)",
      "okogu_code": "1327035",
      "slug": "roskazna",
      "foiv_type": 2,
      "parent_foiv": 18,
      "website": "https://roskazna.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 24,
    "fields": {
      "sequence_number": 24,
      "short_name": "Росимущество",
      "full_name": "Федеральное агентство по управлению государственным имуществом",
      "okogu_code": "1327080",
      "slug": "rosim",
      "foiv_type": 3,
      "parent_foiv": 18,
      "website": "https://rosim.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 25,
    "fields": {
      "sequence_number": 25,
      "short_name": "Минцифры России",
      "full_name": "Министерство цифрового развития, связи и массовых коммуникаций Российской Федерации",
      "okogu_code": "1327500",
      "slug": "digital",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://digital.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 26,
    "fields": {
      "sequence_number": 26,
      "short_name": "Роскомнадзор",
      "full_name": "Федеральная служба по надзору в сфере связи, информационных технологий и массовых коммуникаций",
      "okogu_code": "1327525",
      "slug": "rkn",
      "foiv_type": 2,
      "parent_foiv": 25,
      "website": "https://rkn.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 27,
    "fields": {
      "sequence_number": 27,
      "short_name": "Минэкономразвития России",
      "full_name": "Министерство экономического развития Российской Федерации",
      "okogu_code": "1328000",
      "slug": "economy",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://economy.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 28,
    "fields": {
      "sequence_number": 28,
      "short_name": "Росаккредитация",
      "full_name": "Федеральная служба по аккредитации",
      "okogu_code": "1328005",
      "slug": "fsa",
      "foiv_type": 2,
      "parent_foiv": 27,
      "website": "https://fsa.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 29,
    "fields": {
      "sequence_number": 29,
      "short_name": "Росстат",
      "full_name": "Федеральная служба государственной статистики",
      "okogu_code": "1328035",
      "slug": "rosstat",
      "foiv_type": 2,
      "parent_foiv": 27,
      "website": "https://rosstat.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 30,
    "fields": {
      "sequence_number": 30,
      "short_name": "Роспатент",
      "full_name": "Федеральная служба по интеллектуальной собственности",
      "okogu_code": "1328040",
      "slug": "rupt",
      "foiv_type": 2,
      "parent_foiv": 27,
      "website": "https://rupto.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 31,
    "fields": {
      "sequence_number": 31,
      "short_name": "Минэнерго России",
      "full_name": "Министерство энергетики Российской Федерации",
      "okogu_code": "1328500",
      "slug": "minenergo",
      "foiv_type": 1,
      "parent_foiv": null,
      "website": "https://minenergo.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 32,
    "fields": {
      "sequence_number": 32,
      "short_name": "ФАС России",
      "full_name": "Федеральная антимонопольная служба",
      "okogu_code": "1330405",
      "slug": "fas",
      "foiv_type": 2,
      "parent_foiv": null,
      "website": "https://fas.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 33,
    "fields": {
      "sequence_number": 33,
      "short_name": "Росреестр",
      "full_name": "Федеральная служба государственной регистрации, кадастра и картографии",
      "okogu_code": "1330411",
      "slug": "rosreestr",
      "foiv_type": 2,
      "parent_foiv": null,
      "website": "https://rosreestr.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 34,
    "fields": {
      "sequence_number": 34,
      "short_name": "Роспотребнадзор",
      "full_name": "Федеральная служба по надзору в сфере защиты прав потребителей и благополучия человека",
      "okogu_code": "1330415",
      "slug": "rospotrebnadzor",
      "foiv_type": 2,
      "parent_foiv": null,
      "website": "https://rospotrebnadzor.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  },
  {
    "model": "core.FOIV",
    "pk": 35,
    "fields": {
      "sequence_number": 35,
      "short_name": "Рособрнадзор",
      "full_name": "Федеральная служба по надзору в сфере образования и науки",
      "okogu_code": "1330429",
      "slug": "obrnadzor",
      "foiv_type": 2,
      "parent_foiv": null,
      "website": "https://obrnadzor.gov.ru/",
      "created_at": "2026-02-22T12:00:00Z",
      "updated_at": "2026-02-22T12:00:00Z"
    }
  }
]
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

# Файл: models\models_foiv.py

```
from django.db import models
from django.utils.text import slugify
from core.models.models_geo import City
from common.utils import TextUtils


class FOIVType(models.Model):
    """
    Тип федерального органа исполнительной власти
    (Министерство, Служба, Агентство)
    """
    foiv_type_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID типа ФОИВ'
    )
    foiv_type = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Тип ФОИВ'
    )
    foiv_type_short = models.CharField(
        max_length=20,
        verbose_name='Краткое обозначение типа',
        help_text='Министерство, Служба, Агентство'
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
        verbose_name = 'Тип ФОИВ'
        verbose_name_plural = 'Типы ФОИВ'
        ordering = ['foiv_type_id']

    def __str__(self):
        return self.foiv_type


class FOIV(models.Model):
    """
    Федеральный орган исполнительной власти (ФОИВ)
    """
    foiv_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='ID ФОИВ'
    )
    
    # Порядковый номер в классификации
    sequence_number = models.PositiveSmallIntegerField(
        verbose_name='Порядковый номер',
        help_text='Номер в таблице ФОИВ'
    )
    
    # Коды и идентификаторы
    okogu_code = models.CharField(
        max_length=20,
        verbose_name='Код ОКОГУ',
        help_text='Буквенный код по классификатору ОКОГУ',
        db_index=True
    )
    
    # Названия
    short_name = models.CharField(
        max_length=200,
        verbose_name='Краткое наименование',
        help_text='Краткое название как в таблице (Минпромторг России)',
        db_index=True
    )
    full_name = models.TextField(
        verbose_name='Полное наименование',
        help_text='Полное официальное наименование'
    )
    name_for_sort = models.CharField(
        max_length=200,
        verbose_name='Наименование для сортировки',
        help_text='Название без кавычек и служебных слов для корректной сортировки',
        blank=True,
        null=True
    )
    
    # URL-идентификаторы
    slug = models.SlugField(
        max_length=220,
        unique=True,
        verbose_name='URL-идентификатор',
        blank=True,
        help_text='Идентификатор для URL (из столбца slug таблицы)'
    )
    
    # Тип ФОИВ
    foiv_type = models.ForeignKey(
        FOIVType,
        on_delete=models.PROTECT,
        related_name='foivs',
        verbose_name='Тип ФОИВ',
        db_column='foiv_type_id',
        null=True,
        blank=True
    )
    
    # Руководство (связь с существующей моделью Person)
    head_position = models.CharField(
        max_length=200,
        verbose_name='Должность руководителя',
        blank=True,
        null=True
    )
    head = models.ForeignKey(
        'core.Person',  # Используем существующую модель Person
        on_delete=models.SET_NULL,
        related_name='headed_foivs',
        verbose_name='Руководитель',
        db_column='head_id',
        null=True,
        blank=True
    )
    
    # Иерархия (подчиненность)
    parent_foiv = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='subordinate_foivs',
        verbose_name='Вышестоящий ФОИВ',
        null=True,
        blank=True,
        db_column='parent_foiv_id'
    )
    
    # Контактная информация
    address = models.TextField(
        verbose_name='Адрес',
        blank=True,
        null=True
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='foivs',
        verbose_name='Город',
        db_column='city_id',
        null=True,
        blank=True
    )
    phone = models.CharField(
        max_length=200,
        verbose_name='Телефон',
        blank=True,
        null=True
    )
    email = models.EmailField(
        max_length=200,
        verbose_name='Email',
        blank=True,
        null=True
    )
    website = models.URLField(
        max_length=500,
        verbose_name='Официальный сайт',
        blank=True,
        null=True
    )
    
    # Дополнительная информация
    foundation_date = models.DateField(
        verbose_name='Дата основания',
        null=True,
        blank=True
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True,
        null=True
    )
    
    # Системные поля
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        db_index=True
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
        verbose_name = 'Федеральный орган исполнительной власти'
        verbose_name_plural = 'Федеральные органы исполнительной власти'
        ordering = ['sequence_number']
        indexes = [
            models.Index(fields=['short_name']),
            models.Index(fields=['okogu_code']),
            models.Index(fields=['sequence_number']),
            models.Index(fields=['foiv_type']),
            models.Index(fields=['parent_foiv']),
        ]
        unique_together = [['okogu_code'], ['sequence_number']]

    def __str__(self):
        return self.short_name

    def save(self, *args, **kwargs):
        # Генерация name_for_sort для правильной сортировки
        if not self.name_for_sort and self.short_name:
            # Убираем кавычки и слова "России", "Федеральное" для сортировки
            name_for_sort = self.short_name
            name_for_sort = name_for_sort.replace('"', '')
            name_for_sort = name_for_sort.replace('России', '').strip()
            name_for_sort = name_for_sort.replace('Федеральная', '')
            name_for_sort = name_for_sort.replace('Федеральное', '')
            name_for_sort = name_for_sort.replace('Федеральный', '')
            self.name_for_sort = name_for_sort.strip()
        
        # Генерация slug, если не указан
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
        
        super().save(*args, **kwargs)

    def get_full_hierarchy(self):
        """
        Возвращает полную иерархию подчиненности
        """
        hierarchy = []
        current = self
        while current:
            hierarchy.append(str(current))
            current = current.parent_foiv
        return " → ".join(reversed(hierarchy))
```


-----

# Файл: models\models_geo.py

```
from django.db import models
from django.utils.text import slugify
from common.utils import TextUtils


class Country(models.Model):
    """
    Справочник стран (ISO 3166)
    """
    name = models.CharField('Название страны', max_length=100)
    name_en = models.CharField('Название на английском', max_length=100, blank=True)
    code = models.CharField('Код (двухбуквенный)', max_length=2, unique=True)
    code_alpha3 = models.CharField('Код (трехбуквенный)', max_length=3, blank=True)

    class Meta:
        verbose_name = 'Страна'
        verbose_name_plural = 'Страны'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


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
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
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
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
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
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
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

from common.utils.text import TextUtils


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
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
        super().save(*args, **kwargs)
```


-----

# Файл: models\models_it.py

```
from django.db import models

class ProgrammingLanguage(models.Model):
    """
    Языки программирования
    """
    name = models.CharField('Название языка', max_length=50, unique=True)

    class Meta:
        verbose_name = 'Язык программирования'
        verbose_name_plural = 'Языки программирования'
        ordering = ['name']

    def __str__(self):
        return self.name


class DBMS(models.Model):
    """
    Системы управления базами данных
    """
    name = models.CharField('Название СУБД', max_length=50, unique=True)

    class Meta:
        verbose_name = 'СУБД'
        verbose_name_plural = 'СУБД'
        ordering = ['name']

    def __str__(self):
        return self.name


class OperatingSystem(models.Model):
    """
    Операционные системы
    """
    name = models.CharField('Название ОС', max_length=50, unique=True)

    class Meta:
        verbose_name = 'Операционная система'
        verbose_name_plural = 'Операционные системы'
        ordering = ['name']

    def __str__(self):
        return self.name
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
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
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
            
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
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
