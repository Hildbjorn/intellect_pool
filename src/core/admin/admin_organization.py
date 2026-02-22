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