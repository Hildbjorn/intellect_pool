# Файл: admin.py

```
from django.contrib import admin

# Register your models here.

```


-----

# Файл: apps.py

```
from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'

```


-----

# Файл: models.py

```
from django.db import models

# Create your models here.

```


-----

# Файл: tests.py

```
from django.test import TestCase

# Create your tests here.

```


-----

# Файл: urls.py

```
from django.urls import path
from .views import *

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('user_agreement', UserАgreementView.as_view(), name='user_agreement'),
    path('user_agreement_modal', UserAgreementModalView.as_view(), name='user_agreement_modal'),
    path('privacy_policy', UserPrivacyPolicyView.as_view(), name='privacy_policy'),
    path('privacy_policy_modal', UserPrivacyPolicyModalView.as_view(), name='privacy_policy_modal'),
]

```


-----

# Файл: views.py

```
from django.views.generic import TemplateView

__all__ = (
    'IndexView',
    'UserАgreementView',
    'UserAgreementModalView',
    'UserPrivacyPolicyView',
    'UserPrivacyPolicyModalView',
)

class IndexView(TemplateView):
    template_name = 'home/index.html'


class UserАgreementView(TemplateView):
    """Представление для загрузки пользовательского соглашения"""
    template_name = 'home/components/documents/user_agreement/user_agreement.html'


class UserAgreementModalView(TemplateView):
    """Представление для загрузки пользовательского соглашения в модальное окно"""
    template_name = 'home/components/documents/user_agreement/user_agreement_modal.html'


class UserPrivacyPolicyView(TemplateView):
    """Представление для загрузки политики конфиденциальности"""
    template_name = 'home/components/documents/privacy_policy/privacy_policy.html'


class UserPrivacyPolicyModalView(TemplateView):
    """Представление для загрузки политики конфиденциальности в модальное окно"""
    template_name = 'home/components/documents/privacy_policy/privacy_policy_modal.html'
```


-----

# Файл: __init__.py

```

```


-----

# Файл: templates\home\index.html

```
{% extends 'layout/base.html' %}
{% load static %}
{% load widget_tweaks %}

{% block title %}
  IntellectPool - Центр идей, созданных на базе РИД
{% endblock %}

<!-- META TAGS -->
{% block meta_tags %}
  {% include 'layout/components/meta_tags.html' %}
{% endblock %}

{% block content %}
  {% if request.user.is_authenticated %}
    {% include 'home/components/main.html' %}
  {% else %}
    <!-- Hero -->
    {% include 'home/components/hero.html' %}
  {% endif %}
{% endblock %}

```


-----

# Файл: templates\home\components\hero.html

```
{% load static %}

<!-- ======= Hero Section ======= -->
<section id="hero">
  <div class="hero__body">
    <div class="container p-0">
      <div class="row align-items-center g-4 g-lg-6">
        <!-- Текстовый блок -->
        <div class="col-12 col-xl-6 order-1 order-xl-1">
          <div class="mb-4">
            <span class="badge bg-light bg-opacity-10 text-light border border-primary border-opacity-25 fs-6 px-4 py-2 rounded-pill"><i class="bi bi-lightbulb me-2"></i>Платформа инновационных проектов</span>
          </div>

          <h1 class="display-4 fw-bold mb-4">
            IntellectPool
            <span class="text-light d-block fs-2 fw-normal mt-2">Центр идей на&nbsp;базе РИД</span>
          </h1>

          <p class="lead text-light mb-5">Структурированный и&nbsp;визуально привлекательный способ демонстрации технологических решений и&nbsp;их&nbsp;коммерческого потенциала.</p>

          <!-- Ключевые преимущества в списке -->
          <div class="row mb-5">
            <div class="col-md-6 mb-3">
              <div class="d-flex">
                <div class="text-success me-3">
                  <i class="bi bi-check2-circle fs-4"></i>
                </div>
                <div>
                  <h6 class="text-warning fw-bold mb-1">Защищённые технологии</h6>
                  <p class="small text-light mb-0">Проекты на&nbsp;основе патентованных решений</p>
                </div>
              </div>
            </div>
            <div class="col-md-6 mb-3">
              <div class="d-flex">
                <div class="text-success me-3">
                  <i class="bi bi-check2-circle fs-4"></i>
                </div>
                <div>
                  <h6 class="text-warning fw-bold mb-1">Коммерческий анализ</h6>
                  <p class="small text-light mb-0">Структурированные метрики и&nbsp;показатели</p>
                </div>
              </div>
            </div>
            <div class="col-md-6 mb-3">
              <div class="d-flex">
                <div class="text-success me-3">
                  <i class="bi bi-check2-circle fs-4"></i>
                </div>
                <div>
                  <h6 class="text-warning fw-bold mb-1">Визуальная презентация</h6>
                  <p class="small text-light mb-0">Привлекательный формат демонстрации</p>
                </div>
              </div>
            </div>
            <div class="col-md-6 mb-3">
              <div class="d-flex">
                <div class="text-success me-3">
                  <i class="bi bi-check2-circle fs-4"></i>
                </div>
                <div>
                  <h6 class="text-warning fw-bold mb-1">Целевая аудитория</h6>
                  <p class="small text-light mb-0">Для стратегических партнёров и&nbsp;инвесторов</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Кнопки действий -->
          <div class="d-flex flex-row justify-content-center justify-content-lg-start gap-3 mb-4">
            <!-- Кнопка входа -->
            <div type="button" class="btn btn-lg btn-success px-5 shadow-sm" role="button" hx-get="{% url 'profile_login_modal' %}?next={% url 'index' %}" hx-target="#modal-content" hx-trigger="click" data-bs-toggle="modal" data-bs-target="#modal">
              <i class="bi bi-box-arrow-in-right fs-5 me-2"></i>Вход в&nbsp;систему
            </div>
          </div>
        </div>

        <!-- Визуальный блок -->
        <div class="col-12 col-xl-6 order-2 order-xl-2">
          <div class="position-relative">
            <!-- Логотип -->
            <div class="text-center">
              <img class="img-fluid" src="{% static 'img/elements/logo.webp' %}" alt="IntellectPool - Центр инновационных проектов" style="max-height: 400px;" />
            </div>
            <div class="text-center">
              {% include 'home/components/statistics.html' %}
            </div>

            <!-- Декоративные элементы -->
            <div class="position-absolute top-0 start-0 translate-middle bg-warning bg-opacity-10 rounded-circle" style="width: 100px; height: 100px;"></div>
            <div class="position-absolute bottom-0 end-0 translate-middle bg-light bg-opacity-10 rounded-circle" style="width: 80px; height: 80px;"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
<!-- ===== End of Hero Section ===== -->

```


-----

# Файл: templates\home\components\main.html

```
{% load static %}

<!-- ========== MAIN SECTION ========== -->
<section class="py-3 py-md-4 py-lg-5">
  <div class="container">
    {% comment %}
    <!-- Заголовок раздела -->
    <div class="row mb-3">
      <div class="col-12">
        <h1 class="display-5 fw-bold text-primary">Панель управления</h1>
        <p class="lead text-muted">Обзорная панель для управления идеями, проектами и&nbsp;аналитики</p>
      </div>
    </div>
    {% endcomment %}

    <!-- Статистическая панель -->
    <div class="row mb-4">
      <div class="col-12">
        <div class="card border-0 shadow-sm">
          <div class="card-body">
            <div class="row text-center">
              <div class="col-md-3 mb-3 mb-md-0">
                <div class="display-6 fw-bold text-primary">156</div>
                <div class="text-muted">Всего идей</div>
              </div>
              <div class="col-md-3 mb-3 mb-md-0">
                <div class="display-6 fw-bold text-info">89</div>
                <div class="text-muted">Защищённых РИД</div>
              </div>
              <div class="col-md-3 mb-3 mb-md-0">
                <div class="display-6 fw-bold text-success">42</div>
                <div class="text-muted">Активных проекта</div>
              </div>
              <div class="col-md-3">
                <div class="display-6 fw-bold text-dark">28</div>
                <div class="text-muted">Организаций</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Карточки -->
    <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
      <!-- Карточка: Все идеи -->
      <div class="col">
        <div class="card h-100 border-0 shadow-sm overflow-hidden d-flex flex-column position-relative" style="min-height: 270px;">
          <!-- Фон карточки -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: url('{% static 'img/categories/ideas-bg.jpg' %}') center/cover; z-index: 1;"></div>

          <!-- Градиентная подложка -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.6) 70%, rgba(0,0,0,0.8) 100%); z-index: 2;"></div>

          <!-- Контент карточки -->
          <div class="position-relative d-flex flex-column flex-grow-1 p-4" style="z-index: 3;">
            <!-- Иконка и заголовок -->
            <div class="mb-3">
              <div class="d-flex align-items-center">
                <div class="bg-primary bg-opacity-75 d-flex align-items-center justify-content-center" style="width: 56px; height: 56px; border-radius: 28px;">
                  <i class="bi bi-lightbulb fs-4 text-white"></i>
                </div>
                <h3 class="h4 mb-0 ms-3 text-white">Все идеи</h3>
              </div>
            </div>

            <!-- Описание -->
            <div class="mb-4 flex-grow-1">
              <p class="text-white mb-0" style="text-shadow: 1px 1px 2px rgba(0,0,0,0.5);">Полный каталог всех идей и&nbsp;инновационных предложений, созданных на&nbsp;платформе</p>
            </div>

            <!-- Кнопка -->
            <div class="mt-auto">
              <a href="#" class="btn btn-primary w-100 shadow-sm"><i class="bi bi-arrow-right-circle me-2"></i>Перейти к&nbsp;идеям</a>
            </div>
          </div>
        </div>
      </div>

      <!-- Карточка: Каталог РИД -->
      <div class="col">
        <div class="card h-100 border-0 shadow-sm overflow-hidden d-flex flex-column position-relative" style="min-height: 270px;">
          <!-- Фон карточки -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: url('{% static 'img/categories/patents-bg.jpg' %}') center/cover; z-index: 1;"></div>

          <!-- Градиентная подложка -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.6) 70%, rgba(0,0,0,0.8) 100%); z-index: 2;"></div>

          <!-- Контент карточки -->
          <div class="position-relative d-flex flex-column flex-grow-1 p-4" style="z-index: 3;">
            <!-- Иконка и заголовок -->
            <div class="mb-3">
              <div class="d-flex align-items-center">
                <div class="bg-info bg-opacity-75 d-flex align-items-center justify-content-center" style="width: 56px; height: 56px; border-radius: 28px;">
                  <i class="bi bi-file-earmark-text fs-4 text-white"></i>
                </div>
                <h3 class="h4 mb-0 ms-3 text-white">Каталог РИД</h3>
              </div>
            </div>

            <!-- Описание -->
            <div class="mb-4 flex-grow-1">
              <p class="text-white mb-0" style="text-shadow: 1px 1px 2px rgba(0,0,0,0.5);">База патентов и&nbsp;защищённых технологий, которые используются в&nbsp;проектах</p>
            </div>

            <!-- Кнопка -->
            <div class="mt-auto">
              <a href="#" class="btn btn-info text-white w-100 shadow-sm"><i class="bi bi-search me-2"></i>Искать РИД</a>
            </div>
          </div>
        </div>
      </div>

      <!-- Карточка: На рассмотрении в организациях -->
      <div class="col">
        <div class="card h-100 border-0 shadow-sm overflow-hidden d-flex flex-column position-relative" style="min-height: 270px;">
          <!-- Фон карточки -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: url('{% static 'img/categories/review-bg.jpg' %}') center/cover; z-index: 1;"></div>

          <!-- Градиентная подложка -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.6) 70%, rgba(0,0,0,0.8) 100%); z-index: 2;"></div>

          <!-- Контент карточки -->
          <div class="position-relative d-flex flex-column flex-grow-1 p-4" style="z-index: 3;">
            <!-- Иконка и заголовок -->
            <div class="mb-3">
              <div class="d-flex align-items-center">
                <div class="bg-warning bg-opacity-75 d-flex align-items-center justify-content-center" style="width: 56px; height: 56px; border-radius: 28px;">
                  <i class="bi bi-clock-history fs-4 text-white"></i>
                </div>
                <h3 class="h4 mb-0 ms-3 text-white">На&nbsp;рассмотрении</h3>
              </div>
            </div>

            <!-- Описание -->
            <div class="mb-4 flex-grow-1">
              <p class="text-white mb-0" style="text-shadow: 1px 1px 2px rgba(0,0,0,0.5);">Идеи, находящиеся на&nbsp;оценке в&nbsp;различных организациях-партнёрах</p>
            </div>

            <!-- Кнопка -->
            <div class="mt-auto">
              <a href="#" class="btn btn-warning text-white w-100 shadow-sm"><i class="bi bi-eye me-2"></i>Просмотреть статус</a>
            </div>
          </div>
        </div>
      </div>

      <!-- Карточка: Реализуемые проекты -->
      <div class="col">
        <div class="card h-100 border-0 shadow-sm overflow-hidden d-flex flex-column position-relative" style="min-height: 270px;">
          <!-- Фон карточки -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: url('{% static 'img/categories/projects-bg.jpg' %}') center/cover; z-index: 1;"></div>

          <!-- Градиентная подложка -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.6) 70%, rgba(0,0,0,0.8) 100%); z-index: 2;"></div>

          <!-- Контент карточки -->
          <div class="position-relative d-flex flex-column flex-grow-1 p-4" style="z-index: 3;">
            <!-- Иконка и заголовок -->
            <div class="mb-3">
              <div class="d-flex align-items-center">
                <div class="bg-success bg-opacity-75 d-flex align-items-center justify-content-center" style="width: 56px; height: 56px; border-radius: 28px;">
                  <i class="bi bi-rocket-takeoff fs-4 text-white"></i>
                </div>
                <h3 class="h4 mb-0 ms-3 text-white">Реализуемые проекты</h3>
              </div>
            </div>

            <!-- Описание -->
            <div class="mb-4 flex-grow-1">
              <p class="text-white mb-0" style="text-shadow: 1px 1px 2px rgba(0,0,0,0.5);">Активные проекты, находящиеся в&nbsp;стадии реализации и&nbsp;коммерциализации</p>
            </div>

            <!-- Кнопка -->
            <div class="mt-auto">
              <a href="#" class="btn btn-success w-100 shadow-sm"><i class="bi bi-play-circle me-2"></i>Управлять проектами</a>
            </div>
          </div>
        </div>
      </div>

      <!-- Карточка: Отрасли -->
      <div class="col">
        <div class="card h-100 border-0 shadow-sm overflow-hidden d-flex flex-column position-relative" style="min-height: 270px;">
          <!-- Фон карточки -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: url('{% static 'img/categories/industries-bg.jpg' %}') center/cover; z-index: 1;"></div>

          <!-- Градиентная подложка -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.6) 70%, rgba(0,0,0,0.8) 100%); z-index: 2;"></div>

          <!-- Контент карточки -->
          <div class="position-relative d-flex flex-column flex-grow-1 p-4" style="z-index: 3;">
            <!-- Иконка и заголовок -->
            <div class="mb-3">
              <div class="d-flex align-items-center">
                <div class="bg-secondary bg-opacity-75 d-flex align-items-center justify-content-center" style="width: 56px; height: 56px; border-radius: 28px;">
                  <i class="bi bi-building fs-4 text-white"></i>
                </div>
                <h3 class="h4 mb-0 ms-3 text-white">Отрасли</h3>
              </div>
            </div>

            <!-- Описание -->
            <div class="mb-4 flex-grow-1">
              <p class="text-white mb-0" style="text-shadow: 1px 1px 2px rgba(0,0,0,0.5);">Классификация проектов по&nbsp;отраслям промышленности и&nbsp;сферам деятельности</p>
            </div>

            <!-- Кнопка -->
            <div class="mt-auto">
              <a href="#" class="btn btn-secondary w-100 shadow-sm"><i class="bi bi-funnel me-2"></i>Фильтровать по&nbsp;отраслям</a>
            </div>
          </div>
        </div>
      </div>

      <!-- Карточка: Организации-участники -->
      <div class="col">
        <div class="card h-100 border-0 shadow-sm overflow-hidden d-flex flex-column position-relative" style="min-height: 270px;">
          <!-- Фон карточки -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: url('{% static 'img/categories/organizations-bg.jpg' %}') center/cover; z-index: 1;"></div>

          <!-- Градиентная подложка -->
          <div class="position-absolute top-0 start-0 w-100 h-100" style="background: linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.6) 70%, rgba(0,0,0,0.8) 100%); z-index: 2;"></div>

          <!-- Контент карточки -->
          <div class="position-relative d-flex flex-column flex-grow-1 p-4" style="z-index: 3;">
            <!-- Иконка и заголовок -->
            <div class="mb-3">
              <div class="d-flex align-items-center">
                <div class="bg-dark bg-opacity-75 d-flex align-items-center justify-content-center" style="width: 56px; height: 56px; border-radius: 28px;">
                  <i class="bi bi-people fs-4 text-white"></i>
                </div>
                <h3 class="h4 mb-0 ms-3 text-white">Организации-участники</h3>
              </div>
            </div>

            <!-- Описание -->
            <div class="mb-4 flex-grow-1">
              <p class="text-white mb-0" style="text-shadow: 1px 1px 2px rgba(0,0,0,0.5);">Компании и&nbsp;организации, участвующие в&nbsp;развитии и&nbsp;реализации инновационных проектов</p>
            </div>

            <!-- Кнопка -->
            <div class="mt-auto">
              <a href="#" class="btn btn-dark w-100 shadow-sm"><i class="bi bi-person-badge me-2"></i>Просмотреть организации</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
<!-- ========== END OF MAIN SECTION ========== -->

```


-----

# Файл: templates\home\components\statistics.html

```
{% load static %}

<!-- Мини-статистика -->
<div class="d-flex flex-row justify-content-center gap-5 mt-5 mb-5">
  <div>
    <div class="fs-3 fw-bold text-light">100+</div>
    <div class="small text-light">Патентов</div>
  </div>
  <div>
    <div class="fs-3 fw-bold text-warning">80+</div>
    <div class="small text-light">Идей</div>
  </div>
  <div>
    <div class="fs-3 fw-bold text-success">50+</div>
    <div class="small text-light">Успешных проектов</div>
  </div>
</div>

```
