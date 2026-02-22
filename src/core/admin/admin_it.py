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