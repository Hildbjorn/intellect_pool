# Файл: admin\base_site.html

```
{% extends 'admin/base.html' %}
{% load static %}
{% load sass_tags %}

{% block extrahead %}
  {{ block.super }}
  <link href="{% sass_src 'css/admin.scss' %}" rel="stylesheet" type="text/css" />
  <script type="text/javascript" src="{% static 'js/admin.js' %}"></script>
{% endblock %}

{% block title %}
  {% if subtitle %}
    {{ subtitle }} |
  {% endif %}
  {{ title }} | {{ site_title|default:_('Django site admin') }}
{% endblock %}

{% block branding %}
  <div id="site-name">
    <a href="{% url 'admin:index' %}">{{ site_header|default:_('Django administration') }}</a>
  </div>
  {% if user.is_anonymous %}
    {% include 'admin/color_theme_toggle.html' %}
  {% endif %}
{% endblock %}

{% block nav-global %}
{% endblock %}

```


-----

# Файл: layout\404.html

```
{% extends 'layout/base.html' %}
{% load static %}

{% block title %}
  Страница не существует
{% endblock %}

{% block content %}
  <!-- ========== КОНТЕНТ СТРАНИЦЫ 404 ========== -->
  <div class="container w-auto my-auto p-3 p-lg-4">
    <!-- Заголовок ошибки -->
    <h2 class="text-center text-primary">Страница не&nbsp;существует</h2>

    <!-- Основное содержимое -->
    <div class="text-center mt-5">
      <!-- Изображение для визуализации ошибки -->
      <div class="mt-5">
        <img class="img-fluid w-50" src="{% static 'img/elements/logo.webp' %}" alt="Страница не существует" />
      </div>

      <!-- Код ошибки -->
      <div class="text-center text-primary mt-3">
        <h1 class="text-center text-danger text-big fw-bold">4 0 4</h1>
      </div>

      <!-- Рекомендация для пользователя -->
      <div class="mt-5">
        <p>
          <h2 class="text-center text-primary big-text">Попробуйте уточнить запрос</h2>
        </p>
      </div>
    </div>
  </div>
{% endblock %}

```


-----

# Файл: layout\access_denied.html

```
{% extends 'layout/base.html' %}
{% load static %}

{% block title %}
  Доступ запрещен!
{% endblock %}

{% block content %}
  <!-- ========== КОНТЕНТ СТРАНИЦЫ ОШИБКИ ДОСТУПА ========== -->
  <div class="container bg-danger-subtle rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <!-- Заголовок ошибки -->
    <h2 class="text-center text-primary">Доступ запрещен!</h2>

    <!-- Основное содержимое -->
    <div class="text-center mt-5">
      <!-- Изображение для визуализации ошибки -->
      <div class="mt-5">
        <img class="img-fluid w-50" src="{% static 'img/elements/logo.webp' %}" alt="Доступ запрещен" />
      </div>

      <!-- Сообщение об ошибке -->
      <div class="mt-5">
        <h2 class="text-center text-primary fw-bold big-text">У&nbsp;вас нет прав на&nbsp;просмотр данной страницы.</h2>
      </div>

      <!-- Кнопка связи с администрацией -->
      <p class="text-end mt-5 mb-0">
        <a class="btn btn-outline-primary" href="mailto:info@stratman.pro?subject=Проблема%20с%20доступом&body=Добрый%20день!">Обратитесь к&nbsp;администрации</a>
      </p>
    </div>
  </div>
{% endblock %}

```


-----

# Файл: layout\base.html

```
<!DOCTYPE html>
<!--              
  Базовый шаблон проекта "IntellectPool"
  Автор: Artem Fomin (2024)
  Используемые технологии:
  - Django
  - Bootstrap 5
  - HTMX
  - jQuery
  - Sass
             -->
{% load static %}
{% load sass_tags %}
{% load django_bootstrap5 %}

<html lang="ru" data-bs-theme="light">
  <head>
    <!-- ==================== БАЗОВЫЕ НАСТРОЙКИ ==================== -->
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />

    <!-- ==================== ЗАЩИТА И БЕЗОПАСНОСТЬ ==================== -->
    <meta name="csrfmiddlewaretoken" content="{{ csrf_token }}" />

    <!-- ==================== СТИЛИ ==================== -->
    <!-- Основные стили проекта (компилируются из Sass) -->
    <link href="{% sass_src 'css/main.scss' %}" rel="stylesheet" type="text/css" />

    <!-- ==================== СКРИПТЫ ==================== -->
    <!-- HTMX - библиотека для AJAX-запросов и динамического обновления контента -->
    <script src="{% static 'htmx/htmx.min.js' %}"></script>

    <!-- Bootstrap JavaScript (включает Popper.js для всплывающих элементов) -->
    {% bootstrap_javascript %}

    <!-- jQuery (основная зависимость для многих плагинов) -->
    <script src="{% static 'js/jquery-3.7.1.min.js' %}"></script>

    <!-- Основные скрипты проекта (кастомная логика) -->
    <script type="text/javascript" src="{% static 'js/script.js' %}"></script>

    <!-- Интеграция с DaData для автодополнения организаций -->
    <script src="{% static 'dadata/suggestions/js/jquery.suggestions.min.js' %}"></script>

    <!-- ==================== ЗАГОЛОВОК И ФАВИКОНКИ ==================== -->
    <title>
      {% block title %}
        IntellectPool
      {% endblock %}
    </title>

    <!-- Фавиконки для всех устройств и браузеров -->
    {% include 'layout/components/favicons.html' %}

    <!-- ==================== ДОПОЛНИТЕЛЬНЫЕ МЕТА-ТЕГИ ==================== -->
    {% block meta_tags %}

    {% endblock %}
  </head>

  <!-- ==================== ТЕЛО СТРАНИЦЫ ==================== -->
  <body class="bg-body">
    <!-- Индикатор загрузки (отображается при AJAX-запросах) -->
    {% include 'layout/components/spinner.html' %}

    <!-- Контейнер для всех модальных окон -->
    {% include 'layout/components/modal.html' %}

    <!-- Шапка сайта (навигация, логотип и т.д.) -->
    {% if request.user.is_authenticated %}
      {% include 'layout/header/header.html' %}
    {% endif %}

    <!-- ==================== ОСНОВНОЙ КОНТЕНТ ==================== -->
    <main id="main-content" class="d-flex flex-column flex-fill bg-body">
      <!-- Системные сообщения (успех, ошибки, предупреждения) -->
      {% include 'layout/components/messages.html' %}

      <!--              
        БЛОК КОНТЕНТА 
        Основное содержимое страницы (переопределяется в дочерних шаблонах)
                   -->
      {% block content %}

      {% endblock %}
    </main>
    <!-- Кнопка "Наверх" -->
    {% include 'layout/components/scroll_to_top.html' %}
    <!-- Подвал сайта (контактная информация, ссылки и т.д.) -->
    {% comment %} {% include 'layout/footer/footer.html' %} {% endcomment %}
  </body>
</html>

```


-----

# Файл: layout\components\favicons.html

```
{% load static %}

<link rel="icon" type="image/png" href="{% static 'img/favicons/favicon-96x96.png' %}" sizes="96x96" />
<link rel="icon" type="image/svg+xml" href="{% static 'img/favicons/favicon.svg' %}" />
<link rel="shortcut icon" href="{% static 'img/favicons/favicon.ico' %}" />
<link rel="apple-touch-icon" sizes="180x180" href="{% static 'img/favicons/apple-touch-icon.png' %}" />
<meta name="apple-mobile-web-app-title" content="Intellect Pool" />
<link rel="manifest" href="{% static 'img/favicons/site.webmanifest' %}" />

```


-----

# Файл: layout\components\messages.html

```
<!-- Блок для отображения системных сообщений (успех, ошибки, предупреждения) -->
<div id="messages" class="messages">
  <!-- Проверка наличия сообщений -->
  {% if messages %}
    <div class="alert_messages">
      <div class="mt-3">
        <!-- Цикл по всем сообщениям -->
        {% for message in messages %}
          <!-- Определение класса иконки в зависимости от типа сообщения -->
          {% with icon_class=message.tags|default:'info' %}
            <!-- Контейнер сообщения -->
            <div class="alert alert-{{ icon_class }} d-flex justify-content-between align-items-top" role="alert" aria-live="assertive">
              <!-- Основное содержимое сообщения (иконка + текст) -->
              <div class="d-flex align-items-top">
                <!-- Выбор иконки в зависимости от типа сообщения -->
                <i class="bi 
                  <!-- Иконка для успешных сообщений -->
                  {% if message.tags == 'success' %}
                    
                    
                    bi-check-circle
                  <!-- Иконка для предупреждений -->


                  {% elif message.tags == 'warning' %}
                    
                    
                    bi-exclamation-circle
                  <!-- Иконка для ошибок -->


                  {% elif message.tags == 'error' %}
                    
                    
                    bi-x-circle
                  <!-- Иконка по умолчанию -->


                  {% else %}
                    
                    
                    bi-info-circle


                  {% endif %} 
                  pe-2">

                </i>

                <!-- Текст сообщения (с поддержкой HTML) -->
                <div>{{ message|safe }}</div>
              </div>

              <!-- Кнопка закрытия сообщения -->
              <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Закрыть"></button>
            </div>
          {% endwith %}
        {% endfor %}
      </div>
    </div>
  {% endif %}
</div>

```


-----

# Файл: layout\components\meta_tags.html

```
{% load static %}
<!-- ========== ОСНОВНЫЕ МЕТА-ТЕГИ ДЛЯ SEO И СОЦИАЛЬНЫХ СЕТЕЙ ========== -->

<!-- Базовые SEO-теги -->
<meta name="description" content="IntellectPool - Центр идей, созданных на базе РИД" />
<meta name="keywords" content="IntellectPool" />
<meta name="robots" content="index,follow" />
<link rel="canonical" href="https://b-model.pro/" />

<!-- Open Graph (Facebook, VK, Одноклассники) -->
<meta property="og:type" content="website" />
<meta property="og:site_name" content="IntellectPool" />
<meta property="og:title" content="IntellectPool" />
<meta property="og:description" content="IntellectPool - Центр идей, созданных на базе РИД" />
<meta property="og:url" content="https://b-model.pro/" />
<meta property="og:locale" content="ru_RU" />

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="IntellectPool" />
<meta name="twitter:description" content="IntellectPool - Центр идей, созданных на базе РИД" />
<meta name="twitter:image:src" content="{% static 'img/elements/logo.png' %}" />
<meta name="twitter:url" content="https://b-model.pro/" />
<meta name="twitter:domain" content="IntellectPool" />
<meta name="twitter:site" content="IntellectPool" />
<meta name="twitter:creator" content="@stratman.pro" />

<!-- Schema.org для Google -->
<meta itemprop="name" content="IntellectPool" />
<meta itemprop="description" content="IntellectPool - Центр идей, созданных на базе РИД" />
<meta itemprop="image" content="{% static 'img/elements/logo.png' %}" />

```


-----

# Файл: layout\components\modal.html

```
{% load static %}
<!-- ========== УНИВЕРСАЛЬНОЕ МОДАЛЬНОЕ ОКНО ========== -->
<div class="modal fade" id="modal" data-bs-backdrop="static" data-bs-keyboard="false" tabindex="-1" aria-labelledby="modal" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable modal-lg">
    <div class="modal-content" id="modal-content">
      <!-- Контент будет подгружаться динамически через HTMX -->
    </div>
  </div>
</div>

<!-- ========== БОЛЬШОЕ МОДАЛЬНОЕ ОКНО ДЛЯ ДОКУМЕНТОВ ========== -->
<div class="modal fade" id="largeModal" data-bs-backdrop="static" data-bs-keyboard="false" tabindex="-1" aria-labelledby="largeModal" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable modal-xl">
    <div class="modal-content" id="largeModal-content">
      <!-- Контент будет подгружаться динамически через HTMX -->
    </div>
  </div>
</div>

```


-----

# Файл: layout\components\scroll_to_top.html

```
{% load static %}
<a href="#" class="btn btn-light rounded-circle scroll-to-top" id="scrollToTop" style="display: none; position: fixed; bottom: 1rem; right: 1rem; width: 40px; height: 40px; z-index: 1000;"><i class="bi bi-arrow-up"></i></a>

```


-----

# Файл: layout\components\spinner.html

```
{% load static %}
<!-- ========== ИНДИКАТОР ЗАГРУЗКИ ========== -->
<!-- Отображается во время загрузки контента Используется для AJAX-запросов и тяжелых операций -->
<div id="spinner" class="bg-body-secondary">
  <div class="spinner-border text-primary" role="status">
    <span class="visually-hidden">Загрузка...</span>
  </div>
</div>

```


-----

# Файл: layout\components\spinner_modal.html

```
{% load static %}
<!-- ========== ИНДИКАТОР ЗАГРУЗКИ ДЛЯ МОДАЛЬНЫХ ОКОН ========== -->
<!-- Специальный индикатор для модальных окон Автоматически отображается HTMX во время запросов -->
<div id="spinner_modal" class="htmx-indicator bg-body-secondary">
  <div class="spinner-border text-primary" role="status">
    <span class="visually-hidden">Загрузка...</span>
  </div>
</div>

```


-----

# Файл: layout\footer\footer.html

```
{% load static %}
<!-- ========== ПОДВАЛ САЙТА ========== -->
<footer class="footer bg-body-tertiary text-primary pt-5 pb-4">
  <div class="container">
    <div class="row g-4 px-3 px-md-0">
      <!-- Быстрые ссылки -->
      <!-- О компании -->
      {% include 'layout/footer/footer_about.html' %}
      <!-- Навигация -->
      {% include 'layout/footer/footer_navigation.html' %}

      <!-- Ресурсы -->
      {% include 'layout/footer/footer_resources.html' %}
      <!-- Подписка -->
      {% include 'layout/footer/footer_news_subscribe.html' %}
    </div>

    <!-- Копирайт -->
    {% include 'layout/footer/footer_copyright.html' %}
  </div>
</footer>

```


-----

# Файл: layout\footer\footer_about.html

```
{% load static %}
<div class="col-lg-4 col-md-6">
  <div class="footer-brand d-flex align-items-center mb-3">
    <img id="navbar_brand_logo" src="{% static 'img/elements/logo.webp' %}" alt="IdeaHu" class="me-2 me-md-3" style="height: 28px; width: auto;" />
    <span class="h4 mb-0">IntellectPool</span>
  </div>
  <p class="text-muted">Центр идей, созданных на&nbsp;базе РИД.</p>

  <!-- Соцсети -->
  <div class="social-links d-flex align-items-center mt-3">
    <!-- Email -->
    <a href="mailto:info@b-model.pro" class="text-primary me-3" aria-label="Email" target="_blank" rel="noopener noreferrer"><i class="bi bi-envelope-fill fs-5"></i></a>

    <!-- WhatsApp -->
    <a href="https://wa.me/79167536868" class="text-primary me-3" aria-label="WhatsApp" target="_blank" rel="noopener noreferrer"><i class="bi bi-whatsapp fs-5"></i></a>

    <!-- Telegram -->
    <a href="https://t.me/b_model_pro" class="text-primary me-4" aria-label="Telegram" target="_blank" rel="noopener noreferrer"><i class="bi bi-telegram fs-5"></i></a>

    <!-- Telegram-канал IntellectPool -->
    <a href="https://t.me/+Ztz_1ysmG3kyOWFi" class="btn btn-sm btn-primary" aria-label="Telegram Channel" target="_blank" rel="noopener noreferrer"><i class="bi bi-send-fill me-2"></i>Подписаться</a>
  </div>
</div>

```


-----

# Файл: layout\footer\footer_copyright.html

```
{% load static %}
<hr class="my-4 border-gray-700" />
<div class="row align-items-center">
  <div class="col-md-6 text-center text-md-start mb-3 mb-md-0">
    <p class="mb-0 small text-muted">
      &copy; 2025 <a href="https://b-model.pro" class="text-decoration-none text-primary">IntellectPool</a>. Все&nbsp;права&nbsp;защищены.
    </p>
  </div>
  <div class="col-md-6 text-center text-md-end">
    <a href="{% url 'privacy_policy' %}" class="text-decoration-none text-muted hover-white small me-3" hx-get="{% url 'privacy_policy_modal' %}" hx-target="#largeModal-content" hx-trigger="click" data-bs-toggle="modal" data-bs-target="#largeModal">Политика&nbsp;конфиденциальности</a>
    <a href="{% url 'user_agreement' %}" class="text-decoration-none text-muted hover-white small me-3" hx-get="{% url 'user_agreement_modal' %}" hx-target="#largeModal-content" hx-trigger="click" data-bs-toggle="modal" data-bs-target="#largeModal">Пользовательское&nbsp;соглашение</a>
  </div>
</div>

```


-----

# Файл: layout\footer\footer_navigation.html

```
{% load static %}
<div class="col-lg-2 col-md-3 col-sm-6">
  <h5 class="mb-3">Навигация</h5>
  <ul class="list-unstyled text-dark">
    {% comment %} <li class="mb-2 d-block text-start">
      <a class="text-nowrap text-decoration-none" href="{% url 'index' %}#"><i class="bi bi-receipt me-2"></i>Тарифы</a>
    </li> {% endcomment %}
    {% comment %} <li class="mb-2 d-block text-start">
      <a class="text-nowrap text-decoration-none" href="{% url 'index' %}#"><i class="bi bi-newspaper me-2"></i>Новости</a>
    </li> {% endcomment %}
    <li class="mb-2 d-block text-start">
      <a class="text-nowrap text-decoration-none" href="{% url 'index' %}#about"><i class="bi bi-info-circle me-2"></i>О&nbsp;сервисе</a>
    </li>
    <li class="mb-2 d-block text-start">
      <a class="text-nowrap text-decoration-none" href="#"><i class="bi bi-lightbulb me-2"></i>РИД</a>
    </li>
    {% if request.user.is_authenticated %}
      <li class="mb-2 d-block text-start">
        <a class="text-nowrap text-decoration-none" href="{% url 'profile' tab='profile' %}"><i class="bi bi-person-workspace me-2"></i>Личный кабинет</a>
      </li>
      <li class="mb-2 d-block text-start">
        <a class="text-nowrap text-decoration-none" href="{% url 'profile' tab='projects' %}"><i class="bi bi-clipboard-data me-2"></i>Проекты</a>
      </li>
    {% else %}
      <li class="mb-2 d-block text-start">
        <a type="button" class="text-nowrap text-decoration-none" role="button" hx-get="{% url 'profile_login_modal' %}?next={% url 'profile' tab='profile' %}" hx-target="#modal-content" hx-trigger="click" data-bs-toggle="modal" data-bs-target="#modal"><i class="bi bi-person-workspace me-2"></i>Личный кабинет</a>
      </li>
      <li class="mb-2 d-block text-start">
        <a type="button" class="text-nowrap text-decoration-none" role="button" hx-get="{% url 'profile_login_modal' %}?next={% url 'profile' tab='projects' %}" hx-target="#modal-content" hx-trigger="click" data-bs-toggle="modal" data-bs-target="#modal"><i class="bi bi-clipboard-data me-2"></i>Проекты</a>
      </li>
    {% endif %}
  </ul>
</div>

```


-----

# Файл: layout\footer\footer_news_subscribe.html

```
{% load static %}
<div class="col-lg-4 col-md-6">
  <h5 class="mb-3">Рассылка</h5>
  <p class="text-muted">Подпишитесь, чтобы получать полезные материалы и&nbsp;обновления платформы.</p>

  <form class="mt-3">
    <div class="input-group">
      <input type="email" class="form-control bg-gray-800 border-gray-700 text-primary" placeholder="Ваш email" required />
      <button class="btn btn-primary" type="submit"><i class="bi bi-envelope-arrow-up"></i></button>
    </div>
  </form>
</div>

```


-----

# Файл: layout\footer\footer_resources.html

```
{% load static %}
<div class="col-lg-2 col-md-3 col-sm-6">
  <h5 class="mb-3">Ресурсы</h5>
  <ul class="list-unstyled">
    {% comment %} <li class="mb-2 d-block text-start">
      <a class="text-nowrap text-decoration-none" href="{% url 'index' %}#">Документация</a>
    </li> {% endcomment %}
    <li class="mb-2 d-block text-start">
      <a class="text-nowrap text-decoration-none" href="#">Методология</a>
    </li>
    <li class="mb-2 d-block text-start">
      <a class="text-nowrap text-decoration-none" href="#">Стадии проектов</a>
    </li>
    <li class="mb-2 d-block text-start">
      <a class="text-nowrap text-decoration-none" href="#">Ключевые рынки</a>
    </li>
  </ul>
</div>

```


-----

# Файл: layout\header\header.html

```
<!-- ==================== ШАПКА САЙТА ==================== -->
<!--                       
  Основной header сайта с навигацией:
  - Адаптивное меню (коллапсируется в offcanvas на мобильных)
  - Содержит логотип, основное меню и меню пользователя
  - Фиксированная позиция вверху страницы
                      -->
{% load static %}
{% load widget_tweaks %}

<header id="header" class="d-flex align-items-center justify-content-between fixed-top">
  <!-- ========== ОСНОВНАЯ НАВИГАЦИЯ ========== -->
  <nav class="navbar navbar-expand-xl bg-primary fixed-top">
    <div class="container">
      <!-- Логотип и название сайта -->
      {% include 'layout/header/navbar_brand.html' %}

      <!-- Кнопка открытия мобильного меню (offcanvas) -->
      <button class="navbar-toggler" type="button" data-bs-toggle="offcanvas" data-bs-target="#offcanvasNavbar" aria-controls="offcanvasNavbar" aria-label="Переключить навигацию"><i class="bi bi-list fs-2 text-light"></i></button>

      <!-- ========== OFF-CANVAS МЕНЮ (для мобильных) ========== -->
      <div class="offcanvas offcanvas-end bg-primary" tabindex="-1" id="offcanvasNavbar" aria-labelledby="offcanvasNavbarLabel">
        <!-- Шапка offcanvas меню -->
        <div class="offcanvas-header">
          <h5 class="offcanvas-title" id="offcanvasNavbarLabel">{% include 'layout/header/navbar_brand.html' %}</h5>
          <!-- Кнопка закрытия меню -->
          <button type="button" class="btn-close fs-2" data-bs-dismiss="offcanvas" aria-label="Закрыть"><i class="bi bi-x"></i></button>
        </div>

        <!-- Тело offcanvas меню -->
        <div class="offcanvas-body">
          <!-- ========== ГЛАВНОЕ МЕНЮ ========== -->
          <ul class="navbar-nav text-light justify-content-center align-items-start align-items-xl-center flex-grow-1 pe-5 gap-2 gap-xl-4 mb-2 mb-xl-0">
            <!-- Основные пункты меню (подключаются как отдельные компоненты) -->
            {% comment %} {% include 'layout/header/main_menu/home_link.html' %} <!-- Ссылка на главную --> {% endcomment %}
            {% comment %} {% include 'layout/header/main_menu/about_link.html' %} <!-- О сервисе --> {% endcomment %}
            {% comment %} {% include 'layout/header/main_menu/handbook_dropdown_menu.html' %} <!-- Выпадающее меню справочника --> {% endcomment %}
          </ul>
          <!-- ========== КОНЕЦ ГЛАВНОГО МЕНЮ ========== -->

          <!-- Меню пользователя (логин/регистрация или профиль) -->
          {% include 'layout/header/user_menu.html' %}
        </div>
      </div>
      <!-- ========== КОНЕЦ OFF-CANVAS МЕНЮ ========== -->
    </div>
  </nav>
  <!-- ========== КОНЕЦ ОСНОВНОЙ НАВИГАЦИИ ========== -->
</header>

<!-- Заглушка для компенсации фиксированного header'а (чтобы контент не скрывался) -->
<div id="header_plug" class="header_plug bg-primary"></div>

```


-----

# Файл: layout\header\navbar_brand.html

```
{% load static %}
<!-- ========== ЛОГОТИП И НАЗВАНИЕ САЙТА ========== -->
<!-- Компонент бренда в навигационной панели Ссылка на главную страницу -->

<a class="navbar-brand flex-nowrap" href="{% url 'index' %}">
  <!-- Логотип -->
  <img id="navbar_brand_logo" src="{% static 'img/elements/logo.webp' %}" alt="IntellectPool" />

  <!-- Название сайта -->
  <span class="mx-3 fs-4 fw-bold">IntellectPool</span>
</a>

```


-----

# Файл: layout\header\user_menu.html

```
<!-- ==================== МЕНЮ ПОЛЬЗОВАТЕЛЯ ==================== -->
<!--          
Компонент отображает: 
- Для авторизованных: выпадающее меню с профилем и действиями 
- Для гостей: кнопки входа и регистрации Поддерживает: 
- Разные варианты для обычных пользователей и администраторов 
- HTMX для модальных окон авторизации 
         -->
{% load static %}
{% load common_tags %}

<ul class="navbar-nav align-items-xl-center mt-4 mt-xl-0">
  {% if request.user.is_authenticated %}
    <!-- ========== МЕНЮ АВТОРИЗОВАННОГО ПОЛЬЗОВАТЕЛЯ ========== -->
    <li class="nav-item dropdown">
      <!-- Кнопка-триггер выпадающего меню -->
      <a class="nav-link dropdown-toggle d-flex align-items-center" href="#" role="button" data-bs-toggle="dropdown" data-bs-display="static" aria-expanded="false">
        <i class="bi bi-person-lines-fill fs-4 me-2"></i>
        <span class="d-inline-block d-xl-none text-light">Меню пользователя</span>
      </a>

      <!-- Выпадающее меню -->
      <ul class="dropdown-menu dropdown-menu-lg-end">
        <!-- Ссылка на профиль -->
        <li>
          <a class="dropdown-item"
            href="{% url 'profile' tab='profile' %}"
            title="{% if user.first_name and user.last_name %}
              {{ user.first_name }} {{ user.last_name }}
            {% else %}
              {{ user.get_username }}
            {% endif %}">
            <i class="bi bi-person-workspace me-2"></i>Профиль
          </a>
        </li>

        <!-- ========== АДМИНИСТРАТОРСКИЕ ПУНКТЫ ========== -->
        {% if request.user.is_authenticated and user.is_superuser %}
          <li>
            <hr class="dropdown-divider" />
          </li>

          <!-- Панель администратора -->
          <li>
            <a class="dropdown-item" href="{% url 'admin:index' %}" target="_blank"><b><i class="bi bi-sliders2-vertical me-2"></i>Панель администратора</b></a>
          </li>

          <!-- Список пользователей -->
          <li>
            <a class="dropdown-item" href="{% url 'all_users' %}"><i class="bi bi-people me-2"></i>Все пользователи</a>
          </li>

          <!-- Проекты (если компонент существует) -->
          {% if 'projects/components/all_projects_user_menu_item.html'|template_exists %}
            {% include 'projects/components/all_projects_user_menu_item.html' %}
          {% endif %}

          <li>
            <hr class="dropdown-divider" />
          </li>

          <!-- Удаление неактивных профилей -->
          <li>
            <form action="{% url 'delete_inactive_profiles' %}" method="post">
              {% csrf_token %}
              <button type="submit" class="dropdown-item text-danger"><i class="bi bi-trash me-2"></i>Удалить неактивных</button>
            </form>
          </li>
        {% endif %}
        <!-- ========== КОНЕЦ АДМИНИСТРАТОРСКИХ ПУНКТОВ ========== -->

        <!-- Выход из системы -->
        <li>
          <hr class="dropdown-divider" />
        </li>
        <li>
          <form id="logout-form" method="post" action="{% url 'logout' %}">
            {% csrf_token %}
            <button class="dropdown-item" type="submit"><i class="bi bi-box-arrow-right me-2"></i>Выход</button>
          </form>
        </li>
      </ul>
    </li>
    <!-- ========== КОНЕЦ МЕНЮ АВТОРИЗОВАННОГО ПОЛЬЗОВАТЕЛЯ ========== -->
  {% else %}
    <!-- ========== МЕНЮ ГОСТЯ (кнопки входа/регистрации) ========== -->
    <li>
      <div class="d-flex align-self-end align-items-center">
        <!-- Кнопка входа (HTMX + модальное окно) -->
        <div type="button" class="btn btn-sm btn-link text-light me-3" role="button" hx-get="{% url 'profile_login_modal' %}?next={% url 'profile' tab='profile' %}" hx-target="#modal-content" hx-trigger="click" data-bs-toggle="modal" data-bs-target="#modal">
          <i class="bi bi-box-arrow-in-right fs-5 px-1"></i>
        </div>
      </div>
    </li>
    <!-- ========== КОНЕЦ МЕНЮ ГОСТЯ ========== -->
  {% endif %}
</ul>

```


-----

# Файл: layout\header\handbook_dropdown_menu\key_markets_link.html

```
{% load static %}
<!-- ========== ССЫЛКА НА КЛЮЧЕВЫЕ РЫНКИ ========== -->
<!-- Пункт выпадающего меню справочника Ведет на страницу ключевых рынков -->
<li>
  {% comment %} <a class="dropdown-item" href="{% url 'key_markets' %}#"><i class="bi bi-shop-window me-2"></i>Ключевые рынки</a> {% endcomment %}
  <a class="dropdown-item" href="#"><i class="bi bi-shop-window me-2"></i>Ключевые рынки</a>
</li>

```


-----

# Файл: layout\header\handbook_dropdown_menu\methodology_link.html

```
{% load static %}
<!-- ========== ССЫЛКА НА МЕТОДИКУ ========== -->
<!-- Пункт выпадающего меню справочника Ведет на страницу методики -->
<li>
  {% comment %} <a class="dropdown-item" href="{% url 'methodology' %}#"><i class="bi bi-book me-2"></i>Методика</a> {% endcomment %}
  <a class="dropdown-item" href="#"><i class="bi bi-book me-2"></i>Методика</a>
</li>

```


-----

# Файл: layout\header\handbook_dropdown_menu\project_stages_link.html

```
{% load static %}
<!-- ========== ССЫЛКА НА СТАДИИ ПРОЕКТА ========== -->
<!-- Пункт выпадающего меню справочника Ведет на страницу стадий проекта -->
<li>
  {% comment %} <a class="dropdown-item" href="{% url 'project_stages' %}#"><i class="bi bi-bar-chart-steps me-2"></i>Стадии проекта</a> {% endcomment %}
  <a class="dropdown-item" href="#"><i class="bi bi-bar-chart-steps me-2"></i>Стадии проекта</a>
</li>

```


-----

# Файл: layout\header\main_menu\about_link.html

```
{% load static %}
<!-- ========== ССЫЛКА "О СЕРВИСЕ" ========== -->
<!--
  Пункт главного меню навигации
  Ведет на раздел "О сервисе" на главной странице
-->

<li class="nav-item">
  <a class="nav-link btn btn-sm btn-link text-nowrap {% if request.path == '/about' %}active{% endif %}"
      {% if request.path == '/about' %}
          aria-current="page"
      {% else %}
          aria-current="false"
      {% endif %}
      href="{% url 'index' %}#about">
      <i class="bi bi-info-circle me-2"></i>О&nbsp;сервисе
  </a>
</li>

```


-----

# Файл: layout\header\main_menu\contacts_link.html

```
{% load static %}
<!-- ========== ССЫЛКА "КОНТАКТЫ" ========== -->
<!--
  Пункт главного меню навигации
  Ведет на раздел контактов на главной странице
-->

{% comment %} <li class="nav-item">
  <a class="nav-link btn btn-sm btn-link text-nowrap {% if request.path == '/contacts' %}active{% endif %}"
      {% if request.path == '/contacts' %}
          aria-current="page"
      {% else %}
          aria-current="false"
      {% endif %}
      href="{% url 'index' %}#contacts">
      <i class="bi bi-chat-right-dots me-2"></i>Контакты
  </a>
</li> {% endcomment %}

<li class="nav-item">
  <a class="nav-link btn btn-sm btn-link text-nowrap {% if request.path == '/contacts' %}active{% endif %}"
      {% if request.path == '/contacts' %}
          aria-current="page"
      {% else %}
          aria-current="false"
      {% endif %}
      href="{% url 'index' %}#">
      <i class="bi bi-chat-right-dots me-2"></i>Контакты
  </a>
</li>
```


-----

# Файл: layout\header\main_menu\handbook_dropdown_menu.html

```
{% load static %}
<!-- ========== ВЫПАДАЮЩЕЕ МЕНЮ СПРАВОЧНИКА ========== -->
<!-- Компонент выпадающего меню "Справочник" Содержит ссылки на различные справочные материалы -->
<li class="nav-item dropdown">
  <!-- Кнопка-триггер выпадающего меню -->
  <a class="nav-link dropdown-toggle d-flex align-items-center" href="#" role="button" data-bs-toggle="dropdown" data-bs-display="static" aria-expanded="false">
    <i class="bi bi-question-circle me-2"></i>
    <span class="text-light">Справочник</span>
  </a>

  <!-- Содержимое выпадающего меню -->
  <ul class="dropdown-menu dropdown-menu-lg-end">
    <!-- Подключаемые пункты меню -->
    {% include 'layout/header/handbook_dropdown_menu/methodology_link.html' %}
    {% include 'layout/header/handbook_dropdown_menu/project_stages_link.html' %}
    {% include 'layout/header/handbook_dropdown_menu/key_markets_link.html' %}
  </ul>
</li>

```


-----

# Файл: layout\header\main_menu\home_link.html

```
{% load static %}
<!-- ========== ССЫЛКА "ГЛАВНАЯ" ========== -->
<!--
  Основной пункт главного меню навигации
  Ведет на главную страницу
-->

<li class="nav-item">
  <a class="nav-link btn btn-sm btn-link text-nowrap {% if request.path == '/#' %}active{% endif %}"
  {% if request.path == '/#' %}
      aria-current="page"
  {% else %}
      aria-current="false"
  {% endif %}
  href="{% url 'index' %}#">
      <i class="bi bi-house-door me-2 mx-0 mx-xl-2"></i>
      <span class="d-inline-block d-xl-none text-light">Главная</span>
  </a>
</li>
```


-----

# Файл: layout\header\main_menu\projects_link.html

```
{% load static %}
<!-- ========== ССЫЛКА "ПРОЕКТЫ" ========== -->
<!--
  Пункт главного меню навигации
  Доступен только авторизованным пользователям
  Ведет на страницу проектов пользователя
-->

{% if request.user.is_authenticated %}
  <li class="nav-item">
    <a class="nav-link btn btn-sm btn-success text-nowrap {% if request.path == '/projects' %}active{% endif %}"
      {% if request.path == '/projects' %}
        aria-current="page"
      {% else %}
        aria-current="false"
      {% endif %}
      href="{% url 'profile' tab='projects' %}">
      <i class="bi bi-clipboard-data me-2"></i>Проекты
    </a>
  </li>
{% endif %}

```


-----

# Файл: layout\header\main_menu\rids_link.html

```
{% load static %}
<!-- ========== ССЫЛКА "РИД" ========== -->
<!--
  Пункт главного меню навигации
  Ведет на страницу со списком РИД
-->

{% if request.user.is_authenticated %}
  <li class="nav-item">
    <a class="nav-link btn btn-sm btn-success text-nowrap {% if request.path == '/rids' %}active{% endif %}"
      {% if request.path == '/rids' %}
        aria-current="page"
      {% else %}
        aria-current="false"
      {% endif %}
      href="#">
      <i class="bi bi-lightbulb me-2"></i>РИД
    </a>
  </li>
{% endif %}

```


-----

# Файл: layout\header\main_menu\tariffs_link.html

```
{% load static %}
<!-- ========== ССЫЛКА "ТАРИФЫ" ========== -->
<!--
  Пункт главного меню навигации
  Ведет на раздел тарифов на главной странице
-->

{% comment %} <li class="nav-item">
  <a class="nav-link btn btn-sm btn-link text-nowrap {% if request.path == '/tariffs' %}active{% endif %}"
      {% if request.path == '/tariffs' %}
          aria-current="page"
      {% else %}
          aria-current="false"
      {% endif %}
      href="{% url 'index' %}#tariffs">
      <i class="bi bi-receipt me-2"></i>Тарифы
  </a>
</li> {% endcomment %}

```


-----

# Файл: layout\registration\logged_out.html

```
{% extends 'layout/base.html' %}
{% load static %}

{% block title %}
  До свидания!
{% endblock %}

{% block content %}
  <!-- ========== СТРАНИЦА ВЫХОДА ИЗ СИСТЕМЫ ========== -->
  <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <!-- Заголовок -->
    <h2>До свидания!</h2>

    <!-- Сообщение о выходе -->
    <div class="text-center mt-5">
      <p>
        <b>Вы&nbsp;вышли из&nbsp;учетной записи</b>
      </p>
    </div>

    <!-- Кнопка входа снова -->
    <div class="d-flex row justify-content-end px-3 gap-2">
      <a href="{% url 'login' %}" class="btn_submit btn btn-lg btn-primary my-3">Войти снова</a>
    </div>
  </div>
{% endblock %}

```


-----

# Файл: layout\registration\login.html

```
{% extends 'layout/base.html' %}
{% load static %}
{% load widget_tweaks %}

{% block title %}
  Вход
{% endblock %}

{% block content %}
  <!-- ========== СТРАНИЦА АВТОРИЗАЦИИ ========== -->
  <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <!-- Заголовок -->
    <h2>Вход на&nbsp;сайт</h2>

    <!-- Форма входа -->
    <div class="mt-5">
      {% include 'layout/registration/login_form.html' %}
    </div>
  </div>
{% endblock %}

```


-----

# Файл: layout\registration\login_form.html

```
{% load static %}
{% load widget_tweaks %}

<form action="{{ action }}" id="login_form" method="POST" enctype="multipart/form-data" class="form">
  {% csrf_token %}

  <!-- Сообщения об ошибках -->
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

  <!-- Поля формы -->
  <div class="my-3">
    <!-- Поле логина -->
    <div class="form-floating my-3">
      {{ form.username|add_class:'form-control floating'|attr:'id:id_username'|attr:'placeholder:name@example.com' }}
      <label for="{{ form.username.id_for_label }}">{{ form.username.label }}</label>
    </div>

    <!-- Поле пароля -->
    <div class="form-floating my-3">
      {{ form.password|add_class:'form-control floating'|attr:'id:id_password'|attr:'placeholder:Пароль' }}
      <label for="{{ form.password.id_for_label }}">{{ form.password.label_tag }}</label>
      <div id="{{ form.password.id_for_label }}Help" class="form-text">{{ form.password.errors }}</div>
    </div>
  </div>

  <!-- Кнопка отправки -->
  <div class="d-flex row justify-content-end px-3 gap-2">
    <button type="submit" class="btn btn-lg btn_submit btn-primary my-3"><i class="bi bi-box-arrow-in-right pe-2"></i>Войти</button>
  </div>
</form>

```


-----

# Файл: layout\registration\password_reset_complete.html

```
{% extends 'layout/base.html' %}
{% load static %}

{% block title %}
  Восстановление пароля завершено
{% endblock %}

{% block content %}
  <!-- ========== СТРАНИЦА УСПЕШНОГО ВОССТАНОВЛЕНИЯ ПАРОЛЯ ========== -->
  <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <!-- Заголовок -->
    <h2>Восстановление пароля завершено</h2>

    <!-- Сообщение об успехе -->
    <div class="mt-5">
      <p>
        <b>Ваш&nbsp;пароль был&nbsp;сохранен.</b>
      </p>
      <p>Теперь вы&nbsp;можете войти на&nbsp;сайт.</p>
    </div>

    <!-- Кнопка входа -->
    <div class="d-flex row justify-content-end px-3 gap-2">
      <a href="{% url 'login' %}" class="btn btn_submit btn-primary w-auto px-3">Войти</a>
    </div>
  </div>
{% endblock %}

```


-----

# Файл: layout\registration\password_reset_confirm.html

```
{% extends 'layout/base.html' %}
{% load static %}
{% load widget_tweaks %}

{% block title %}
  Создание нового пароля
{% endblock %}

{% block content %}
  <!-- ========== СТРАНИЦА ПОДТВЕРЖДЕНИЯ СБРОСА ПАРОЛЯ ========== -->
  {% if validlink %}
    <!-- Форма для установки нового пароля -->
    <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
      <h2>Введите новый пароль</h2>
      <div class="mt-5">
        <form action="{{ action }}" id="reset_password_form" method="POST" enctype="multipart/form-data" class="form">
          {% csrf_token %}

          <!-- Сообщения об ошибках -->
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

          <!-- Поля формы -->
          <div class="my-3">
            <!-- Новый пароль -->
            <div class="form-floating my-3">
              {{ form.new_password1|add_class:'form-control floating'|attr:'id:id_password1'|attr:'placeholder:Новый пароль' }}
              <label for="id_password1">{{ form.new_password1.label }}</label>
              <div id="password1Help" class="form-text">{{ form.password1.errors }}</div>
            </div>

            <!-- Подтверждение пароля -->
            <div class="form-floating my-3">
              {{ form.new_password2|add_class:'form-control floating'|attr:'id:id_password2'|attr:'placeholder:Новый пароль еще раз' }}
              <label for="id_password2">Новый пароль еще раз</label>
              <div id="password2Help" class="form-text">{{ form.password2.errors }}</div>
            </div>
          </div>

          <!-- Кнопка сохранения -->
          <div class="d-flex row justify-content-end px-3 gap-2">
            <button type="submit" class="btn btn-lg btn_submit btn-primary my-3">Сохранить пароль</button>
          </div>
        </form>
      </div>
    </div>
  {% else %}
    <!-- Сообщение о недействительной ссылке -->
    <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
      <h2>Восстановление пароля невозможно</h2>
      <div class="mt-5">
        <p>
          <b>Ссылка на&nbsp;сброс пароля из&nbsp;e-mail была некорректной.</b>
        </p>
        <p>Возможно, вы&nbsp;уже&nbsp;использовали эту&nbsp;ссылку ранее.</p>
        <p>Пожалуйста, пройдите процедуру восстановления пароля еще&nbsp;раз.</p>
      </div>
      <div class="d-flex row justify-content-end px-3 gap-2">
        <a href="{% url 'password_reset' %}" class="btn btn_submit btn-primary">Восстановить пароль</a>
      </div>
    </div>
  {% endif %}
{% endblock %}

```


-----

# Файл: layout\registration\password_reset_done.html

```
{% extends 'layout/base.html' %}
{% load static %}

{% block title %}
  Письмо для восстановления пароля отправлено
{% endblock %}

{% block content %}
  <!-- ========== СТРАНИЦА ПОДТВЕРЖДЕНИЯ ОТПРАВКИ ПИСЬМА ========== -->
  <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <h2>Восстановление пароля</h2>
    <div class="mt-5">
      <!-- Основное сообщение -->
      <p>
        <b>Письмо с&nbsp;инструкциями по&nbsp;восстановлению пароля отправлено.</b>
      </p>
      <p>Мы&nbsp;отправили вам инструкцию по&nbsp;установке нового пароля на&nbsp;указанный вами e-mail. Вы&nbsp;получите письмо в&nbsp;ближайшее время (если в&nbsp;нашей базе данных есть введенный вами адрес). Следуйте указанным в&nbsp;нем инструкциям, чтобы установить новый пароль и&nbsp;восстановить доступ к&nbsp;своей учетной записи.</p>

      <!-- Дополнительные инструкции -->
      <p>
        Если вы&nbsp;не&nbsp;получили письмо, пожалуйста, убедитесь, что вы&nbsp;ввели адрес с&nbsp;которым вы&nbsp;зарегистрировались, и&nbsp;проверьте папку <b>&laquo;Спам&raquo;</b>.
      </p>
      <p>
        Если вы&nbsp;все еще не&nbsp;можете найти письмо,
        <a class="text-decoration-underline" href="mailto:info@stratman.pro?subject=Проблема%20с%20доступом&body=Добрый%20день!">свяжитесь с&nbsp;нашей службой поддержки</a>
        и&nbsp;мы&nbsp;поможем вам восстановить доступ к&nbsp;вашей учетной записи.
      </p>
      <p>Будьте внимательны при выборе нового пароля: используйте надежные комбинации из&nbsp;букв, цифр и&nbsp;символов, чтобы защитить свою учетную запись от&nbsp;несанкционированного доступа.</p>
      <p>
        Если у&nbsp;вас есть дополнительные вопросы или проблемы,
        <a class="text-decoration-underline" href="mailto:info@stratman.pro?subject=Вопрос%20по%20работе%20сайта&body=Добрый%20день!">обратитесь к&nbsp;нам</a>
        в&nbsp;любое время.
      </p>
      <p>Данную страницу можно закрыть.</p>
      <p>
        <b>Спасибо, что вы&nbsp;с&nbsp;нами!</b>
      </p>
    </div>
  </div>
{% endblock %}

```


-----

# Файл: layout\registration\password_reset_email.html

```
<!DOCTYPE html>
<html lang="en" xmlns="https://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <meta name="x-apple-disable-message-reformatting" />
    <!-- [if !mso]><! -->
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <!-- <![endif] -->
    <title>Сброс пароля для входа на сайт</title>
    <!--    [if mso]> 
    <style type="text/css"> 
    table {border-collapse:collapse;border:0;border-spacing:0;margin:0;} 
    div, td {padding:0;} 
    div {margin:0 !important;} 
    </style> 
    <noscript> 
    <xml> 
    <o:OfficeDocumentSettings> 
    <o:PixelsPerInch>96</o:PixelsPerInch> 
    </o:OfficeDocumentSettings> 
    </xml> 
    </noscript> 
    <![endif]    -->

    <style>
      body {
        width: 100% !important;
        -webkit-text-size-adjust: 100%;
        -ms-text-size-adjust: 100%;
        margin: 0;
        padding: 0;
        line-height: 100%;
      }
      
      [style*='Tahoma'] {
        font-family: Tahoma, Verdana, arial, sans-serif !important;
      }
      
      a {
        color: #559d9c !important;
      }
      
      img {
        outline: none;
        text-decoration: none;
        border: none;
        -ms-interpolation-mode: bicubic;
        max-width: 100% !important;
        margin: 0;
        padding: 0;
        display: block;
      }
      
      table td {
        border-collapse: collapse;
      }
      
      table {
        border-collapse: collapse;
        mso-table-lspace: 0pt;
        mso-table-rspace: 0pt;
      }
      
      @media (max-width: 426px) {
        h1 {
          font-size: 28px !important;
          line-height: 0 !important;
        }
      
        h2 {
          font-size: 18px !important;
          line-height: 23px !important;
        }
      
        .hero-logo {
          width: 85% !important;
        }
      }
      
      @media (max-width: 321px) {
        h1 {
          font-size: 22px !important;
          line-height: 22px !important;
        }
      
        h3 {
          font-size: 20px !important;
          line-height: 25px !important;
        }
      
        h2,
        p,
        a {
          font-size: 16px !important;
          line-height: 20px !important;
        }
      
        .hero-logo {
          width: 100% !important;
        }
      }
      
      @media (max-width: 281px) {
        h1 {
          font-size: 20px !important;
          line-height: 0 !important;
        }
      }
    </style>
  </head>

  <body style="margin:0;padding:0;word-spacing:normal;background-color:#ededed;">
    <div style="font-size:0px;font-color:#ffffff;opacity:0;visibility:hidden;width:0;height:0;display:none;">Подтверждение сброса пароля для сайта &#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp;&#847; &zwnj; &nbsp; &zwnj; &nbsp;&#847; &nbsp;&#847; &zwnj;</div>
    <div role="article" aria-roledescription="email" lang="en" style="-webkit-text-size-adjust:100%;
        -ms-text-size-adjust:100%;
        background-color:#ededed;">
      <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border:0;border-spacing:0;">
        <tr>
          <td align="center">
            <!--    [if mso]> 
                    <table role="presentation" align="center" style="width:650px;"> 
                    <tr> 
                    <td style="padding:0;"> 
                    <![endif]    -->
            <div class="outer" style="width:96%;max-width:650px;margin:0 auto;">
              <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border:0;border-spacing:0;" bgcolor="#29536F">
                <tr>
                  <td style="padding:10px 30px;text-align:center;">
                    <h1 style="color: #ffffff; 
                                        margin-top: 0; 
                                        margin-bottom: 0; 
                                        font-family: Tahoma, Verdana, arial, sans-serif; 
                                        font-size: 36px; font-weight: bold; 
                                        line-height: 45px;">IntellectPool</h1>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding:10px 30px;font-family: Tahoma, Verdana, arial, sans-serif; font-size:24px;line-height:28px;font-weight:bold;">
                    <img src="https://i.ibb.co/Yjx6Z3m/bm-pro-logo.png" width="590" class="hero-logo" alt="Логотип-Домино" style="width:75%;height:auto;" />
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 30px 20px 30px;text-align:center;">
                    <h2 style="color: #ffffff; 
                                        margin-top: 0; 
                                        margin-bottom: 20px; 
                                        font-family: Tahoma, Verdana, arial, sans-serif; 
                                        font-size: 22px; 
                                        font-weight: bold; 
                                        line-height: 25px;">Инструмент моделирования <br />и оценки проектов</h2>
                  </td>
                </tr>
              </table>
            </div>
            <!--    [if mso]> 
                    </td> 
                    </tr> 
                    </table> 
                    <![endif]    -->
          </td>
        </tr>
        <tr>
          <td align="center">
            <!--    [if mso]> 
                    <table role="presentation" align="center" style="width:650px;"> 
                    <tr> 
                    <td style="padding:0;"> 
                    <![endif]    -->
            <div class="outer" style="width:96%;max-width:650px;margin:0 auto;">
              <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border:0;border-spacing:0;" bgcolor="#FFFFFF">
                <tr>
                  <td style="padding:40px 30px 20px 30px;text-align:left;">
                    <h3 style="color: #000000; 
                                        margin-top: 0; 
                                        margin-bottom: 0; 
                                        font-family: Tahoma, Verdana, arial, sans-serif; 
                                        font-size: 26px; font-weight: bold; 
                                        line-height: 33px;">Сброс пароля для входа на сайт</h3>
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 30px;text-align:left;">
                    <p style="color: #000000; 
                                        margin-top: 0; 
                                        margin-bottom: 0; 
                                        font-family: Tahoma, Verdana, arial, sans-serif; 
                                        font-size: 18px; font-weight: bold; 
                                        line-height: 25px;">Добрый день!</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 30px;text-align:left;">
                    <p style="color: #000000; 
                                        margin-top: 0; 
                                        margin-bottom: 0; 
                                        font-family: Tahoma, Verdana, arial, sans-serif; 
                                        font-size: 18px; font-weight: normal; 
                                        line-height: 25px;">Вы&nbsp;получили это письмо, потому что&nbsp;вы (или кто-то другой) запросили восстановление пароля от&nbsp;учётной записи на&nbsp;сайте {{ domain }}, которая связана с&nbsp;адресом электронной почты {{ user.email }}.</p>
                    <p style="color: #000000; 
                                        margin-top: 20px; 
                                        margin-bottom: 0; 
                                        font-family: Tahoma, Verdana, arial, sans-serif; 
                                        font-size: 18px; font-weight: normal; 
                                        line-height: 25px;">Для сброса пароля нажмите на&nbsp;кнопку:</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 30px;text-align:left;">
                    <p style="margin:0;font-family:Tahoma,Verdana,arial,sans-serif;">
                      <!--    [if mso]>
                                        <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{% if request.is_secure %}https{% else %}http{% endif %}://{{ domain }}{% url 'password_reset_confirm' uidb64=uid token=token %}" style="height:50px;v-text-anchor:middle;width:216px;" arcsize="10%" stroke="f" fillcolor="#559D9C">
                                        <w:anchorlock/>
                                        <center style="color:#ffffff;font-family:sans-serif;font-size:16px;font-weight:bold;">Сбросить пароль</center>
                                        </v:roundrect>
                                        <![endif]    -->
                      <!-- [if !mso]> <! -->
                      <a href="<!-- prettier-ignore -->{% if request.is_secure %}
                          
                          
                          
                          https



                        {% else %}
                          
                          
                          
                          http



                        {% endif %}://{{ domain }}{% url 'password_reset_confirm' uidb64=uid token=token %}"
                        style="display:inline-block;padding: 16px 16px; font-size:18px; line-height:18px; text-align:center;text-decoration:none; color: #ffffff; border-radius: 10px; background: #559D9C; mso-padding-alt:0;text-underline-color:#ffffff">
                        <!-- [if mso]><i style="letter-spacing: 16px;mso-font-width:-100%;mso-text-raise:20pt">&nbsp;</i><![endif] -->
                        <span style="mso-text-raise:10pt;font-weight:bold;text-decoration:none;color:#ffffff">Сбросить пароль</span>
                        <!-- [if mso]><i style="letter-spacing: 16px;mso-font-width:-100%">&nbsp;</i><![endif] -->
                      </a>
                      <!-- <![endif] -->
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 30px;text-align:left;">
                    <p style="color: #000000; 
                                        margin-top: 0; 
                                        margin-bottom: 0; 
                                        font-family: Tahoma, Verdana, arial, sans-serif; 
                                        font-size: 18px; font-weight: normal; 
                                        line-height: 25px;">
                      Если вы не отправляли этот запрос, пожалуйста,
                      <a href="mailto:info@b-model.pro?subject=Несанкционированный%20сброс%20пароля&amp;body=Добрый%20день!%0D%0A%0D%0AКто-то%20без%C2%A0моего%20ведома%20запросил%20сброс%20пароля%20от%C2%A0моего%20аккаунта%20в%C2%A0приложении%20&laquo;Бизнес-Модель%C2%A0PRO&raquo;%0D%0AПожалуйста,%20примите%20меры.%0D%0A%0DАккаунт:%20{{ user.email }}" style="font-family: Tahoma, Verdana, arial, sans-serif; 
                                        margin-top: 0; 
                                        margin-bottom: 0; 
                                        color: #375A7F; 
                                        text-decoration: underline; 
                                        font-size: 18px; 
                                        font-weight: normal; 
                                        line-height: 16px;" target="_blank">сообщите об&nbsp;этом</a>!
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 30px 40px 30px;text-align:left;">
                    <p style="color: #000000; 
                                        margin-top: 0; 
                                        margin-bottom: 0; 
                                        font-family: Tahoma, Verdana, arial, sans-serif; 
                                        font-size: 18px; font-weight: normal; 
                                        line-height: 25px;">
                      С уважением, <br />
                      <b>IntellectPool</b>
                    </p>
                  </td>
                </tr>
              </table>
            </div>
            <!--    [if mso]> 
                    </td> 
                    </tr> 
                    </table> 
                    <![endif]    -->
          </td>
        </tr>
        <tr>
          <td align="center">
            <!--    [if mso]> 
                    <table role="presentation" align="center" style="width:650px;"> 
                    <tr> 
                    <td style="padding:0;"> 
                    <![endif]    -->
            <div class="outer" style="width:96%;max-width:650px;margin:0 auto;">
              <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border:0;border-spacing:0;" bgcolor="#29536F">
                <tr>
                  <td style="padding:20px 30px;text-align:center;">
                    <p style="color: #ededed; 
                                        margin-top: 0; 
                                        margin-bottom: 0; 
                                        font-family: Tahoma, Verdana, arial, sans-serif; 
                                        font-size: 18px; font-weight: bold; 
                                        line-height: 25px;">
                      <a href="https://stratman.pro/" style="font-family: Tahoma, Verdana, arial, sans-serif; 
                                        margin-top: 0; 
                                        margin-bottom: 0; 
                                        color: #ededed !important; 
                                        text-decoration: none; 
                                        font-size: 16px; 
                                        font-weight: normal; 
                                        line-height: 16px;" target="_blank">© 2024 ООО "Стратмен.про"</a>
                    </p>
                  </td>
                </tr>
              </table>
            </div>
            <!--    [if mso]> 
                    </td> 
                    </tr> 
                    </table> 
                    <![endif]    -->
          </td>
        </tr>
      </table>
    </div>
  </body>
</html>

```


-----

# Файл: layout\registration\password_reset_form.html

```
{% extends 'layout/base.html' %}
{% load static %}
{% load widget_tweaks %}

{% block title %}
  Сброс пароля
{% endblock %}

{% block content %}
  <!-- ========== ФОРМА ЗАПРОСА СБРОСА ПАРОЛЯ ========== -->
  <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <h2>Сброс пароля</h2>
    <div class="mt-5">
      <form action="{{ action }}" id="password_reset_form" method="POST" enctype="multipart/form-data" class="form">
        {% csrf_token %}

        <!-- Сообщения об ошибках -->
        <div class="my-3">
          <p class="text-danger">
            {% if form.email.errors %}
              {{ form.email.errors }}
            {% endif %}
          </p>
        </div>

        <!-- Поле email -->
        <div class="my-3">
          <div class="form-floating my-3">
            {{ form.email|add_class:'form-control floating'|attr:'id:id_username'|attr:'placeholder:name@example.com' }}
            <label for="id_username">E-mail:</label>
          </div>
          <div class="my-3">
            <p class="text_smaller">Введите почту, привязонную к&nbsp;Вашей учетной записи</p>
          </div>
        </div>

        <!-- Кнопка сброса -->
        <div class="d-flex row justify-content-end px-3 gap-2">
          <button type="submit" class="btn btn-lg btn_submit btn-primary my-3"><i class="bi bi-key-fill"></i>&nbsp;&nbsp;Сбросить пароль</button>
        </div>
      </form>
    </div>
  </div>
{% endblock %}

```


-----

# Файл: layout\registration\password_reset_subject.txt

```
Сброс пароля для входа на сайт
```


-----

# Файл: layout\registration\signup.html

```
{% extends 'layout/base.html' %}
{% load static %}
{% load widget_tweaks %}
{% load django_bootstrap5 %}

{% block title %}
  Регистрация пользователя
{% endblock %}

{% block content %}
  <!-- ========== СТРАНИЦА РЕГИСТРАЦИИ ========== -->
  <div class="container bg-body-tertiary rounded shadow-sm w-auto my-auto p-3 p-lg-4">
    <h2>Регистрация пользователя</h2>
    <div class="mt-5">
      <form action="{{ action }}" id="registration_form" method="POST" enctype="multipart/form-data" class="form">
        {% csrf_token %}

        <!-- Поле email -->
        <div class="form-floating my-3">
          {{ form.email|attr:'id:id_username'|attr:'placeholder:name@example.com' }}
          <label for="{{ form.email.id_for_label }}">{{ form.email.label }}</label>
          {{ form.email.errors }}
        </div>

        <!-- Поле пароля -->
        <div class="form-floating my-3">
          {{ form.password1|attr:'id:id_password1'|attr:'placeholder:Пароль' }}
          <label for="{{ form.password1.id_for_label }}">{{ form.password1.label }}</label>
          <div id="{{ form.password1.id_for_label }}Help" class="form-text">{{ form.password1.help_text }}</div>
          <div id="{{ form.password1.id_for_label }}Help" class="form-text">{{ form.password1.errors }}</div>
        </div>

        <!-- Подтверждение пароля -->
        <div class="form-floating my-3">
          {{ form.password2|attr:'id:id_password2'|attr:'placeholder:Пароль' }}
          <label for="{{ form.password2.id_for_label }}">{{ form.password2.label }}</label>
          <div id="{{ form.password2.id_for_label }}Help" class="form-text">{{ form.password2.help_text }}</div>
          <div id="{{ form.password2.id_for_label }}Help" class="form-text">{{ form.password2.errors }}</div>
        </div>

        <!-- CAPTCHA -->
        <hr class="hr" />
        <p>Подтвердите, что вы не робот:</p>
        <div class="d-flex flex-row align-items-center my-3">
          {{ form.captcha }}<br />
        </div>
        {{ form.captcha.errors }}
        <hr class="hr" />

        <!-- Кнопка регистрации -->
        <div class="d-flex row justify-content-end px-3 gap-2">
          <button type="submit" class="btn btn-lg btn_submit btn-primary my-3"><i class="bi bi-power"></i>&nbsp;&nbsp;Зарегистрироваться</button>
        </div>
      </form>
    </div>
  </div>
{% endblock %}

```
