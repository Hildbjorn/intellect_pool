from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from common.admin_utils import AdminDisplayMixin, AdminImageMixin
from intellectual_property.models.models_ip import AdditionalPatent, IPImage, IPObject, IPType, ProtectionDocumentType


@admin.register(ProtectionDocumentType)
class ProtectionDocumentTypeAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели ProtectionDocumentType.
    """
    list_display = [
        'name',
        'description',
        'slug',
    ]
    
    search_fields = [
        'name',
        'description',
        'slug',
    ]
    
    list_filter = [
        'name',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description'),
            'description': _('Основная информация о виде охранного документа')
        }),
        (_('URL параметры'), {
            'fields': ('slug',),
            'description': _('Параметры для формирования URL'),
            'classes': ('wide',),
        }),
    )
    
    readonly_fields = ['slug']
    
    def get_queryset(self, request):
        """
        Оптимизация запросов к БД.
        """
        return super().get_queryset(request).annotate(
            ip_types_count=models.Count('ip_types')
        )


@admin.register(IPType)
class IPTypeAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели IPType.
    """
    # Поля для отображения в списке
    list_display = [
        'name',
        'description',
        'protection_document_link',
        'validity_duration',
        'slug',
    ]
    
    # Поля для поиска
    search_fields = [
        'name',
        'description',
        'slug',
        'protection_document_type__name',
    ]
    
    # Фильтры в правой панели
    list_filter = [
        'protection_document_type',
        'name',
    ]
    
    # Поля для редактирования
    fieldsets = (
        (None, {
            'fields': ('name', 'description'),
            'description': _('Основная информация о типе РИД')
        }),
        (_('Срок действия'), {
            'fields': ('validity_duration',),
            'description': _('Срок действия охранного документа'),
            'classes': ('wide',),
        }),
        (_('Связи'), {
            'fields': ('protection_document_type',),
            'description': _('Связь с видом охранного документа'),
            'classes': ('wide',),
        }),
        (_('URL параметры'), {
            'fields': ('slug',),
            'description': _('Параметры для формирования URL'),
            'classes': ('wide',),
        }),
    )
    
    # Поля только для чтения
    readonly_fields = ['slug']
    
    # Фильтры по связанным полям
    autocomplete_fields = ['protection_document_type']
    
    # Группировка по полям
    list_display_links = ['name']
    
    def get_queryset(self, request):
        """
        Оптимизация запросов к БД.
        """
        return super().get_queryset(request).select_related(
            'protection_document_type'
        )
    
    def protection_document_link(self, obj):
        """
        Ссылка на связанный вид охранного документа.
        Универсальный метод получения URL.
        """
        if obj.protection_document_type:
            try:
                # Способ 1: Пробуем стандартный формат admin:app_model_action
                url = reverse(
                    f'admin:{obj.protection_document_type._meta.app_label}_{obj.protection_document_type._meta.model_name}_change',
                    args=[obj.protection_document_type.id]
                )
            except:
                try:
                    # Способ 2: Пробуем формат без app_label
                    url = reverse(
                        f'{obj.protection_document_type._meta.model_name}_change',
                        args=[obj.protection_document_type.id]
                    )
                except:
                    try:
                        # Способ 3: Пробуем использовать django.contrib.admin.utils.get_admin_url
                        from django.contrib.admin.utils import get_admin_url
                        url = get_admin_url(admin.site, obj.protection_document_type, 'change')
                    except:
                        # Если ничего не работает, возвращаем просто текст без ссылки
                        return obj.protection_document_type.name
            
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.protection_document_type.name
            )
        return '-'
    protection_document_link.short_description = _('Вид охранного документа')
    protection_document_link.admin_order_field = 'protection_document_type__name'
    
    def get_readonly_fields(self, request, obj=None):
        """
        Динамическое определение readonly полей.
        """
        readonly_fields = list(self.readonly_fields)
        
        if obj:  # Редактирование существующего объекта
            readonly_fields.extend(['slug'])
        
        return readonly_fields
    
    def get_list_filter(self, request):
        """
        Динамическое определение фильтров.
        """
        list_filter = list(self.list_filter)
        return list_filter
    
    def save_model(self, request, obj, form, change):
        """
        Действия при сохранении модели.
        """
        super().save_model(request, obj, form, change)
        
        action = _('обновлен') if change else _('создан')
        self.message_user(
            request,
            _('Тип РИД "{}" успешно {}').format(obj.name, action),
            level='SUCCESS'
        )
    
    def response_change(self, request, obj):
        """
        Настройка ответа после изменения.
        """
        if "_continue" in request.POST:
            self.message_user(
                request,
                _('Продолжаем редактирование "{}"').format(obj.name),
                level='INFO'
            )
        return super().response_change(request, obj)


@admin.register(AdditionalPatent)
class AdditionalPatentAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для дополнительных патентов.
    """
    list_display = [
        'patent_number',
        'patent_date',
        'description_short',
        'ip_objects_count',
    ]
    
    search_fields = [
        'patent_number',
        'description',
    ]
    
    list_filter = [
        'patent_date',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('patent_number', 'patent_date', 'description')
        }),
    )
    
    def description_short(self, obj):
        """Короткое описание для списка"""
        if obj.description and len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description
    description_short.short_description = _('Описание')
    
    def get_queryset(self, request):
        """Оптимизация запросов с подсчетом связанных РИД"""
        return super().get_queryset(request).annotate(
            ip_objects_count=models.Count('ip_objects')
        )
    
    def ip_objects_count(self, obj):
        """Количество РИД, связанных с этим патентом"""
        count = getattr(obj, 'ip_objects_count', 0)
        if count:
            url = reverse('admin:intellectual_property_ipobject_changelist') + f'?additional_patents__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    ip_objects_count.short_description = _('Связанных РИД')
    ip_objects_count.admin_order_field = 'ip_objects_count'


@admin.register(IPImage)
class IPImageAdmin(AdminImageMixin, admin.ModelAdmin):
    """
    Административный интерфейс для изображений РИД.
    """
    list_display = [
        'image_thumbnail',
        'title',
        'is_main',
        'sort_order',
        'ip_objects_count',
    ]
    
    search_fields = [
        'title',
        'description',
    ]
    
    list_filter = [
        'is_main',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('image', 'title', 'description', 'is_main', 'sort_order')
        }),
    )
    
    def get_queryset(self, request):
        """Оптимизация запросов с подсчетом связанных РИД"""
        return super().get_queryset(request).annotate(
            ip_objects_count=models.Count('ip_objects')
        )
    
    def ip_objects_count(self, obj):
        """Количество РИД, связанных с этим изображением"""
        count = getattr(obj, 'ip_objects_count', 0)
        if count:
            url = reverse('admin:intellectual_property_ipobject_changelist') + f'?images__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    ip_objects_count.short_description = _('Связанных РИД')
    ip_objects_count.admin_order_field = 'ip_objects_count'


@admin.register(IPObject)
class IPObjectAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Административный интерфейс для объектов РИД.
    """
    list_display = [
        'name',
        'ip_type',
        'registration_number',
        'actual_badge',
        'application_date',
        'expiration_date',
        'created_at_display',
    ]
    
    list_filter = [
        'ip_type',
        'actual',
        'application_date',
        'registration_date',
        'expiration_date',
    ]
    
    search_fields = [
        'name',
        'registration_number',
        'ea_application_number',
        'pct_application_number',
        'description',
        'abstract',
        'claims',
    ]
    
    filter_horizontal = [
        'authors',
        'owner_persons',
        'owner_organizations',
        'owner_foivs',
        'first_usage_countries',
        'additional_patents',
        'images',
        'programming_languages',
        'dbms',
        'operating_systems',
    ]
    
    autocomplete_fields = [
        'ip_type',
        'paris_convention_priority_country',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'all_owners_display',
    ]
    
    fieldsets = (
        (_('📋 Основная информация'), {
            'fields': (
                'name',
                'ip_type',
                'actual',
            )
        }),
        
        (_('👥 Авторы и правообладатели'), {
            'fields': (
                'authors',
                'owner_persons',
                'owner_organizations',
                'owner_foivs',
                'all_owners_display',
            ),
            'classes': ('wide',),
        }),
        
        (_('📅 Даты и сроки'), {
            'fields': (
                ('creation_year', 'publication_year', 'update_year'),
                ('application_date', 'registration_date'),
                ('patent_starting_date', 'expiration_date'),
            ),
            'classes': ('wide',),
        }),
        
        (_('🔢 Номера и идентификаторы'), {
            'fields': (
                'registration_number',
                'revoked_patent_number',
                'publication_url',
            ),
            'classes': ('wide',),
        }),
        
        (_('🌍 Евразийская заявка'), {
            'fields': (
                'ea_application_number',
                'ea_application_date',
                ('ea_application_publish_number', 'ea_application_publish_date'),
            ),
            'classes': ('collapse',),
        }),
        
        (_('🌐 PCT заявка'), {
            'fields': (
                'pct_application_number',
                'pct_application_date',
                ('pct_application_publish_number', 'pct_application_publish_date'),
                'pct_application_examination_start_date',
            ),
            'classes': ('collapse',),
        }),
        
        (_('🏛️ Парижская конвенция'), {
            'fields': (
                'paris_convention_priority_number',
                'paris_convention_priority_date',
                'paris_convention_priority_country',
            ),
            'classes': ('collapse',),
        }),
        
        (_('📍 Использование топологии'), {
            'fields': (
                'first_usage_date',
                'first_usage_countries',
            ),
            'classes': ('collapse',),
        }),
        
        (_('📄 Текстовые описания'), {
            'fields': (
                'abstract',
                'claims',
                'description',
                'source_code_deposit',
            ),
            'classes': ('wide',),
        }),
        
        (_('📎 Связанные объекты'), {
            'fields': (
                'additional_patents',
                'images',
            ),
            'classes': ('wide',),
        }),
        
        (_('💻 IT-специфика'), {
            'fields': (
                'programming_languages',
                'dbms',
                'operating_systems',
            ),
            'classes': ('collapse',),
        }),
        
        (_('⚙️ Системная информация'), {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    def actual_badge(self, obj):
        """Отображение статуса действия правовой охраны"""
        if obj.actual:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 7px; border-radius: 10px;">✓ Действует</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 7px; border-radius: 10px;">✗ Не действует</span>'
        )
    actual_badge.short_description = _('Статус')
    actual_badge.admin_order_field = 'actual'
    
    def all_owners_display(self, obj):
        """Отображение всех правообладателей в детальной странице"""
        owners = obj.all_owners
        if owners:
            html = ['<ul style="margin: 0; padding-left: 20px;">']
            for owner in owners:
                # Пытаемся получить ссылку на админку
                try:
                    app_label = owner._meta.app_label
                    model_name = owner._meta.model_name
                    url = reverse(f'admin:{app_label}_{model_name}_change', args=[owner.pk])
                    html.append(f'<li><a href="{url}">{owner}</a></li>')
                except:
                    html.append(f'<li>{owner}</li>')
            html.append('</ul>')
            return format_html(''.join(html))
        return '-'
    all_owners_display.short_description = _('Все правообладатели')
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related(
            'ip_type',
            'paris_convention_priority_country',
        ).prefetch_related(
            'authors',
            'owner_persons',
            'owner_organizations',
            'owner_foivs',
            'first_usage_countries',
            'programming_languages',
            'dbms',
            'operating_systems',
        )
    
    actions = ['mark_as_actual', 'mark_as_not_actual']
    
    @admin.action(description=_('✅ Отметить как действующие'))
    def mark_as_actual(self, request, queryset):
        updated = queryset.update(actual=True)
        self.message_user(request, _('Обновлено {} объектов РИД').format(updated))
    
    @admin.action(description=_('❌ Отметить как недействующие'))
    def mark_as_not_actual(self, request, queryset):
        updated = queryset.update(actual=False)
        self.message_user(request, _('Обновлено {} объектов РИД').format(updated))