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
