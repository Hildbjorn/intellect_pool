import django_filters
from django import forms

from django.db import models
from .models import IPObject, IPType


class IPObjectFilter(django_filters.FilterSet):
    """Фильтр для списка РИД."""
    
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        label='Наименование РИД',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Поиск по названию...'
        })
    )
    
    registration_number = django_filters.CharFilter(
        field_name='registration_number',
        lookup_expr='icontains',
        label='Рег. номер',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Номер...'
        })
    )
    
    ip_type = django_filters.ModelChoiceFilter(
        field_name='ip_type',
        queryset=IPType.objects.all(),
        label='Вид РИД',
        empty_label='Все виды',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    actual = django_filters.BooleanFilter(
        field_name='actual',
        label='Действует',
        widget=forms.Select(
            choices=[('', 'Все'), ('True', 'Да'), ('False', 'Нет')],
            attrs={'class': 'form-select'}
        )
    )
    
    # Добавляем поиск по авторам
    author = django_filters.CharFilter(
        field_name='authors__last_name',
        lookup_expr='icontains',
        label='Автор',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фамилия автора...'
        })
    )
    
    # Добавляем поиск по правообладателям
    owner = django_filters.CharFilter(
        method='filter_owner',
        label='Правообладатель',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Название или ФИО...'
        })
    )
    
    def filter_owner(self, queryset, name, value):
        """Фильтр по правообладателям (и организации, и физлица)"""
        if value:
            return queryset.filter(
                models.Q(owner_organizations__name__icontains=value) |
                models.Q(owner_organizations__short_name__icontains=value) |
                models.Q(owner_persons__last_name__icontains=value) |
                models.Q(owner_persons__first_name__icontains=value) |
                models.Q(owner_persons__ceo__icontains=value)
            ).distinct()
        return queryset

    class Meta:
        model = IPObject
        fields = ['name', 'registration_number', 'ip_type', 'actual', 'author', 'owner']