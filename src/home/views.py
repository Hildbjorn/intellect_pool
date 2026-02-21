from django.views.generic import TemplateView

__all__ = (
    'IndexView',
    'UserАgreementView',
    'UserAgreementModalView',
    'UserPrivacyPolicyView',
    'UserPrivacyPolicyModalView',
)

class IndexView(TemplateView):
    template_name = 'home/index.html'


class UserАgreementView(TemplateView):
    """Представление для загрузки пользовательского соглашения"""
    template_name = 'home/components/documents/user_agreement/user_agreement.html'


class UserAgreementModalView(TemplateView):
    """Представление для загрузки пользовательского соглашения в модальное окно"""
    template_name = 'home/components/documents/user_agreement/user_agreement_modal.html'


class UserPrivacyPolicyView(TemplateView):
    """Представление для загрузки политики конфиденциальности"""
    template_name = 'home/components/documents/privacy_policy/privacy_policy.html'


class UserPrivacyPolicyModalView(TemplateView):
    """Представление для загрузки политики конфиденциальности в модальное окно"""
    template_name = 'home/components/documents/privacy_policy/privacy_policy_modal.html'