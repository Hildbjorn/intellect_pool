from django.contrib import admin
from django.utils.html import format_html
from core.models.models_geo import District, Region, City
from common.admin_utils import AdminImageMixin, AdminDisplayMixin


@admin.register(District)
class DistrictAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для федеральных округов
    """
    list_display = ['district', 'district_short', 'regions_count', 'created_at_display']
    search_fields = ['district', 'district_short']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    fieldsets = (
        ('Основная информация', {
            'fields': ('district_id', 'district', 'district_short', 'slug')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def regions_count(self, obj):
        count = obj.regions.count()
        url = f"/admin/core/region/?district__id__exact={obj.district_id}"
        return format_html('<a href="{}">{} регионов</a>', url, count)
    regions_count.short_description = 'Регионов'


@admin.register(Region)
class RegionAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для регионов
    """
    list_display = ['title', 'district', 'cities_count', 'created_at_display']
    list_filter = ['district']
    search_fields = ['title']
    autocomplete_fields = ['district']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    fieldsets = (
        ('Основная информация', {
            'fields': ('region_id', 'title', 'district', 'slug')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def cities_count(self, obj):
        count = obj.cities.count()
        url = f"/admin/core/city/?region__id__exact={obj.region_id}"
        return format_html('<a href="{}">{} городов</a>', url, count)
    cities_count.short_description = 'Городов'


@admin.register(City)
class CityAdmin(AdminDisplayMixin, admin.ModelAdmin):
    """
    Админ-панель для городов
    """
    list_display = ['city', 'region', 'coordinates_display', 'created_at_display']
    list_filter = ['region', 'region__district']
    search_fields = ['city']
    autocomplete_fields = ['region']
    readonly_fields = ['slug', 'created_at', 'updated_at', 'coordinates_display']
    fieldsets = (
        ('Основная информация', {
            'fields': ('city_id', 'city', 'region', 'slug')
        }),
        ('Координаты', {
            'fields': ('latitude', 'longitude', 'coordinates_display'),
            'classes': ('wide',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def coordinates_display(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '{}°, {}°<br>'
                '<a href="https://maps.google.com/?q={},{}" target="_blank">'
                '<i class="fas fa-map-marker-alt"></i> Открыть на карте</a>',
                obj.latitude, obj.longitude, obj.latitude, obj.longitude
            )
        return '-'
    coordinates_display.short_description = 'Координаты'