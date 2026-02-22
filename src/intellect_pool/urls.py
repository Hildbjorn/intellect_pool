"""
Настройки маршрутов проекта Intellect Pool
Copyright (c) 2026 Artem Fomin
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from django.conf import settings

urlpatterns = [
    # маршрут к админке Django
    path('admin/', admin.site.urls),
    # маршрут к пользователям
    path('users/', include('users.urls')),
    # маршрут к главной странице
    path('', include('home.urls')),
    # маршрут к результатам интеллектуальной деятельности
    path('intellectual_property', include('intellectual_property.urls')),
]

# добавление маршрута к медиафайлам в режиме отладки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
# добавление маршрута к медиафайлам
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# urls аутентификации сайта Django (для входа, выхода, управления паролями)
urlpatterns += [
    path('accounts/', include('django.contrib.auth.urls')),
]

# обработчик ошибки 404
handler404 = "core.views.src/views_page_not_found.page_not_found_view"
