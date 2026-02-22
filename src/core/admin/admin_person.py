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