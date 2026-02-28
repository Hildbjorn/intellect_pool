from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.core.paginator import Paginator
from django.db import models
import django_filters

from intellectual_property.models import (
    IPObject, Person, Organization, ProgrammingLanguage, 
    DBMS, OperatingSystem, Country, AdditionalPatent, IPImage
)
from intellectual_property.filters import IPObjectFilter

__all__ = (
    'IPObjectListView',
)


class IPObjectListView(LoginRequiredMixin, ListView):
    """Представление для отображения списка РИД."""
    model = IPObject
    template_name = 'intellectual_property/ipobject_list.html'
    context_object_name = 'ip_objects'
    paginate_by = 50

    def get_queryset(self):
        """
        Оптимизация запросов: select_related и prefetch_related для связанных полей.
        """
        queryset = super().get_queryset().select_related(
            'ip_type',
            'ip_type__protection_document_type',
            'paris_convention_priority_country',
        ).prefetch_related(
            # Для авторов
            Prefetch('authors', 
                    queryset=Person.objects.all().only(
                        'ceo_id', 'last_name', 'first_name', 'middle_name', 'ceo'
                    )),
            # Для правообладателей (физ. лица)
            Prefetch('owner_persons', 
                    queryset=Person.objects.all().only(
                        'ceo_id', 'last_name', 'first_name', 'middle_name', 'ceo'
                    )),
            # Для правообладателей (организации)
            Prefetch('owner_organizations', 
                    queryset=Organization.objects.all().only(
                        'organization_id', 'name', 'short_name', 'full_name'
                    )),
            # Для языков программирования
            Prefetch('programming_languages', 
                    queryset=ProgrammingLanguage.objects.all().only('id', 'name')),
            # Для СУБД
            Prefetch('dbms', 
                    queryset=DBMS.objects.all().only('id', 'name')),
            # Для операционных систем
            Prefetch('operating_systems', 
                    queryset=OperatingSystem.objects.all().only('id', 'name')),
            # Для стран первого использования
            Prefetch('first_usage_countries', 
                    queryset=Country.objects.all().only('id', 'name', 'code')),
            # Для дополнительных патентов
            Prefetch('additional_patents', 
                    queryset=AdditionalPatent.objects.all().only('id', 'patent_number', 'patent_date')),
            # Для изображений
            Prefetch('images', 
                    queryset=IPImage.objects.all().only('id', 'image', 'title', 'is_main')),
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем базовый queryset
        base_queryset = self.get_queryset()
        
        # Применяем фильтр
        ip_filter = IPObjectFilter(self.request.GET, queryset=base_queryset)
        filtered_qs = ip_filter.qs
        
        # Пагинация
        paginator = Paginator(filtered_qs, self.paginate_by)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context['filter'] = ip_filter
        context['object_list'] = page_obj.object_list
        context['page_obj'] = page_obj
        context['paginator'] = paginator
        
        return context