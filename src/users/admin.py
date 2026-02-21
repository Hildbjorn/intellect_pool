from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from .forms import ProfileCreationForm, ProfileChangeForm
from .models import Profile

from common.admin_utils import AdminImageMixin

@admin.register(Profile)
class ProfileAdmin(AdminImageMixin, UserAdmin):
    add_form = ProfileCreationForm
    form = ProfileChangeForm
    model = Profile
    
    image_field = 'image'
    default_image = 'img/elements/no_photo.webp'

    def get_form(self, request, obj=None, **kwargs):
        # Store request for use in the form if needed
        self.request = request
        return super().get_form(request, obj, **kwargs)

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
    activate_users.short_description = "Активировать выбранных пользователей"
    
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_users.short_description = "Деактивировать выбранных пользователей"
    
    list_display = ('image_tag', 'nic_name', '__str__', 'email', 'phone',
                    'is_staff', 'is_active', 'is_superuser',)
    list_display_links = ('__str__', 'nic_name', 'image_tag', 'email',)
    list_filter = ('email', 'is_staff', 'is_active',)
    fieldsets = (
        ('Учетная запись', {'fields': ('reg_number', 'email', 'password', )}),
        ('Персональные данные', {
         'fields': ('image_thumbnail', 'image', 'nic_name', 'last_name', 'first_name', 'middle_name', 'phone',)}),
        ('Активность', {'fields': (('date_joined', 'last_login'),)}),
        ('Группы', {'fields': ('groups',)}),
        ('Разрешения', {'fields': (('is_active', 'is_staff',
         'is_superuser'), 'user_permissions',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

    search_fields = (
        'nic_name', 'last_name', 'first_name', 'middle_name', 'email', 'phone',)
    ordering = ('last_name', 'first_name',
                'middle_name', 'email', 'nic_name', )
    readonly_fields = ('reg_number', 'image_thumbnail',)
    actions = ['activate_users', 'deactivate_users']


# Кастомизация заголовков и подписей админки
admin.site.site_header = _('База данных РИД')
admin.site.site_title = _('Администрирование РИД')
admin.site.index_title = _('Панель управления')

# Дополнительные настройки для улучшения интерфейса
admin.site.enable_nav_sidebar = True  # Включаем боковую навигацию
