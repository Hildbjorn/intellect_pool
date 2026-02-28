from django.urls import path
from .views.views_ip_list import *

urlpatterns = [
    path('', IPObjectListView.as_view(), name='ip_list'),
]