from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from core.models.models_person import Person
from common.admin_utils import AdminDisplayMixin


@admin.register(Person)
class PersonAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для руководителей (физических лиц)
    С поддержкой двусторонней синхронизации ФИО
    """
    list_display = [
        'get_full_name_display',
        'get_short_name_display',
        'organizations_count',
        'created_at_display'
    ]
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
        ('📊 Связанные организации', {
            'fields': ('organizations_count',),
            'classes': ('collapse',)
        }),
        ('⚙️ Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_list_display(self, request):
        """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
        return ['get_full_name_display', 'get_short_name_display', 'organizations_count', 'created_at_display']
    
    def get_queryset(self, request):
        """Оптимизация запросов с подсчетом организаций"""
        return super().get_queryset(request).annotate(
            org_count=Count('organizations')
        )

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

    def organizations_count(self, obj):
        count = getattr(obj, 'org_count', obj.organizations.count())
        if count:
            url = f"{reverse('admin:core_organization_changelist')}?ceo__id__exact={obj.ceo_id}"
            return format_html(
                '<a href="{}" style="font-weight: bold;">{} предприятий</a>',
                url, count
            )
        return format_html('<span style="color: #999;">нет</span>')
    organizations_count.short_description = 'Руководит'
    organizations_count.admin_order_field = 'org_count'
