# Файл: admin.py

```
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



```


-----

# Файл: apps.py

```
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Пользователи'

```


-----

# Файл: forms.py

```
import json
import re
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms

from .models import Profile

class ProfileCreationForm(UserCreationForm):
    email = forms.EmailField(label='E-mail:',
                             required=True,
                             widget=forms.TextInput(attrs={'id': 'id_username',
                                                           'class': 'form-control floating',
                                                           'aria-describedby': 'emailHelp'}),)

    password1 = forms.CharField(label='Пароль:',
                                strip=False,
                                widget=forms.PasswordInput(attrs={'class': 'form-control floating',
                                                                  'autocomplete': 'new-password',
                                                                  'aria-describedby': 'password1Help'}),
                                help_text=password_validation.password_validators_help_text_html(),)
    
    password2 = forms.CharField(label='Пароль еще раз:',
                                widget=forms.PasswordInput(attrs={'class': 'form-control floating',
                                                                  'autocomplete': 'new-password',
                                                                  'aria-describedby': 'password2Help'}),
                                strip=False,
                                help_text="Введите тот же пароль, что ввели выше.",)
    
    is_staff = forms.BooleanField(required=False,
                                  label='В команде',
                                  widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    is_active = forms.BooleanField(required=False,
                                   label='Активный',
                                   widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        # Если nic_name не задан и есть email
        if not user.nic_name and user.email:
            base_nic_name = user.email.split('@')[0]
            user.nic_name = re.sub(r'[^a-zA-Z0-9]', '', base_nic_name).upper()
            # Проверка на уникальность
            original_nic_name = user.nic_name
            counter = 1
            while Profile.objects.filter(nic_name=user.nic_name).exists():
                # Формируем новое имя с порядковым номером
                user.nic_name = f"{original_nic_name}_{counter:03}"
                counter += 1
        if commit:
            user.save()
        return user

    
    class Meta:
        model = Profile
        fields = ('email', 'password1', 'password2', 'is_staff', 'is_active')


class ProfileChangeForm(UserChangeForm):
    """
    Форма изменения пользователя.
    """

    class Meta:
        model = Profile
        fields = ('email',)
        widgets = {
            'groups': forms.CheckboxSelectMultiple,
            'user_permissions': forms.CheckboxSelectMultiple,
        }


class ProfileUpdateForm(forms.ModelForm):
    """
    Форма обновления данных пользователя в модели Profile.
    """

    nic_name = forms.CharField(required=False,
                               label='Псевдоним:',
                               widget=forms.TextInput(attrs={'class': 'form-control floating',
                                                             'id': 'nic_name',
                                                             'placeholder': 'Псевдоним'}))

    last_name = forms.CharField(required=False,
                                label='Фамилия:',
                                widget=forms.TextInput(attrs={'class': 'form-control floating',
                                                              'id': 'last_name',
                                                              'placeholder': 'Фамилия'}))

    first_name = forms.CharField(required=False,
                                 label='Имя:',
                                 widget=forms.TextInput(attrs={'class': 'form-control floating',
                                                               'id': 'first_name',
                                                               'placeholder': 'Имя'}))

    middle_name = forms.CharField(required=False,
                                  label='Отчество:',
                                  widget=forms.TextInput(attrs={'class': 'form-control floating',
                                                                'id': 'middle_name',
                                                                'placeholder': 'Отчество'}))

    image = forms.ImageField(required=False,
                              label='Аватар:',
                              widget=forms.FileInput(attrs={'class': 'form-control form-control-sm field_hidden',
                                                            'id': 'image_field',
                                                            'accept': '.jpg, .png, .gif',
                                                            'type': 'file'}))

    phone = forms.CharField(required=False,
                            label='Телефон:',
                            widget=forms.TextInput(attrs={'class': 'tel form-control floating',
                                                          'id': 'phone',
                                                          'placeholder': 'Телефон'}))

    email = forms.EmailField(label='E-mail:',
                             required=True,
                             widget=forms.TextInput(attrs={'class': 'form-control floating',
                                                           'id': 'email',
                                                           'placeholder': 'user@mail.ru'}),
                             error_messages={'unique': ("Пользователь с таким e-mail уже зарегистрирован"),
                                             'invalid': ("Введите корректное значение")})

    class Meta:
        model = Profile
        fields = (
            'nic_name',
            'last_name',
            'first_name',
            'middle_name',
            'image',
            'phone',
            'email',
        )

    def clean_nic_name(self):
        nic_name = self.cleaned_data.get('nic_name')
        upper_nic_name = nic_name.upper()
        # Проверяем, если форма редактирует существующий объект
        if self.instance.pk:  # Если объект существует (редактирование)
            # Проверяем, существует ли другой объект с таким же ником
            if Profile.objects.filter(nic_name=upper_nic_name).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(
                    f"Ник '{nic_name}' уже существует.")
        else:  # Если это создание нового объекта
            if Profile.objects.filter(nic_name=upper_nic_name).exists():
                raise forms.ValidationError(
                    f"Ник '{nic_name}' уже существует.")

        return nic_name

```


-----

# Файл: managers.py

```
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class ProfileManager(BaseUserManager):
    """
    Доработанная модель пользователя, в которой e-mail является уникальным идентификатором
    для авторизации вместо имени пользователя
    """

    def create_user(self, email, password, **extra_fields):
        """
        Создание и сохранение пользователя, используя e-mail и пароль.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    
    def create_superuser(self, email, password, **extra_fields):
        """
        Создание и сохранение суперпользователя, используя e-mail и пароль
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

```


-----

# Файл: models.py

```
import os
import re
import logging
import shutil
import uuid
from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from common.utils.files import FileUtils

from .managers import ProfileManager

# Create your models here.
class Profile(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('E-mail'), unique=True)

    reg_number = models.UUIDField(default=uuid.uuid4,
                                  editable=False,
                                  unique=True,
                                  verbose_name='Регистрационный номер')

    nic_name = models.CharField(max_length=100,
                                verbose_name='Псевдоним',
                                null=True,
                                blank=True)

    dir_name = "avatar"
    image = models.ImageField(upload_to=FileUtils.generate_file_path,
                               null=True,
                               blank=True,
                               verbose_name='Аватар')
    max_size = (300, 300)

    first_name = models.CharField(max_length=100,
                                  verbose_name='Имя',
                                  null=True,
                                  blank=True)

    middle_name = models.CharField(max_length=100,
                                   verbose_name='Отчество',
                                   null=True,
                                   blank=True)

    last_name = models.CharField(max_length=100,
                                 verbose_name='Фамилия',
                                 null=True,
                                 blank=True)

    phone = models.CharField(max_length=20,
                             unique=False,
                             null=True,
                             blank=True,
                             verbose_name='Телефон',
                             db_index=True)

    is_staff = models.BooleanField(default=False,
                                   verbose_name='В команде')

    is_active = models.BooleanField(default=False,
                                    verbose_name='Активный')

    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = ProfileManager()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Если nic_name не задан и есть email
        if not self.nic_name and self.email:
            base_nic_name = self.email.split('@')[0]
            self.nic_name = re.sub(r'[^a-zA-Z0-9]', '', base_nic_name).upper()
            # Проверка на уникальность
            original_nic_name = self.nic_name
            counter = 1
            while Profile.objects.filter(nic_name=self.nic_name).exists():
                # Формируем новое имя с порядковым номером
                self.nic_name = f"{original_nic_name}_{counter:03}"
                counter += 1
            super().save(*args, **kwargs)
        # Проверяем наличие аватара
        if self.image:
            # Обрабатываем изображение
            try:
                FileUtils.resize_and_crop_image(self.image.path, self.max_size)
                # Сохраняем изменения, если аватар был изменен
                super().save(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка обработки аватара: {e}")

    def delete(self, *args, **kwargs):
        """
        Удаляет объект, связанные файлы и пустые директории.
        """
        # Определение пути к файлу аватара
        image_path = self.image.path if self.image else None
        # Получение каталога пользователя на основе логики, схожей с generate_file_path
        class_name = self.__class__.__name__.lower()
        named_folder = (
            getattr(self, 'slug', None)
            or getattr(self, 'nic_name', None)
            or str(getattr(self, 'id', 'no_id'))
        )
        named_folder = re.sub(r"[\W]", "_", named_folder.strip()) if named_folder else 'no_id'
        user_folder_path = os.path.join('media', class_name, named_folder)
        # Удаление объекта из базы данных
        super().delete(*args, **kwargs)
        # Удаление файла аватара, если он существует
        if image_path and os.path.isfile(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                print(f'Удаление файла аватара не удалось: {e}')
        # Удаление папки пользователя, если она существует
        if os.path.isdir(user_folder_path):
            try:
                shutil.rmtree(user_folder_path)
            except Exception as e:
                print(f'Удаление папки пользователя не удалось: {e}')
        # Удаление пустых директорий в корневой директории 'media'
        FileUtils.remove_empty_directories('media')


    def __str__(self):
        fio = ''
        if self.nic_name:
            if not self.first_name or not self.last_name:
                fio = str(self.nic_name)
            elif not self.middle_name:
                fio = f"{self.last_name} {self.first_name}"
            else:
                fio = f"{self.last_name} {self.first_name} {self.middle_name}"
        else:
            fio = str(self.email)
        return fio

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
        ordering = ['-is_staff', '-is_active', 'last_name', 'first_name', 'middle_name']
```


-----

# Файл: tests.py

```
from django.test import TestCase

# Create your tests here.

```


-----

# Файл: token.py

```
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
                six.text_type(user.pk) + six.text_type(timestamp) +
                six.text_type(user.is_active)
        )


account_activation_token = TokenGenerator()

```


-----

# Файл: urls.py

```
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

```


-----

# Файл: views.py

```
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView, UpdateView, ListView

from users.forms import ProfileUpdateForm
from users.models import Profile


__all__ = (
    'LoginModalView',
    'ProfileUpdateView',
    'ProfileDeleteConfirmation',
    'SuperuserDeleteDenied',
    'ProfileDeleteView',
    'AllUsersView',
    'DeleteAllInactiveUsersView',
)

class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Класс обновления данных пользователя
    """
    model = Profile
    form_class = ProfileUpdateForm
    success_message = "Данные успешно обновлены."

    def get_object(self, **kwargs):
        self.active_tab = self.kwargs['tab']
        self.user = get_object_or_404(Profile, id=self.request.user.id)
        return self.user

    def get_template_names(self, **kwargs):
        if self.active_tab in ['profile', 'projects', 'subscription']:
            template_name = 'users/profile.html'
        else:
            template_name = 'layout/404.html'
        return template_name

    def get_success_url(self):
        return reverse("profile", kwargs={'tab': 'profile'})

    # def get_project_form(self):
    #     project_initial = {}
    #     if self.request.user.is_authenticated:
    #         project_initial['author'] = self.request.user
    #     project_form_class = ProjectCreateForm
    #     return project_form_class(initial=project_initial)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.get_object()
        context["active_tab"] = self.active_tab
        context["page_id"] = "user_projects"
       
        # # Получение информацию о проектах
        # projects = Project.objects.filter(author=self.request.user)
        # if projects:
        #     context["projects"] = projects

        # # Получение категорий целей
        # goal_categories = GoalCategory.choices
        # if goal_categories:
        #     context["goal_categories"] = goal_categories
        #     context["project_form"] = self.get_project_form()
        return context


class LoginModalView(SuccessMessageMixin, View):
    """ Класс входа в модальном окне """
    template_name = "users/auth/login_modal.html"
    success_message = "Вход в систему выполнен успешно."
    
    def get(self, request, *args, **kwargs):
        """Обрабатывает GET-запрос для загрузки формы"""
        form = AuthenticationForm()
        return render(request, self.template_name, {"form": form})
    
    def post(self, request, *args, **kwargs):
        """ Обработка POST-запроса для входа в систему """
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, self.success_message)
            # Проверяем параметр next
            next_url = request.POST.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return JsonResponse({}, headers={"HX-Redirect": next_url})
            # Перенаправление на страницу профиля по умолчанию
            profile_url = reverse_lazy("profile")
            return JsonResponse({}, headers={"HX-Redirect": profile_url})
        else:
            messages.error(request, "Ошибка входа. Проверьте правильность данных.")
        return render(request, self.template_name, {"form": form})


class ProfileDeleteConfirmation(TemplateView):
    """ Класс подтверждения удаления пользователя """
    
    def get_template_names(self, **kwargs):
        if self.request.user.is_authenticated and self.request.user.is_superuser:
            return ['users/components/superuser_delete_denied_modal.html']
        return ['users/components/profile_delete_confirmation.html']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.user.pk
        profile = get_object_or_404(Profile, pk=user_id)
        context["profile"] = profile
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            # Получаем профиль пользователя
            user_id = request.user.pk
            profile = get_object_or_404(Profile, pk=user_id)
            # Формируем контекст для шаблона
            context = {'profile': profile}
            # Получаем имя шаблона
            template_name = self.get_template_names()
            # Рендерим и возвращаем HTML-шаблон
            return render(request, template_name[0], context)
        except Profile.DoesNotExist:
            return HttpResponse("Пользователь не обнаружен", status=404)


class SuperuserDeleteDenied(TemplateView):
    """ Класс вывода страницы о невозможности удаления суперпользователя """
    template_name = 'users/components/superuser_delete_denied.html'


class ProfileDeleteView(SuccessMessageMixin, LoginRequiredMixin, View):
    model = Profile
    success_url = reverse_lazy('index')
    success_message = 'Профиль пользователя удален'

    def delete_profile(self, request, *args, **kwargs):
        """Удаление профиля пользователя с проверкой суперпользователя."""
        user_id = request.user.pk
        if request.user.is_superuser:
            return redirect('superuser_delete_denied')
        profile = get_object_or_404(Profile, pk=user_id)
        profile.delete()
        messages.success(request, self.success_message)
        logout(request)
        return HttpResponseRedirect(self.success_url)

    def get(self, request, *args, **kwargs):
        return render(request, 'layout/access_denied.html')
    
    def post(self, request, *args, **kwargs):
        return self.delete_profile(request, *args, **kwargs)


class AllUsersView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    """
    Класс просмотра информации обо всех пользователях.
    Доступно только для суперпользователей.
    """
    model = Profile
    template_name = 'users/all_users.html'
    context_object_name = 'all_users'
    
    def test_func(self):
        """Проверка прав суперпользователя"""
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_users"] = Profile.objects.all()
        return context


class DeleteAllInactiveUsersView(LoginRequiredMixin, View):
    """
    Класс удаления неактивных пользователей
    """
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            # Удаляем всех неактивных пользователей
            self.inactive_users = Profile.objects.filter(is_active=False)
            self.count = self.inactive_users.count()
            if self.count > 0:
                self.inactive_users.delete()
                messages.success(request, f'Неактивные профили удалены.')
            else:
                messages.warning(
                    request, 'В сервисе нет неактивных пользователей.')
        else:
            messages.error(
                request, 'У вас нет прав для выполнения этого действия.')

        return redirect('all_users')

```


-----

# Файл: __init__.py

```

```


-----

# Файл: templates\users\all_users.html

```
{% extends 'layout/base.html' %}
{% load static %}
{% load common_tags %}

{% block title %}
  Пользователи
{% endblock %}

<!-- META TAGS -->
{% block meta_tags %}
  {% include 'layout/components/meta_tags.html' %}
{% endblock %}

{% block content %}
  <!-- Контент главной страницы -->
  <section id="all_users" class="my-3">
    <div class="container py-3 py-lg-5">
      <h3 class="text-center fs-2 mb-4">Пользователи</h3>
      <div class="row">
        {% for user in all_users %}
          <div class="col-12 col-md-6 col-lg-4 col-xl-3 p-3">
            <div class="user_card d-flex flex-column h-100 
            {% if user.is_active == False %}
                
                
                
            bg-danger-subtle



              {% else %}
                
                
                
            border border-1 border-secondary



              {% endif %} 
            {% if request.user.is_authenticated and user.is_superuser %}
            bg-secondary
            {% endif %} rounded-3 shadow-sm">
              <div class="user_card_header text-center p-3">
                <a href="{% url 'admin:index' %}users/profile/{{ user.id }}/change/" target="_blank" class="text-decoration-none">{% include 'users/components/avatar.html' with custom_class='img-fluid w-50 rounded-circle shadow-sm' %}</a>
                <a href="{% url 'admin:index' %}users/profile/{{ user.id }}/change/" target="_blank" class="text-decoration-none"><h6 class="fw-bold pt-4">{{ user|upper }}</h6></a>
              </div>

              <div class="user_card_footer">
                <div class="d-flex flex-row justify-content-around align-items-center px-3 pb-3">
                  {% if user.email %}
                    <a href="mailto:{{ user.email }}?subject=Запрос от сервиса &laquo;IntellectPool&raquo;&amp;body=Добрый%20день!" class="btn btn-outline-primary rounded-circle" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-title="{{ user.email }}"><i class="bi bi-envelope-at fs-6"></i></a>
                  {% else %}
                    <div class="btn btn-outline-primary rounded-circle" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-title="&mdash;&mdash;&mdash;">
                      <i class="bi bi-envelope-at fs-6"></i>
                    </div>
                  {% endif %}
                  {% if user.phone %}
                    <a href="tel:{{ user.phone }}" class="btn btn-outline-primary rounded-circle" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-title="{{ user.phone }}"><i class="bi bi-telephone fs-6"></i></a>
                  {% else %}
                    <div class="btn btn-outline-primary rounded-circle" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-title="&mdash;&mdash;&mdash;">
                      <i class="bi bi-telephone fs-6"></i>
                    </div>
                  {% endif %}
                  {% if user.phone %}
                    <a href="https://wa.me/{{ user.phone|format_phone_to_whatsapp }}" class="btn btn-outline-primary rounded-circle" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-title="WhatsApp: {{ user.phone|format_phone_to_whatsapp }}"><i class="bi bi-whatsapp fs-6"></i></a>
                  {% else %}
                    <div class="btn btn-outline-primary rounded-circle" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-title="&mdash;&mdash;&mdash;">
                      <i class="bi bi-whatsapp fs-6"></i>
                    </div>
                  {% endif %}
                  {% comment %} <a href="{% url 'user_projects' pk=user.id %}" class="btn btn-outline-success rounded-circle" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-title="Проекты пользователя"><i class="bi bi-clipboard-data fs-6"></i></a> {% endcomment %}
                </div>
              </div>
            </div>
          </div>
        {% endfor %}
      </div>
    </div>
  </section>
  <!-- *********** -->
{% endblock %}

```


-----

# Файл: templates\users\profile.html

```
{% extends 'layout/base.html' %}
{% load static %}
{% load common_tags %}

{% block title %}
  {% if user.first_name and user.last_name %}
    {{ user.first_name }} {{ user.last_name }}
  {% else %}
    {{ user.get_username }}
  {% endif %}- Личный кабинет
{% endblock %}

<!-- META TAGS -->
{% block meta_tags %}
  {% include 'layout/components/meta_tags.html' %}
{% endblock %}

{% block content %}
  <!-- Контент главной страницы -->
  <section id="profile" class="mb-5">
    <div class="container py-3 py-lg-5">
      <!-- Вкладки -->
      <nav class="mt-5">
        <div class="nav nav-tabs" id="nav-tab" role="tablist">
          <button class="nav-link {% if active_tab == 'profile' %}active{% endif %}"
            id="nav-profile-tab"
            data-bs-toggle="tab"
            data-bs-target="#nav-profile"
            type="button"
            role="tab"
            aria-controls="nav-profile"
            {% if active_tab == 'profile' %}
              aria-selected="true"
            {% else %}
              aria-selected="false"
            {% endif %}>
            <i class="bi bi-person-workspace me-2"></i>Профиль
          </button>
          <button class="nav-link {% if active_tab == 'projects' %}active{% endif %}"
            id="nav-projects-tab"
            data-bs-toggle="tab"
            data-bs-target="#nav-projects"
            type="button"
            role="tab"
            aria-controls="nav-projects"
            {% if active_tab == 'projects' %}
              aria-selected="true"
            {% else %}
              aria-selected="false"
            {% endif %}>
            <i class="bi bi-clipboard-data me-2"></i>Проекты
          </button>
        </div>
      </nav>
      <div class="tab-content" id="nav-tabContent">
        <!-- Вкладка профиля -->
        {% include 'users/components/personal_data.html' %}
        <!-- Вкладка проектов -->
        {% include 'users/components/projects.html' %}
      </div>
    </div>
  </section>
  <!-- *********** -->
{% endblock %}

```


-----

# Файл: templates\users\profile_delete.html

```
{% extends 'layout/base.html' %}
{% load static %}
{% load django_bootstrap5 %}

{% block title %}
  Удаление профиля пользователя
{% endblock %}

{% block content %}
  <!-- Контент страницы -->
  <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <h2>Удаление профиля пользователя</h2>
    <div class="my-5">
      <h3>Внимание!</h3>
      <p>Вы хотите удалить пользователя {{ user }}.</p>
    </div>
    <div class="d-flex row justify-content-end align-content-end text-end">
      <form method="post">
        {% csrf_token %}
        <a href="{% url 'profile' %}" class="btn btn-secondary me-2"><i class="bi bi-arrow-left me-2"></i>Отмена</a>
        {% bootstrap_button '<i class="bi bi-trash me-2"></i>Удалить' button_class='btn-danger' %}
      </form>
    </div>
  </div>
  <!-- *********** -->
{% endblock %}

```


-----

# Файл: templates\users\auth\logged_out.html

```
{% extends 'layout/base.html' %}
{% load static %}

{% block title %}
  До свидания!
{% endblock %}

{% block content %}
  <!-- Контент страницы -->
  <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <h2>До свидания!</h2>
    <div class="text-center mt-5">
      <p>
        <b>Вы&nbsp;вышли из&nbsp;учетной записи</b>
      </p>
    </div>
    <div class="d-flex row justify-content-end px-3 gap-2">
      <a href="{% url 'login' %}" class="btn_submit btn btn-lg btn-primary my-3">Войти снова</a>
    </div>
  </div>
  <!-- *********** -->
{% endblock %}

```


-----

# Файл: templates\users\auth\login.html

```
{% extends 'layout/base.html' %}
{% load static %}
{% load widget_tweaks %}

{% block title %}
  Вход
{% endblock %}

{% block content %}
  <!-- Контент страницы -->
  <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <h2>Вход на&nbsp;сайт</h2>
    <div class="mt-5">
      {% include 'layout/registration/login_form.html' %}
    </div>
  </div>
  <!-- *********** -->
{% endblock %}

```


-----

# Файл: templates\users\auth\login_modal.html

```
{% load static %}
{% load widget_tweaks %}
{% load common_tags %}

<form id="login_form" method="POST" enctype="multipart/form-data" class="form" hx-post="{% url 'profile_login_modal' %}" hx-swap="innerHTML" hx-indicator="#spinner_modal">
  {% csrf_token %}
  <!-- Поле для сохранения -->
  <input type="hidden" name="next" value="{{ request.GET.next }}" />
  <div class="modal-header rounded-top ps-xl-4">
    <h3 class="modal-title align-middle" id="staticBackdropLabel"><i class="bi bi-key me-3"></i>Вход</h3>
    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
  </div>
  <div class="modal-body ps-xl-4">
    <div class="row my-0 my-lg-3">
      <div class="col-12 col-lg-4 order-1 d-none d-lg-flex px-3">
        <div class="d-flex align-items-center justify-content-start flex-grow-1">
          <img src="{% static 'img/elements/logo.webp' %}" class="img-fluid rounded-3" alt="Регистрация" />
        </div>
      </div>
      <div class="col-12 col-lg-8 order-2 d-flex flex-column justify-content-center mt-3 mt-lg-0 px-3">
        <div class="justify-content-start">
          <!-- Форма -->
          <div class="my-3">
            <p class="text-danger">
              {% if form.errors %}
                Ваше имя пользователя и&nbsp;пароль не&nbsp;совпадают. Попробуйте&nbsp;еще&nbsp;раз.
              {% endif %}
              {% if next %}
                {% if user.is_authenticated %}
                  У&nbsp;вашей учетной записи нет&nbsp;доступа к&nbsp;этой странице.
                  <br />Чтобы продолжить, пожалуйста, войдите в&nbsp;систему с&nbsp;учетной записью, у&nbsp;которой есть доступ.
                {% endif %}
              {% endif %}
            </p>
          </div>

          <div class="my-3">
            <div class="form-floating my-3">
              {{ form.username|add_class:'form-control floating'|attr:'id:id_username'|attr:'placeholder:name@example.com' }}
              <label for="{{ form.username.id_for_label }}">{{ form.username.label }}</label>
            </div>
            <div class="form-floating my-3">
              {{ form.password|add_class:'form-control floating'|attr:'id:id_password'|attr:'placeholder:Пароль' }}
              <label for="{{ form.password.id_for_label }}">{{ form.password.label_tag }}</label>
              <div id="{{ form.password.id_for_label }}Help" class="form-text">{{ form.password.errors }}</div>
            </div>
          </div>
          <!-- ===== -->
        </div>
      </div>
    </div>
  </div>
  <div class="modal-footer rounded-bottom ps-xl-4">
    <div class="d-flex row justify-content-end px-3 gap-2">
      <button type="submit" class="btn btn-lg btn_submit btn-primary my-3"><i class="bi bi-box-arrow-in-right pe-2"></i>Войти</button>
    </div>
  </div>
</form>

<!-- Индикатор загрузки в модальном окне -->
{% include 'layout/components/spinner_modal.html' %}

```


-----

# Файл: templates\users\components\avatar.html

```
{% load static %}

{% if user.image %}
  <img src="{{ user.image.url }}" alt="{{ user }}" class="{{ custom_class }}" />
{% else %}
  <img src="{% static 'img/elements/no_photo.webp' %}" alt="{{ user }}" class="{{ custom_class }}" />
{% endif %}

```


-----

# Файл: templates\users\components\personal_data.html

```
{% load static %}
{% load common_tags %}

<div class="tab-pane fade {% if active_tab == 'profile' %}show active{% endif %} my-3" id="nav-profile" role="tabpanel" aria-labelledby="nav-profile-tab">
  <div class="bg-body-tertiary p-3 p-md-4">
    <form action="{{ action }}" id="profile_form" method="POST" enctype="multipart/form-data" class="form">
      {% csrf_token %}

      <!-- Заголовок раздела -->
      <div class="mb-4">
        <h4 class="fw-bold text-primary mb-1">Профиль пользователя</h4>
        <p class="text-muted">Управление личной информацией и контактными данными</p>
      </div>

      <div class="profile_container">
        <!-- Три колонки в одной строке -->
        <div class="row align-items-stretch g-4 mb-4">
          <!-- Колонка 1: Аватар -->
          <div class="col-lg-3 d-flex">
            <div class="card border-0 shadow-sm w-100 d-flex flex-column align-items-center w-100 p-3">
              <div id="image_preview" class="image w-100 d-flex flex-column" style="height: 100%;">
                <label for="image_field" class="form-label d-flex flex-column justify-content-between align-items-center" style="flex-grow: 1;">
                  {% include 'users/components/avatar.html' with custom_class='img-fluid rounded-circle shadow-sm mb-3' %}
                  <div class="btn btn-sm btn-outline-primary w-100 mt-auto">
                    <i class="bi bi-camera pe-2"></i>Изменить фото
                  </div>
                </label>
                {{ form.image }}
              </div>
            </div>
          </div>

          <!-- Колонка 2: ФИО -->
          <div class="col-md-6 col-lg-5 d-flex">
            <div class="card border-0 shadow-sm w-100 d-flex flex-column">
              <div class="card-header bg-light-subtle flex-shrink-0">
                <h5 class="fw-bold mb-0">Личные данные</h5>
              </div>

              <div class="card-body d-flex flex-column p-3">
                <div class="d-flex flex-column justify-content-around h-100">
                  <!-- Фамилия -->
                  <div class="form-floating mb-3">
                    {{ form.last_name }}
                    <label class="form-label text-muted small mb-1"><i class="bi bi-people me-2 text-primary"></i>{{ form.last_name.label }}</label>
                  </div>

                  <!-- Имя -->
                  <div class="form-floating mb-3">
                    {{ form.first_name }}
                    <label class="form-label text-muted small mb-1"><i class="bi bi-person me-2 text-primary"></i>{{ form.first_name.label }}</label>
                  </div>

                  <!-- Отчество -->
                  <div class="form-floating mb-3">
                    {{ form.middle_name }}
                    <label class="form-label text-muted small mb-1"><i class="bi bi-person-up me-2 text-primary"></i>{{ form.middle_name.label }}</label>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Колонка 3: Контактные данные -->
          <div class="col-md-6 col-lg-4 d-flex">
            <div class="card border-0 shadow-sm w-100 d-flex flex-column">
              <div class="card-header bg-light-subtle flex-shrink-0">
                <h5 class="fw-bold mb-0">Контактные данные</h5>
              </div>

              <div class="card-body d-flex flex-column p-3">
                <div class="d-flex flex-column justify-content-around h-100">
                  <!-- Псевдоним -->
                  <div class="form-floating mb-3">
                    {{ form.nic_name }}
                    <label class="form-label text-muted small mb-1"><i class="bi bi-at me-2 text-primary"></i>{{ form.nic_name.label }}</label>
                  </div>

                  <!-- E-mail -->
                  <div class="form-floating mb-3">
                    {{ form.email }}
                    <label class="form-label text-muted small mb-1"><i class="bi bi-envelope-at me-2 text-primary"></i>{{ form.email.label }}</label>
                    <div class="text-danger">{{ form.email.errors }}</div>
                  </div>

                  <!-- Телефон -->
                  <div class="form-floating mb-3">
                    {{ form.phone }}
                    <label class="form-label text-muted small mb-1"><i class="bi bi-telephone me-2 text-primary"></i>{{ form.phone.label }}</label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Панель действий -->
      <div class="border-top pt-4 mt-3">
        <div class="d-flex justify-content-between align-items-end">
          {% if request.user.is_authenticated and not user.is_superuser %}
            <button type="button" class="btn btn-outline-danger text-decoration-none fw-bold" hx-post="{% url 'profile_delete_confirmation' %}" hx-target="#modal-content" hx-trigger="click" data-bs-toggle="modal" data-bs-target="#modal"><i class="bi bi-trash me-2"></i>Удалить профиль</button>
          {% else %}
            <div></div> <!-- Пустой div для выравнивания -->
          {% endif %}

          <button type="submit" class="btn btn-primary btn-lg px-5 fw-bold"><i class="bi bi-save me-2"></i>Сохранить изменения</button>
        </div>
      </div>
    </form>
  </div>
</div>

```


-----

# Файл: templates\users\components\profile_delete_confirmation.html

```
{% load static %}
{% load common_tags %}

<div class="modal-header bg-danger-subtle rounded-top ps-xl-4">
  <h3 class="modal-title align-middle text-danger" id="staticBackdropLabel"><i class="bi bi-trash me-3"></i>Удаление профиля</h3>
  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
</div>
<div class="modal-body bg-danger-subtle ps-xl-4">
  <div class="row my-0 my-lg-3">
    <div class="col-12 col-lg-4 order-1 d-none d-lg-flex px-3">
      <div class="d-flex align-items-center justify-content-start flex-grow-1">
        {% if profile.image %}
          <img src="{{ profile.image.url }}" class="img-fluid rounded-3" alt="{{ profile|safe }}" />
        {% else %}
          <img src="{% static 'img/elements/no_photo.webp' %}" class="img-fluid bg-light rounded-3" alt="{{ profile|safe }}" />
        {% endif %}
      </div>
    </div>
    <div class="col-12 col-lg-8 order-2 d-flex flex-column justify-content-center mt-3 mt-lg-0 px-3">
      <div class="justify-content-start">
        <!-- Предупреждение -->
        <div class="mb-2">
          <h3 class="text-danger mb-3">Внимание!</h3>
          <p>
            Вы&nbsp;собираетесь удалить свой профиль <br /><span class="text-primary fw-bold">{{ profile|replace_n|safe|typus }}</span>.
          </p>
          <p>Это действие необратимо и&nbsp;приведет к&nbsp;следующему:</p>
          <ul>
            <li>Все ваши данные будут безвозвратно удалены.</li>
            <li>Вы&nbsp;потеряете доступ ко&nbsp;всем проектам и&nbsp;функциям.</li>
          </ul>
          <p>
            Если вы&nbsp;уверены, нажмите &laquo;Удалить&raquo;.<br />Если хотите отменить, просто закройте это окно.
          </p>
        </div>
        <!-- ============= -->
      </div>
    </div>
  </div>
</div>
<div class="modal-footer bg-danger-subtle rounded-bottom ps-xl-4">
  <button type="button" class="btn_submit btn btn-outline-primary me-2" data-bs-dismiss="modal">Закрыть</button>
  <form action="{% url 'profile_delete' %}" method="post" hx-indicator="#spinner_modal">
    {% csrf_token %}
    <button type="submit" class="btn btn_submit btn-danger"><i class="bi bi-trash me-2"></i>Удалить</button>
  </form>
</div>

<!-- Индикатор загрузки в модальном окне -->
{% include 'layout/components/spinner_modal.html' %}

```


-----

# Файл: templates\users\components\projects.html

```
{% load static %}
{% load common_tags %}

<!-- Информация о проектах -->
<div class="tab-pane fade {% if active_tab == 'projects' %}show active{% endif %} my-3" id="nav-projects" role="tabpanel" aria-labelledby="nav-projects-tab">
  <div class="form-control p-3"></div>
</div>

```


-----

# Файл: templates\users\components\superuser_delete_denied.html

```
{% extends 'layout/base.html' %}
{% load static %}
{% load common_tags %}

{% block title %}
  Самостоятельное удаление не&nbsp;предусмотрено
{% endblock %}

{% block content %}
  <!-- Контент страницы -->
  <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <h2 class="text-danger">Действие запрещено</h2>
    <div class="mt-5">
      <h3 class="mb-3">Удаление суперпользователя невозможно</h3>
      <ul>
        <li class="mb-2">
          <span class="text-primary fw-bold">{{ profile|replace_n|safe|typus }}</span> является суперпользователем
        </li>
        <li>Самостоятельное удаление суперпользователя невозможно</li>
      </ul>
      <p class="fw-bold">Пожалуйста, обратитесь к администратору.</p>
    </div>
  </div>
  <!-- *********** -->
{% endblock %}

```


-----

# Файл: templates\users\components\superuser_delete_denied_modal.html

```
{% load static %}
{% load common_tags %}

<div class="modal-header rounded-top ps-xl-4">
  <h3 class="modal-title align-middle text-danger" id="staticBackdropLabel">Самостоятельное удаление не&nbsp;предусмотрено</h3>
  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
</div>
<div class="modal-body ps-xl-4">
  <div class="row my-0 my-lg-3">
    <div class="col-12 col-lg-4 order-1 d-none d-lg-flex px-3">
      <div class="d-flex align-items-center justify-content-start flex-grow-1">
        {% if profile.image %}
          <img src="{{ profile.image.url }}" class="img-fluid rounded-3" alt="{{ profile|safe }}" />
        {% else %}
          <img src="{% static 'img/elements/no_photo.webp' %}" class="img-fluid bg-light rounded-3" alt="{{ profile|safe }}" />
        {% endif %}
      </div>
    </div>
    <div class="col-12 col-lg-8 order-2 d-flex flex-column justify-content-center mt-3 mt-lg-0 px-3">
      <div class="justify-content-start">
        <!-- Предупреждение -->
        <div class="mt-5">
          <h3 class="mb-3">Удаление суперпользователя невозможно</h3>
          <ul>
            <li class="mb-2">
              <span class="text-primary fw-bold">{{ profile|replace_n|safe|typus }}</span> является суперпользователем
            </li>
            <li>Самостоятельное удаление суперпользователя невозможно</li>
          </ul>
          <p class="fw-bold">Пожалуйста, обратитесь к администратору.</p>
        </div>
        <!-- ============= -->
      </div>
    </div>
  </div>
</div>
<div class="modal-footer rounded-bottom ps-xl-4">
  <button type="button" class="btn_submit btn btn-outline-primary me-2" data-bs-dismiss="modal">Закрыть</button>
</div>

```
