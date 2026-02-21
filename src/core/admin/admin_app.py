from django.contrib import admin
from django.utils.translation import gettext_lazy as _

# Кастомизация заголовков и подписей админки
admin.site.site_header = _('База данных РИД')
admin.site.site_title = _('Администрирование РИД')
admin.site.index_title = _('Панель управления')

# Дополнительные настройки для улучшения интерфейса
admin.site.enable_nav_sidebar = True  # Включаем боковую навигацию