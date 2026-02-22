from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from intellectual_property.models.models_fips_catalogue import FipsOpenDataCatalogue


@admin.register(FipsOpenDataCatalogue)
class FipsOpenDataCatalogueAdmin(admin.ModelAdmin):
    """
    Простой административный интерфейс для модели FipsOpenDataCatalogue.
    """
    
    list_display = [
        'name',
        'ip_type',
        'publication_date',
        'upload_date',
    ]
    
    list_filter = [
        'ip_type',
        'publication_date',
    ]
    
    search_fields = [
        'name',
        'ip_type__name',
    ]
    
    readonly_fields = [
        'upload_date',
        'last_modified',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('ip_type', 'name', 'catalogue_file', 'publication_date', 'description')
        }),
        (_('Служебная информация'), {
            'fields': ('upload_date', 'last_modified'),
            'classes': ('collapse',),
        }),
    )
    
    autocomplete_fields = ['ip_type']
    date_hierarchy = 'publication_date'
