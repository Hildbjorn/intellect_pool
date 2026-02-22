from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from core.models.models_foiv import FOIV, FOIVType


@admin.register(FOIVType)
class FOIVTypeAdmin(admin.ModelAdmin):
    """
    Админка для типов ФОИВ
    """
    list_display = (
        'foiv_type_id',
        'foiv_type',
        'foiv_type_short',
        'foiv_count',
        'created_at'
    )
    list_display_links = ('foiv_type_id', 'foiv_type')
    search_fields = ('foiv_type', 'foiv_type_short')
    list_filter = ('created_at',)
    ordering = ('foiv_type_id',)
    
    def get_queryset(self, request):
        """Оптимизация запросов с подсчетом количества ФОИВ"""
        return super().get_queryset(request).annotate(
            foiv_count=Count('foivs')
        )
    
    def foiv_count(self, obj):
        """Количество ФОИВ данного типа"""
        count = getattr(obj, 'foiv_count', 0)
        url = reverse('admin:core_foiv_changelist') + f'?foiv_type__id__exact={obj.foiv_type_id}'
        return format_html('<a href="{}">{} органов</a>', url, count)
    foiv_count.short_description = 'Количество ФОИВ'
    foiv_count.admin_order_field = 'foiv_count'


@admin.register(FOIV)
class FOIVAdmin(admin.ModelAdmin):
    """
    Админка для федеральных органов исполнительной власти
    """
    list_display = (
        'sequence_number',
        'short_name_colored',
        'foiv_type',
        'okogu_code',
        'parent_foiv_link',
        'head_info',
        'subordinate_count',
        'is_active',
        'updated_at'
    )
    list_display_links = ('short_name_colored',)
    
    list_filter = (
        'foiv_type',
        'is_active',
        ('parent_foiv', admin.RelatedOnlyFieldListFilter),
        'created_at',
        'updated_at'
    )
    
    search_fields = (
        'short_name',
        'full_name',
        'okogu_code',
        'slug',
        'description'
    )
    
    readonly_fields = (
        'created_at',
        'updated_at',
        'hierarchy_display',
        'subordinate_tree'
    )
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'sequence_number',
                ('short_name', 'full_name'),
                'name_for_sort',
                'slug',
                ('foiv_type', 'okogu_code'),
                'is_active'
            )
        }),
        ('Иерархия', {
            'fields': (
                'parent_foiv',
                'hierarchy_display',
                'subordinate_tree'
            ),
            'classes': ('collapse',)
        }),
        ('Руководство', {
            'fields': (
                ('head_position', 'head'),
            )
        }),
        ('Контакты', {
            'fields': (
                'address',
                'city',
                ('phone', 'email'),
                'website'
            ),
            'classes': ('wide',)
        }),
        ('Дополнительно', {
            'fields': (
                'foundation_date',
                'description'
            ),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    autocomplete_fields = ['parent_foiv', 'head', 'city']
    raw_id_fields = ['head', 'city']
    list_per_page = 25
    save_on_top = True
    actions = ['make_active', 'make_inactive']
    
    # Кастомные методы для отображения
    
    def short_name_colored(self, obj):
        """
        Цветное отображение краткого названия в зависимости от типа
        """
        colors = {
            'Министерство': '#1e3c72',  # темно-синий
            'Федеральная служба': '#2e7d32',  # темно-зеленый
            'Федеральное агентство': '#b85e00'  # оранжево-коричневый
        }
        color = colors.get(str(obj.foiv_type), '#333333')
        
        # Добавляем иконку для неактивных
        if not obj.is_active:
            return format_html(
                '<span style="color: #999; text-decoration: line-through;">{}</span>',
                obj.short_name
            )
        
        return format_html(
            '<span style="color: {}; font-weight: 500;">{}</span>',
            color,
            obj.short_name
        )
    short_name_colored.short_description = 'Краткое наименование'
    short_name_colored.admin_order_field = 'short_name'
    
    def parent_foiv_link(self, obj):
        """
        Ссылка на вышестоящий ФОИВ
        """
        if obj.parent_foiv:
            url = reverse('admin:core_foiv_change', args=[obj.parent_foiv.pk])
            return format_html(
                '<a href="{}">{} [{}]</a>',
                url,
                obj.parent_foiv.short_name,
                obj.parent_foiv.okogu_code
            )
        return format_html('<span style="color: #999;">—</span>')
    parent_foiv_link.short_description = 'Вышестоящий орган'
    parent_foiv_link.admin_order_field = 'parent_foiv__short_name'
    
    def head_info(self, obj):
        """
        Информация о руководителе
        """
        if obj.head:
            url = reverse('admin:core_person_change', args=[obj.head.pk])
            position = f"<br><small>{obj.head_position or 'Должность не указана'}</small>"
            return format_html(
                '<a href="{}">{}</a>{}',
                url,
                obj.head,
                position
            )
        elif obj.head_position:
            return format_html(
                '<span style="color: #666;">{}</span>',
                obj.head_position
            )
        return format_html('<span style="color: #999;">—</span>')
    head_info.short_description = 'Руководитель'
    
    def subordinate_count(self, obj):
        """
        Количество подчиненных органов
        """
        count = obj.subordinate_foivs.count()
        if count > 0:
            url = reverse('admin:core_foiv_changelist') + f'?parent_foiv__id__exact={obj.pk}'
            return format_html(
                '<a href="{}" style="font-weight: 500;">{} подчиненных</a>',
                url,
                count
            )
        return format_html('<span style="color: #999;">0</span>')
    subordinate_count.short_description = 'Подчиненные'
    subordinate_count.admin_order_field = 'subordinate_foivs__count'
    
    def hierarchy_display(self, obj):
        """
        Отображение полной иерархии
        """
        if obj.pk:
            return format_html(
                '<div style="background: #f8f9fa; padding: 10px; border-radius: 4px;">'
                '<strong>Иерархия подчинения:</strong><br>{}'
                '</div>',
                obj.get_full_hierarchy()
            )
        return '-'
    hierarchy_display.short_description = 'Иерархия'
    
    def subordinate_tree(self, obj):
        """
        Древовидное отображение подчиненных органов
        """
        if obj.pk:
            subordinates = obj.subordinate_foivs.all().order_by('sequence_number')
            if subordinates:
                html = ['<div style="background: #f8f9fa; padding: 10px; border-radius: 4px;">']
                html.append('<strong>Подчиненные органы:</strong><ul style="margin-top: 5px;">')
                
                for sub in subordinates:
                    sub_url = reverse('admin:core_foiv_change', args=[sub.pk])
                    html.append(
                        f'<li>'
                        f'<a href="{sub_url}">{sub.short_name}</a> '
                        f'<span style="color: #666;">[{sub.okogu_code}]</span>'
                        f'</li>'
                    )
                    
                    # Добавляем подчиненных второго уровня
                    sub_subordinates = sub.subordinate_foivs.all().order_by('sequence_number')[:5]
                    if sub_subordinates:
                        html.append('<ul style="margin-left: 20px;">')
                        for sub_sub in sub_subordinates:
                            sub_sub_url = reverse('admin:core_foiv_change', args=[sub_sub.pk])
                            html.append(
                                f'<li>'
                                f'<a href="{sub_sub_url}">{sub_sub.short_name}</a> '
                                f'<span style="color: #999;">[{sub_sub.okogu_code}]</span>'
                                f'</li>'
                            )
                        if sub.subordinate_foivs.count() > 5:
                            html.append('<li><em>...</em></li>')
                        html.append('</ul>')
                
                html.append('</ul></div>')
                return format_html(''.join(html))
        return '-'
    subordinate_tree.short_description = 'Дерево подчиненных'
    
    # Actions
    
    def make_active(self, request, queryset):
        """Активировать выбранные ФОИВ"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано {updated} органов')
    make_active.short_description = 'Активировать выбранные органы'
    
    def make_inactive(self, request, queryset):
        """Деактивировать выбранные ФОИВ"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано {updated} органов')
    make_inactive.short_description = 'Деактивировать выбранные органы'
    
    # Переопределение queryset для оптимизации
    
    def get_queryset(self, request):
        """Оптимизация запросов с предзагрузкой связанных объектов"""
        return super().get_queryset(request).select_related(
            'foiv_type', 'parent_foiv', 'head', 'city'
        ).prefetch_related(
            'subordinate_foivs'
        ).annotate(
            subordinate_foivs_count=Count('subordinate_foivs', distinct=True)
        )
    
    # Сохранение с автоматической генерацией полей
    
    def save_model(self, request, obj, form, change):
        """Переопределение сохранения с сообщением"""
        super().save_model(request, obj, form, change)
        if not change:
            self.message_user(
                request,
                f'Орган "{obj.short_name}" успешно создан. Код ОКОГУ: {obj.okogu_code}',
                level='SUCCESS'
            )
    
    # Поиск
    
    def get_search_results(self, request, queryset, search_term):
        """Улучшенный поиск"""
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        
        # Добавляем поиск по коду ОКОГУ с частичным совпадением
        if search_term.isdigit():
            queryset |= self.model.objects.filter(okogu_code__icontains=search_term)
        
        return queryset, use_distinct


class FOIVInline(admin.TabularInline):
    """
    Inline для отображения подчиненных ФОИВ в админке вышестоящего органа
    """
    model = FOIV
    fk_name = 'parent_foiv'
    fields = ['sequence_number', 'short_name', 'okogu_code', 'foiv_type', 'is_active']
    readonly_fields = ['sequence_number', 'short_name', 'okogu_code', 'foiv_type']
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = 'Подчиненный орган'
    verbose_name_plural = 'Подчиненные органы'
    
    def has_add_permission(self, request, obj=None):
        return False
    