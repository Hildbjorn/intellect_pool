from django.urls import path
from django.contrib.auth import views as auth_views
from .views import *

# Вход и выход пользователя
urlpatterns = [
    # Вход
    path('login/', auth_views.LoginView.as_view(
        template_name='users/auth/login.html',
        redirect_authenticated_user=True  # Если уже вошел - редирект
    ), name='login'),
    # Вход (Модальное окно)
    path('login-modal/', LoginModalView.as_view(), name='profile_login_modal'),
    # Выход
    path('logout/', auth_views.LogoutView.as_view(
        template_name='users/auth/logout.html'
    ), name='logout'),
]

# Профиль пользователя
urlpatterns += [
    # path('profile/', ProfileUpdateView.as_view(), name='profile'),
    path('profile/<str:tab>/', ProfileUpdateView.as_view(), name='profile')
]

# Все пользователи
urlpatterns += [
    path('all-users/', AllUsersView.as_view(), name='all_users'),
]

# Удаление учетных записей пользователей
urlpatterns += [
    path('profile-delete_confirmation/', ProfileDeleteConfirmation.as_view(), name='profile_delete_confirmation'),
    path('superuser-delete_denied/', SuperuserDeleteDenied.as_view(), name='superuser_delete_denied'),
    path('profile-delete/', ProfileDeleteView.as_view(), name='profile_delete'),
    path('delete-inactive_profiles/', DeleteAllInactiveUsersView.as_view(), name='delete_inactive_profiles'),
]
