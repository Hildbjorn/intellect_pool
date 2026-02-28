// ============================================================================
// PROJECT: Основной JavaScript файл
// DESCRIPTION: Инициализация всех компонентов, обработка событий, управление UI
// AUTHOR: Artem Fomin
// ============================================================================

// ----------------------------------------------------------------------------
// SECTION: Конфигурация и константы
// ----------------------------------------------------------------------------

/**
 * Конфигурация приложения
 * @type {Object}
 */
const APP_CONFIG = {
    CSRF_META_SELECTOR: 'meta[name="csrfmiddlewaretoken"]',
    SMALL_SCREEN_BREAKPOINT: 1200,
    ALERT_DISPLAY_DELAY: 2000,
    ALERT_FADE_OUT_DELAY: 300,
    SCROLL_TOP_THRESHOLD: 300,
    SCROLL_TRANSPARENCY_THRESHOLD: 60,
    DADATA_TOKEN: "96e2dc70ca88016a7ab1e758ecd29864cd1e981d",
    PHONE_MASK_TEMPLATE: "+7 (___) ___ ____",

    // Конфигурация для таблицы РИД
    IP_TABLE_CONFIG: {
        STORAGE_KEY_FILTERS: 'ipFilters',
        STORAGE_KEY_COLUMNS: 'visibleColumns',
        POPOVER_OPTIONS: {
            container: 'body',
            html: false,
            placement: 'auto',
            trigger: 'hover focus'
        }
    }
};

// ----------------------------------------------------------------------------
// SECTION: Утилиты и вспомогательные функции
// ----------------------------------------------------------------------------

/**
 * Проверяет, находится ли пользователь на странице списка РИД
 * @returns {boolean}
 */
const isIPListPage = () => {
    return document.getElementById('ipTable') !== null ||
        document.querySelector('[data-ip-table]') !== null ||
        window.location.pathname.includes('/intellectual_property/');
};

/**
 * Проверяет, является ли экран маленьким (мобильным/планшетным)
 * @returns {boolean}
 */
const isSmallScreen = () => window.innerWidth < APP_CONFIG.SMALL_SCREEN_BREAKPOINT;

/**
 * Показывает/скрывает спиннер загрузки
 * @param {boolean} show - показать спиннер
 */
const toggleSpinner = (show) => {
    const spinner = document.getElementById("spinner");
    if (!spinner) return;

    spinner.style.display = show ? "flex" : "none";
    document.body.classList.toggle('lock', show);
};

/**
 * Устанавливает высоту заглушки header для фиксированной навигации
 */
const setHeaderPlugHeight = () => {
    const headerPlug = document.getElementById('header_plug');
    if (!headerPlug) return;

    const navbar = document.querySelector('nav.navbar');
    const header = document.querySelector('header');

    const navbarHeight = navbar?.offsetHeight || 0;
    const headerHeight = header?.offsetHeight || 0;
    const maxHeight = Math.max(navbarHeight, headerHeight);

    headerPlug.style.height = `${maxHeight}px`;
    document.documentElement.style.scrollPaddingTop = `${maxHeight}px`;
};

/**
 * Показывает временное уведомление
 * @param {string} message - Текст сообщения
 * @param {string} type - Тип сообщения (success, danger, warning, info)
 * @param {number} duration - Длительность показа (мс)
 */
const showToast = (message, type = 'success', duration = 3000) => {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    toast.style.zIndex = '1060';
    toast.innerHTML = `
        <i class="bi ${type === 'success' ? 'bi-check-circle' : type === 'danger' ? 'bi-exclamation-circle' : 'bi-info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(toast);

    // Автоматически скрываем через указанное время
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);

    // Обработчик закрытия по кнопке
    toast.querySelector('.btn-close').addEventListener('click', () => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    });
};

// ----------------------------------------------------------------------------
// SECTION: Функционал таблицы РИД
// ----------------------------------------------------------------------------

/**
 * Инициализация поповеров для таблицы РИД
 */
const initializeIPTablePopovers = () => {
    if (!isIPListPage()) return;

    const popoverElements = document.querySelectorAll('#ipTable [data-bs-toggle="popover"]');
    popoverElements.forEach(el => {
        new bootstrap.Popover(el, APP_CONFIG.IP_TABLE_CONFIG.POPOVER_OPTIONS);
    });
};

/**
 * Сохранение состояния фильтров РИД в localStorage
 */
const setupIPFiltersStorage = () => {
    if (!isIPListPage()) return;

    const filterForm = document.getElementById('filter-form');
    if (!filterForm) return;

    // Восстановление фильтров при загрузке
    const savedFilters = localStorage.getItem(APP_CONFIG.IP_TABLE_CONFIG.STORAGE_KEY_FILTERS);
    if (savedFilters) {
        try {
            const filters = JSON.parse(savedFilters);
            Object.keys(filters).forEach(key => {
                const input = filterForm.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = filters[key];
                    // Триггерим событие change для select и radio
                    if (input.tagName === 'SELECT' || input.type === 'radio' || input.type === 'checkbox') {
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            });
        } catch (error) {
            console.warn('Ошибка при восстановлении фильтров:', error);
        }
    }

    // Сохранение фильтров при отправке
    filterForm.addEventListener('submit', function () {
        const formData = new FormData(filterForm);
        const filters = {};
        formData.forEach((value, key) => {
            if (value) filters[key] = value;
        });
        localStorage.setItem(APP_CONFIG.IP_TABLE_CONFIG.STORAGE_KEY_FILTERS, JSON.stringify(filters));
    });

    // Кнопка сброса очищает сохраненные фильтры
    const resetBtn = filterForm.querySelector('a[href="?"]');
    if (resetBtn) {
        resetBtn.addEventListener('click', (e) => {
            localStorage.removeItem(APP_CONFIG.IP_TABLE_CONFIG.STORAGE_KEY_FILTERS);
        });
    }
};

/**
 * Управление видимостью колонок таблицы РИД
 */
const setupIPColumnsVisibility = () => {
    if (!isIPListPage()) return;

    const columnToggle = document.getElementById('columnToggle');
    if (!columnToggle) return;

    // Функция переключения колонки
    const toggleColumn = (columnName, show) => {
        const selector = `th[data-column="${columnName}"], td[data-column="${columnName}"]`;
        document.querySelectorAll(selector).forEach(el => {
            if (show) {
                el.classList.remove('d-none');
            } else {
                el.classList.add('d-none');
            }
        });
    };

    // Загрузка сохраненных настроек
    const savedColumns = localStorage.getItem(APP_CONFIG.IP_TABLE_CONFIG.STORAGE_KEY_COLUMNS);
    if (savedColumns) {
        try {
            const visibleColumns = JSON.parse(savedColumns);
            document.querySelectorAll('th[data-column]').forEach(th => {
                const column = th.dataset.column;
                if (visibleColumns[column] === false) {
                    toggleColumn(column, false);
                    const checkbox = columnToggle.querySelector(`input[value="${column}"]`);
                    if (checkbox) checkbox.checked = false;
                }
            });
        } catch (error) {
            console.warn('Ошибка при восстановлении видимости колонок:', error);
        }
    }

    // Сохранение при изменении
    columnToggle.addEventListener('change', function (e) {
        if (e.target.type === 'checkbox') {
            const column = e.target.value;
            toggleColumn(column, e.target.checked);

            // Сохраняем состояние
            const currentSettings = {};
            document.querySelectorAll('th[data-column]').forEach(th => {
                currentSettings[th.dataset.column] = !th.classList.contains('d-none');
            });
            localStorage.setItem(APP_CONFIG.IP_TABLE_CONFIG.STORAGE_KEY_COLUMNS, JSON.stringify(currentSettings));
        }
    });
};

/**
 * Горячие клавиши для страницы РИД
 */
const setupIPHotkeys = () => {
    if (!isIPListPage()) return;

    document.addEventListener('keydown', function (e) {
        // Ctrl/Cmd + F - фокус на поиск
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.querySelector('[name="name"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        // Escape - сброс фильтров
        if (e.key === 'Escape') {
            const resetBtn = document.querySelector('a[href="?"]');
            if (resetBtn && document.activeElement?.tagName !== 'INPUT') {
                resetBtn.click();
            }
        }
    });
};

/**
 * Обновление статистики таблицы РИД (количество записей и т.д.)
 */
const updateIPTableStats = () => {
    if (!isIPListPage()) return;

    const table = document.getElementById('ipTable');
    if (!table) return;

    const rowCount = table.querySelectorAll('tbody tr').length;
    const statsElement = document.querySelector('[data-ip-stats]');
    if (statsElement) {
        statsElement.textContent = `Записей: ${rowCount}`;
    }
};

// ----------------------------------------------------------------------------
// SECTION: Инициализация сторонних библиотек
// ----------------------------------------------------------------------------

/**
 * Инициализирует Bootstrap компоненты (popovers, tooltips)
 */
const initializeBootstrapComponents = () => {
    // Popovers (общие)
    const popoverElements = document.querySelectorAll('[data-bs-toggle="popover"]:not(#ipTable *)');
    popoverElements.forEach(el => new bootstrap.Popover(el));

    // Tooltips
    const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipElements.forEach(el => new bootstrap.Tooltip(el));
};

/**
 * Инициализирует маску для телефонных номеров
 */
const initializePhoneMask = () => {
    const phoneInputs = document.querySelectorAll('.tel');
    if (!phoneInputs.length) return;

    /**
     * Применяет маску к телефонному номеру
     * @param {Event} event - Событие ввода
     * @param {HTMLInputElement} input - Поле ввода
     * @param {number} keyCode - Код клавиши
     */
    const applyMask = (event, input, keyCode) => {
        // Сохраняем код клавиши для событий keydown
        if (event.keyCode) keyCode = event.keyCode;

        const position = input.selectionStart;

        // Запрещаем удаление кода страны
        if (position < 3 && event.type === 'keydown' && event.key === 'Backspace') {
            event.preventDefault();
            return;
        }

        const template = APP_CONFIG.PHONE_MASK_TEMPLATE;
        let i = 0;
        const def = template.replace(/\D/g, "");
        const value = input.value.replace(/\D/g, "");

        const newValue = template.replace(/[_\d]/g, (char) => {
            return i < value.length ? value.charAt(i++) || def.charAt(i) : char;
        });

        // Удаляем лишние символы (подчеркивания)
        const underscoreIndex = newValue.indexOf("_");
        if (underscoreIndex !== -1) {
            const adjustedIndex = underscoreIndex < 5 ? 3 : underscoreIndex;
            input.value = newValue.slice(0, adjustedIndex);
        } else {
            input.value = newValue;
        }

        // Валидация
        const regex = template.substring(0, input.value.length)
            .replace(/_+/g, (underscores) => `\\d{1,${underscores.length}}`)
            .replace(/[+()]/g, "\\$&");

        const validationRegex = new RegExp(`^${regex}$`);

        if (!validationRegex.test(input.value) ||
            input.value.length < 5 ||
            (keyCode > 47 && keyCode < 58)) {
            input.value = newValue;
        }

        // Очистка при потере фокуса, если номер неполный
        if (event.type === "blur" && input.value.length < 5) {
            input.value = "";
        }
    };

    phoneInputs.forEach(input => {
        let keyCode = null;

        const createEventHandler = (eventType) => (event) => {
            applyMask(event, input, keyCode);
        };

        // Создаем обработчики для каждого типа события
        const handleInput = createEventHandler('input');
        const handleFocus = createEventHandler('focus');
        const handleBlur = createEventHandler('blur');
        const handleKeyDown = (event) => {
            keyCode = event.keyCode;
            applyMask(event, input, keyCode);
        };

        // Добавляем обработчики
        input.addEventListener("input", handleInput);
        input.addEventListener("focus", handleFocus);
        input.addEventListener("blur", handleBlur);
        input.addEventListener("keydown", handleKeyDown);

        // Сохраняем ссылки на обработчики для возможного удаления
        input._maskHandlers = { handleInput, handleFocus, handleBlur, handleKeyDown };
    });
};

// ----------------------------------------------------------------------------
// SECTION: Навигация и меню
// ----------------------------------------------------------------------------

/**
 * Настраивает поведение навигационного меню
 */
const setupNavbarBehavior = () => {
    const navItems = document.querySelectorAll('.nav-item');
    if (!navItems.length) return;

    const handleNavLinkClick = (event) => {
        if (!event.target.classList.contains('dropdown-toggle') && isSmallScreen()) {
            document.querySelector("button.navbar-toggler")?.click();
        }
    };

    const updateNavLinks = () => {
        navItems.forEach(item => {
            item.removeEventListener('click', handleNavLinkClick);
            if (isSmallScreen()) {
                item.addEventListener('click', handleNavLinkClick);
            }
        });
    };

    updateNavLinks();
    window.addEventListener('resize', updateNavLinks);
};

/**
 * Настраивает прозрачность навигации при скролле
 */
const setupNavbarTransparency = () => {
    const navbar = document.querySelector('nav.navbar');
    if (!navbar) return;

    const updateTransparency = () => {
        const shouldBeTransparent = window.scrollY > APP_CONFIG.SCROLL_TRANSPARENCY_THRESHOLD;
        navbar.classList.toggle('transparent', shouldBeTransparent);
    };

    document.addEventListener('scroll', updateTransparency);
    updateTransparency(); // Инициализация начального состояния
};

/**
 * Настраивает навигацию по разделам РИД
 */
const setupRIDNavigation = () => {
    const ridNavbar = document.getElementById('rid-navbar');
    const ridSectionsNav = document.getElementById('rid-sections-nav');

    if (!ridNavbar || !ridSectionsNav) return;

    // Плавная прокрутка к секциям
    ridSectionsNav.querySelectorAll('a').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();

            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                // Обновляем активный пункт меню
                ridSectionsNav.querySelectorAll('a').forEach(a => a.classList.remove('active'));
                this.classList.add('active');

                // Прокручиваем к цели
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });

                // Закрываем мобильное меню на маленьких экранах
                if (isSmallScreen()) {
                    ridNavbar.classList.remove('show');
                }
            }
        });
    });

    // Отслеживание активного раздела при скролле
    const sections = document.querySelectorAll('.rid-section');
    const navLinks = ridSectionsNav.querySelectorAll('a');

    const updateActiveNavLink = () => {
        let currentSectionId = '';

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            if (window.scrollY >= sectionTop - 100) {
                currentSectionId = '#' + section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.toggle('active', link.getAttribute('href') === currentSectionId);
        });
    };

    window.addEventListener('scroll', updateActiveNavLink);

    // Мобильное меню
    const mobileMenuBtn = document.createElement('button');
    mobileMenuBtn.className = 'rid-mobile-menu-btn d-lg-none';
    mobileMenuBtn.innerHTML = '<i class="bi bi-list"></i>';
    mobileMenuBtn.ariaLabel = 'Открыть меню РИД';

    mobileMenuBtn.addEventListener('click', () => {
        ridNavbar.classList.toggle('show');
    });

    document.body.appendChild(mobileMenuBtn);

    // Закрытие меню при клике вне его
    document.addEventListener('click', (e) => {
        const isClickInsideSidebar = ridNavbar.contains(e.target);
        const isClickOnMenuBtn = mobileMenuBtn.contains(e.target);

        if (!isClickInsideSidebar && !isClickOnMenuBtn && ridNavbar.classList.contains('show')) {
            ridNavbar.classList.remove('show');
        }
    });
};

/**
 * Настраивает кнопку "Наверх"
 */
const setupScrollToTopButton = () => {
    const scrollButton = document.getElementById('scrollToTop');
    if (!scrollButton) return;

    window.addEventListener('scroll', () => {
        scrollButton.style.display = window.pageYOffset > APP_CONFIG.SCROLL_TOP_THRESHOLD ? 'block' : 'none';
    });

    scrollButton.addEventListener('click', (e) => {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
};

// ----------------------------------------------------------------------------
// SECTION: Формы и валидация
// ----------------------------------------------------------------------------

/**
 * Настраивает предпросмотр изображений в формах
 */
const setupImagePreview = () => {
    const imagePreview = document.getElementById('image_preview');
    if (!imagePreview) return;

    const imageInput = imagePreview.querySelector('input[type="file"][name="image"]');
    const previewImage = imagePreview.querySelector('img');

    if (imageInput && previewImage) {
        imageInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImage.src = e.target.result;
                    previewImage.style.display = 'block';
                };
                reader.readAsDataURL(file);
            } else {
                previewImage.style.display = 'none';
            }
        });
    }
};

/**
 * Настраивает предпросмотр обложки проекта
 */
const setupProjectCoverPreview = () => {
    const coverInput = document.getElementById('id_cover');
    const coverPreview = document.getElementById('cover_preview_img');

    if (coverInput && coverPreview) {
        coverInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    coverPreview.src = e.target.result;
                    coverPreview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
};

/**
 * Инициализирует формы проектов
 */
const initializeProjectForms = () => {
    setupProjectCoverPreview();
    setupProjectDescriptionHeight();
};

/**
 * Настраивает автозаполнение организаций через DaData для профиля пользователя
 */
const initializeCompanyAutocomplete = () => {
    const companyFields = document.querySelectorAll('.company_field');

    if (!companyFields.length) return;

    companyFields.forEach((field) => {
        const form = field.closest('form');
        let orgDataField = null;

        if (form) {
            // Находим или создаем скрытое поле для данных
            orgDataField = form.querySelector('[data-autocomplete-target="organizationData"]') ||
                form.querySelector('#organization_data') ||
                form.querySelector('[name="organization_data"]');

            if (!orgDataField) {
                orgDataField = document.createElement('input');
                orgDataField.type = 'hidden';
                orgDataField.name = 'organization_data';
                orgDataField.id = 'organization_data';
                orgDataField.setAttribute('data-autocomplete-target', 'organizationData');
                form.appendChild(orgDataField);
            }

            $(field).suggestions({
                token: APP_CONFIG.DADATA_TOKEN,
                type: "PARTY",
                count: 5,

                onSelect: (suggestion) => {
                    // Сохраняем полные данные в скрытое поле
                    if (orgDataField) {
                        orgDataField.value = JSON.stringify(suggestion);

                        // Триггерим изменение, чтобы Django увидел данные
                        orgDataField.dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // Устанавливаем название в поле ввода
                    field.value = suggestion.value;

                    // Триггерим change event для валидации
                    const changeEvent = new Event('change', { bubbles: true });
                    field.dispatchEvent(changeEvent);
                }
            });
        }
    });
};

/**
 * Инициализирует автозаполнение формы организации через DaData
 */
const initializeOrganizationAutocomplete = () => {
    const companyFields = document.querySelectorAll('.company_field');

    companyFields.forEach((companyField) => {
        const form = companyField.closest('form');

        if (!form) {
            console.warn('Поле company_field не находится внутри формы');
            return;
        }

        // Проверяем, что это форма организации (имеет поле name)
        const nameField = form.querySelector('[name="name"]');
        if (!nameField) {
            console.log('Это не форма организации, пропускаем');
            return;
        }

        // Находим все поля формы организации
        const fields = {
            name: nameField,
            full_name: form.querySelector('[name="full_name"]'),
            inn: form.querySelector('[name="inn"]'),
            ogrn: form.querySelector('[name="ogrn"]'),
            okpo: form.querySelector('[name="okpo"]'),
            address: form.querySelector('[name="address"]'),
            director: form.querySelector('[name="director"]'),
            phone: form.querySelector('[name="phone"]'),
            email: form.querySelector('[name="email"]'),
            org_type: form.querySelector('[name="org_type"]'),
            activity_status: form.querySelector('[name="activity_status"]'),
            registration_date: form.querySelector('[name="registration_date"]'),
            is_small_business: form.querySelector('[name="is_small_business"]')
        };

        // Создаем hidden поле для хранения полных данных
        let orgDataField = form.querySelector('[data-autocomplete-target="organizationData"]') ||
            form.querySelector('#organization_data') ||
            form.querySelector('[name="organization_data"]');

        if (!orgDataField) {
            orgDataField = document.createElement('input');
            orgDataField.type = 'hidden';
            orgDataField.name = 'organization_data';
            orgDataField.id = 'organization_data';
            orgDataField.setAttribute('data-autocomplete-target', 'organizationData');
            form.appendChild(orgDataField);
        }

        // Инициализируем DaData suggestions
        try {
            $(companyField).suggestions({
                token: APP_CONFIG.DADATA_TOKEN,
                type: "PARTY",
                count: 5,

                onSelect: (suggestion) => {
                    console.log("Статус:", suggestion.data.state?.status);

                    // Сохраняем полные данные в скрытое поле
                    orgDataField.value = JSON.stringify(suggestion);

                    // Заполняем поля формы
                    fillOrganizationForm(fields, suggestion);

                    // Триггерим события для валидации
                    triggerFormValidation(fields);

                    showToast('Данные организации успешно заполнены!', 'warning');
                },

                onSearchError: (error) => {
                    console.error("Ошибка поиска DaData:", error);

                    if (error && (error.message || '').includes('Unauthorized')) {
                        showToast('Ошибка авторизации DaData. Проверьте токен.', 'danger');
                        // Переключаемся на мок-режим
                        if (!companyField.hasAttribute('data-mock-enabled')) {
                            initializeMockAutocompleteForField(companyField, fields, orgDataField);
                        }
                    }
                }
            });

        } catch (error) {
            showToast('Автозаполнение недоступно. Используйте тестовые данные.', 'warning');
            initializeMockAutocompleteForField(companyField, fields, orgDataField);
        }
    });
};

/**
 * Заполняет поля формы организации данными из DaData
 */
const fillOrganizationForm = (fields, suggestion) => {
    console.groupCollapsed("📋 Данные выбранной организации");
    console.log("Наименование:", suggestion.value);
    console.log("Полные данные:", suggestion);
    console.log("Дата регистрации в state:", suggestion.data.state?.registration_date);
    console.log("employeeCount:", suggestion.data.employee_count);
    console.groupEnd();

    // Основные поля
    if (fields.name) fields.name.value = suggestion.value;

    if (fields.full_name) {
        fields.full_name.value = suggestion.data.name?.full_with_opf ||
            suggestion.data.name?.full ||
            suggestion.value || '';
    }

    if (fields.inn && suggestion.data.inn) {
        fields.inn.value = suggestion.data.inn;
    }

    if (fields.ogrn && suggestion.data.ogrn) {
        fields.ogrn.value = suggestion.data.ogrn;
    }

    if (fields.okpo && suggestion.data.okpo) {
        fields.okpo.value = suggestion.data.okpo;
    }

    if (fields.address && suggestion.data.address?.value) {
        fields.address.value = suggestion.data.address.value;
    }

    if (fields.director && suggestion.data.management?.name) {
        fields.director.value = suggestion.data.management.name;
    }

    // Телефон
    if (fields.phone) {
        let phone = '';
        if (suggestion.data.phones && suggestion.data.phones.length > 0) {
            const phoneItem = suggestion.data.phones[0];
            phone = typeof phoneItem === 'object' ? phoneItem.value : phoneItem;
            // Очищаем для маски
            phone = phone.replace(/\D/g, '');
        }
        fields.phone.value = phone;

        // Применяем маску
        if (fields.phone.classList.contains('tel')) {
            setTimeout(() => {
                fields.phone.dispatchEvent(new Event('input', { bubbles: true }));
            }, 100);
        }
    }

    // Email
    if (fields.email) {
        let email = '';
        if (suggestion.data.emails && suggestion.data.emails.length > 0) {
            const emailItem = suggestion.data.emails[0];
            const emailValue = typeof emailItem === 'object' ? emailItem.value : emailItem;
            if (emailValue && emailValue.includes('@')) {
                email = emailValue;
            }
        }
        fields.email.value = email;
    }

    // Тип организации (оставляем как было)
    if (fields.org_type) {
        const orgTypeMapping = {
            'LEGAL': 'LEGAL',
            'INDIVIDUAL': 'IE',
            'SOLE_PROPRIETOR': 'IE',
            'FOREIGN': 'FOREIGN',
            'PHYSICAL': 'PHYSICAL'
        };
        fields.org_type.value = orgTypeMapping[suggestion.data.type] || 'LEGAL';
    }

    // ============ СТАТУС ДЕЯТЕЛЬНОСТИ ============
    if (fields.activity_status) {
        const statusMapping = {
            'ACTIVE': 'ACTIVE',
            'LIQUIDATING': 'LIQUIDATED',
            'LIQUIDATED': 'LIQUIDATED',
            'BANKRUPT': 'BANKRUPT',
            'REORGANIZING': 'REORGANIZING'
        };

        // Берем статус из данных DaData и маппим его
        const daDataStatus = suggestion.data.state?.status || 'ACTIVE';
        let mappedStatus = statusMapping[daDataStatus] || 'ACTIVE';

        // Если нет точного соответствия, пытаемся определить по коду или названию
        if (!statusMapping[daDataStatus]) {
            if (daDataStatus.includes('ACTIVE')) {
                mappedStatus = 'ACTIVE';
            } else if (daDataStatus.includes('LIQUIDAT')) {
                mappedStatus = 'LIQUIDATED';
            } else if (daDataStatus.includes('BANKRUPT')) {
                mappedStatus = 'BANKRUPT';
            } else if (daDataStatus.includes('REORGAN')) {
                mappedStatus = 'REORGANIZING';
            } else {
                mappedStatus = 'ACTIVE'; // значение по умолчанию
            }
        }

        fields.activity_status.value = mappedStatus;
        console.log(`Статус деятельности: ${daDataStatus} -> ${mappedStatus}`);

        // Триггерим событие change для обновления UI
        setTimeout(() => {
            fields.activity_status.dispatchEvent(new Event('change', { bubbles: true }));
        }, 50);
    }

    // ============ ДАТА РЕГИСТРАЦИИ ============
    if (fields.registration_date && suggestion.data.state?.registration_date) {
        try {
            const regDate = new Date(suggestion.data.state.registration_date);
            if (!isNaN(regDate.getTime())) {
                const year = regDate.getFullYear();
                const month = String(regDate.getMonth() + 1).padStart(2, '0');
                const day = String(regDate.getDate()).padStart(2, '0');
                fields.registration_date.value = `${year}-${month}-${day}`;
            } else {
                console.warn('Не удалось распарсить дату регистрации:', suggestion.data.state.registration_date);
            }
        } catch (error) {
            console.error('Ошибка при обработке даты регистрации:', error);
        }
    } else if (fields.registration_date) {
        console.warn('Дата регистрации не найдена в данных DaData');
    }

    // ============ МСП (is_small_business) ============
    if (fields.is_small_business) {
        // Получаем количество сотрудников из данных DaData
        const employeeCount = suggestion.data.employee_count;

        // Определяем статус МСП:
        // 1. Если employee_count отсутствует (undefined) или null - НЕ МСП (false)
        // 2. Если employee_count > 250 - НЕ МСП (false)
        // 3. Если employee_count <= 250 - МСП (true)
        const isSmallBusiness = (employeeCount !== undefined &&
            employeeCount !== null &&
            employeeCount <= 250);

        console.log(`Данные МСП: employee_count=${employeeCount}, is_small_business=${isSmallBusiness}`);

        // Поле может быть checkbox или select
        if (fields.is_small_business.type === 'checkbox') {
            fields.is_small_business.checked = isSmallBusiness;
        } else if (fields.is_small_business.tagName === 'SELECT') {
            // Для select выбираем значение
            fields.is_small_business.value = isSmallBusiness.toString();
        } else if (fields.is_small_business.type === 'radio') {
            // Для radio кнопок
            const radioButtons = form.querySelectorAll(`[name="${fields.is_small_business.name}"]`);
            radioButtons.forEach(radio => {
                if (radio.value === isSmallBusiness.toString()) {
                    radio.checked = true;
                }
            });
        } else {
            // Для других типов полей (text, hidden и т.д.)
            fields.is_small_business.value = isSmallBusiness.toString();
        }

        // Триггерим событие change для обновления UI
        setTimeout(() => {
            fields.is_small_business.dispatchEvent(new Event('change', { bubbles: true }));
            fields.is_small_business.dispatchEvent(new Event('input', { bubbles: true }));
        }, 50);
    }

    // Триггерим валидацию для всех полей
    triggerFormValidation(fields);
};


/**
 * Триггерит события валидации для полей формы
 */
const triggerFormValidation = (fields) => {
    Object.values(fields).forEach(field => {
        if (field) {
            setTimeout(() => {
                field.dispatchEvent(new Event('change', { bubbles: true }));
                field.dispatchEvent(new Event('blur', { bubbles: true }));
            }, 50);
        }
    });
};

/**
 * Обработчик отправки формы профиля с отладкой
 */
const setupProfileFormHandlers = () => {
    const profileForm = document.getElementById('profile_form');
    if (!profileForm) return;

    profileForm.addEventListener('submit', function (e) {
        // Отладка перед отправкой
        const orgDataField = this.querySelector('[data-autocomplete-target="organizationData"]');
        if (orgDataField && orgDataField.value) {
            try {
                const orgData = JSON.parse(orgDataField.value);
                console.log("📤 Отправка данных организации:", {
                    name: orgData.value,
                    inn: orgData.data?.inn,
                    ogrn: orgData.data?.ogrn
                });
            } catch (error) {
                console.warn("⚠️ Не удалось разобрать данные организации:", error);
                // Очищаем некорректные данные
                orgDataField.value = '';
            }
        }
    });
};

/**
 * Настраивает AJAX отправку форм
 */
const setupAjaxForms = () => {
    $('form.ajax-form').on('submit', function (event) {
        event.preventDefault();
        const $form = $(this);

        // Очищаем предыдущие ошибки
        $form.find('.errorlist, .error-message').remove();

        $.ajax({
            type: 'POST',
            url: $form.attr('action'),
            data: $form.serialize(),
            success: (response) => {
                $('#messages').empty().append(response.message_html);
                $form.replaceWith(response.form_html);

                // Реинициализация после замены формы
                setupAjaxForms();
                toggleSpinner(false);
                setTimeout(() => showAlertMessages(APP_CONFIG.ALERT_DISPLAY_DELAY), 100);
            },
            error: (xhr, status, error) => {
                console.error('Ошибка при отправке формы:', xhr.statusText, error);
                toggleSpinner(false);
            }
        });
    });
};

/**
 * Настраивает обработку кнопок отправки и спиннер
 */
const setupFormSubmitHandlers = () => {
    const submitButtons = document.querySelectorAll(".btn_submit");

    if (!submitButtons.length) return;

    submitButtons.forEach(button => {
        button.addEventListener("click", (e) => {
            const form = button.closest('form');
            if (!form) return;

            // Проверяем, есть ли у формы hx-indicator
            const hasHxIndicator = form.hasAttribute('hx-indicator');

            // Включаем спиннер ТОЛЬКО если это не HTMX форма с индикатором
            if (!hasHxIndicator && form.checkValidity()) {
                toggleSpinner(true);
            }
        });
    });
};

/**
 * Выравнивает высоту описания проекта
 */
const setupProjectDescriptionHeight = () => {
    const imagePreview = document.getElementById('image_preview');
    const descriptionCol = document.querySelector('.project_description_col');

    if (!imagePreview || !descriptionCol) return;

    const updateHeight = () => {
        if (window.innerWidth >= 992) {
            descriptionCol.style.height = `${imagePreview.offsetHeight}px`;
        } else {
            descriptionCol.style.height = '';
        }
    };

    updateHeight();
    window.addEventListener('resize', updateHeight);
};

// ----------------------------------------------------------------------------
// SECTION: Мок-функции для DaData (если нужны)
// ----------------------------------------------------------------------------

/**
 * Инициализирует мок-режим автозаполнения для поля
 */
const initializeMockAutocompleteForField = (field, fields, orgDataField) => {
    // Упрощенная версия для тестирования
    field.setAttribute('data-mock-enabled', 'true');

    // Добавляем подсказки для тестирования
    const mockData = [
        { value: 'ПАО "Газпром"', inn: '7736050003', ogrn: '1027700070518' },
        { value: 'ПАО "ЛУКОЙЛ"', inn: '7708004767', ogrn: '1027700035769' },
        { value: 'ПАО "Сбербанк России"', inn: '7707083893', ogrn: '1027700132195' }
    ];

    // Создаем простой datalist для автозаполнения
    const datalistId = 'mock-datalist-' + Math.random().toString(36).substr(2, 9);
    const datalist = document.createElement('datalist');
    datalist.id = datalistId;

    mockData.forEach(item => {
        const option = document.createElement('option');
        option.value = item.value;
        datalist.appendChild(option);
    });

    field.parentNode.appendChild(datalist);
    field.setAttribute('list', datalistId);

    field.addEventListener('change', () => {
        const selected = mockData.find(item => item.value === field.value);
        if (selected) {
            if (fields.inn) fields.inn.value = selected.inn;
            if (fields.ogrn) fields.ogrn.value = selected.ogrn;
            if (orgDataField) orgDataField.value = JSON.stringify(selected);
        }
    });
};

// ----------------------------------------------------------------------------
// SECTION: Сообщения и уведомления
// ----------------------------------------------------------------------------

/**
 * Показывает сообщения с автозакрытием
 * @param {number} delay - задержка перед скрытием (мс)
 */
const showAlertMessages = (delay = APP_CONFIG.ALERT_DISPLAY_DELAY) => {
    const alertContainer = document.querySelector('.alert_messages');
    const messagesContainer = document.getElementById('messages');

    if (!alertContainer || !messagesContainer) return;

    // Показываем сообщения
    alertContainer.classList.add('show');

    // Настройка автозакрытия
    const hideTimeout = setTimeout(() => {
        alertContainer.classList.remove('show');

        setTimeout(() => {
            messagesContainer.innerHTML = '';
        }, APP_CONFIG.ALERT_FADE_OUT_DELAY);
    }, delay);

    // Обработка кнопок закрытия
    document.querySelectorAll('.btn-close').forEach(button => {
        const closeHandler = () => {
            clearTimeout(hideTimeout);
            alertContainer.classList.remove('show');

            setTimeout(() => {
                messagesContainer.innerHTML = '';
                button.removeEventListener('click', closeHandler);
            }, APP_CONFIG.ALERT_FADE_OUT_DELAY);
        };

        button.addEventListener('click', closeHandler);
    });
};

// ----------------------------------------------------------------------------
// SECTION: UI эффекты и анимации
// ----------------------------------------------------------------------------

/**
 * Настраивает анимацию в hero-секции
 */
const setupHeroAnimation = () => {
    const animatedElement = document.querySelector('.animated');
    if (!animatedElement) return;

    const animations = ['move-up', 'move-down', 'move-left', 'move-right'];

    const applyRandomAnimation = () => {
        const randomIndex = Math.floor(Math.random() * animations.length);
        const animationClass = animations[randomIndex];

        animatedElement.classList.remove(...animations);
        animatedElement.classList.add(animationClass);

        setTimeout(() => {
            animatedElement.classList.remove(animationClass);
        }, 2000);
    };

    setInterval(applyRandomAnimation, 1000);
};

// ----------------------------------------------------------------------------
// SECTION: HTMX интеграция
// ----------------------------------------------------------------------------

/**
 * Настраивает CSRF токены для HTMX запросов
 */
const setupHTMXCSRF = () => {
    document.addEventListener('htmx:configRequest', (event) => {
        const csrfToken = document.querySelector(APP_CONFIG.CSRF_META_SELECTOR)?.content;

        if (csrfToken) {
            event.detail.headers['X-CSRFToken'] = csrfToken;
        } else {
            console.warn("CSRF Token not found in meta tag.");
        }
    });
};

/**
 * Обработчик для динамического контента после HTMX обновлений
 */
const setupHTMXContentHandlers = () => {
    document.addEventListener('htmx:afterSwap', () => {
        // Реинициализация компонентов для нового контента
        initializeCompanyAutocomplete();
        initializeOrganizationAutocomplete();
        initializePhoneMask();
        setupAjaxForms();
        setupFormSubmitHandlers();
        initializeProjectForms();

        // Реинициализация таблицы РИД, если мы на соответствующей странице
        if (isIPListPage()) {
            initializeIPTablePopovers();
            setupIPColumnsVisibility();
            updateIPTableStats();
        }

        setTimeout(() => showAlertMessages(APP_CONFIG.ALERT_DISPLAY_DELAY), 100);
    });

    // Специальная обработка модальных окон
    document.addEventListener('htmx:afterSwap', (event) => {
        if (event.detail.target.id === 'modal-content') {
            setupProjectCoverPreview();
            initializeOrganizationAutocomplete();

            // Если в модалке есть таблица РИД
            if (isIPListPage()) {
                initializeIPTablePopovers();
            }
        }
    });

    // Дополнительно: обрабатываем ошибки запросов
    document.addEventListener('htmx:responseError', () => {
        toggleSpinner(false);
    });

    document.addEventListener('htmx:sendError', () => {
        toggleSpinner(false);
    });
};

// ----------------------------------------------------------------------------
// SECTION: Главная инициализация
// ----------------------------------------------------------------------------

/**
 * Основная функция инициализации всех компонентов
 */
const initializeApp = () => {
    // Настройка HTMX
    setupHTMXCSRF();
    setupHTMXContentHandlers();

    // Навигация
    setupNavbarBehavior();
    setupNavbarTransparency();
    setupRIDNavigation();
    setupScrollToTopButton();

    // Формы и ввод данных
    initializeBootstrapComponents();
    setupFormSubmitHandlers();
    initializeCompanyAutocomplete();
    initializeOrganizationAutocomplete();
    setupProfileFormHandlers();
    initializePhoneMask();
    setupAjaxForms();
    initializeProjectForms();
    setupImagePreview();

    // UI эффекты
    setupHeroAnimation();
    setupProjectDescriptionHeight();

    // Утилиты
    setHeaderPlugHeight();
    toggleSpinner(false);

    // Инициализация таблицы РИД, если мы на соответствующей странице
    if (isIPListPage()) {
        initializeIPTablePopovers();
        setupIPFiltersStorage();
        setupIPColumnsVisibility();
        setupIPHotkeys();
        updateIPTableStats();
    }

    // Показ сообщений с небольшой задержкой
    setTimeout(() => showAlertMessages(APP_CONFIG.ALERT_DISPLAY_DELAY), 100);
};

/**
 * Инициализация при загрузке страницы
 */
document.addEventListener('DOMContentLoaded', initializeApp);

/**
 * Обработка полной загрузки страницы (изображения, шрифты)
 */
window.addEventListener('load', () => {
    setHeaderPlugHeight();
    setupProjectDescriptionHeight();

    // Обновление статистики таблицы РИД после полной загрузки
    if (isIPListPage()) {
        updateIPTableStats();
    }
});

/**
 * Обработка изменения размеров окна
 */
window.addEventListener('resize', () => {
    setHeaderPlugHeight();
    setupProjectDescriptionHeight();
});

// ----------------------------------------------------------------------------
// EXPORTS (для тестирования и отладки)
// ----------------------------------------------------------------------------
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        isSmallScreen,
        toggleSpinner,
        setHeaderPlugHeight,
        initializeApp,
        APP_CONFIG,
        isIPListPage
    };
}