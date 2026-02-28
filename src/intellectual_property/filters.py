import django_filters
from django import forms
from .models import IPObject, IPType

class IPObjectFilter(django_filters.FilterSet):
    """Фильтр для списка РИД."""
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        label='Наименование РИД',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск по названию...'})
    )
    registration_number = django_filters.CharFilter(
        field_name='registration_number',
        lookup_expr='icontains',
        label='Рег. номер',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Номер...'})
    )
    ip_type = django_filters.ModelChoiceFilter(
        queryset=IPType.objects.all(),
        label='Вид РИД',
        empty_label='Все виды',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    actual = django_filters.BooleanFilter(
        field_name='actual',
        label='Действует',
        widget=forms.Select(
            choices=[('', 'Все'), (True, 'Да'), (False, 'Нет')],
            attrs={'class': 'form-select'}
        )
    )
    # Добавьте другие фильтры по необходимости

    class Meta:
        model = IPObject
        fields = ['name', 'registration_number', 'ip_type', 'actual']
