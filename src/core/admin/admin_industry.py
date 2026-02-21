# from django.contrib import admin
# from django.utils.html import format_html
# from django.urls import reverse
# from django.db.models import Count
# from core.models.models_industry import Industry
# from common.admin_utils import AdminDisplayMixin


# @admin.register(Industry)
# class IndustryAdmin(AdminDisplayMixin, admin.ModelAdmin):
#     """
#     Админ-панель для отраслей промышленности
#     """
#     list_display = [
#         'industry', 
#         'organizations_count', 
#         'created_at_display',
#         'updated_at_display'
#     ]
#     search_fields = ['industry']
#     readonly_fields = ['slug', 'created_at', 'updated_at', 'organizations_count']
#     fieldsets = (
#         ('Основная информация', {
#             'fields': ('industry_id', 'industry', 'slug')
#         }),
#         ('Статистика', {
#             'fields': ('organizations_count',),
#             'classes': ('collapse',)
#         }),
#         ('Системная информация', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )

#     def get_list_display(self, request):
#         """Переопределяем, чтобы убрать автоматически добавленные поля из миксина"""
#         return ['industry', 'organizations_count', 'created_at_display', 'updated_at_display']
    
#     def get_queryset(self, request):
#         """Оптимизация запросов с подсчетом организаций"""
#         return super().get_queryset(request).annotate(
#             org_count=Count('organizations')
#         )

#     def organizations_count(self, obj):
#         count = getattr(obj, 'org_count', obj.organizations.count())
#         if count:
#             url = f"{reverse('admin:core_organization_changelist')}?industry__id__exact={obj.industry_id}"
#             return format_html(
#                 '<a href="{}" style="font-weight: bold;">{} предприятий</a>',
#                 url, count
#             )
#         return format_html('<span style="color: #999;">0 предприятий</span>')
#     organizations_count.short_description = 'Организации'
#     organizations_count.admin_order_field = 'org_count'