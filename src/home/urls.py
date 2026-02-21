from django.urls import path
from .views import *

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('user_agreement', UserАgreementView.as_view(), name='user_agreement'),
    path('user_agreement_modal', UserAgreementModalView.as_view(), name='user_agreement_modal'),
    path('privacy_policy', UserPrivacyPolicyView.as_view(), name='privacy_policy'),
    path('privacy_policy_modal', UserPrivacyPolicyModalView.as_view(), name='privacy_policy_modal'),
]
