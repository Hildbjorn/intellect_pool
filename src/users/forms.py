import json
import re
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms

from .models import Profile

class ProfileCreationForm(UserCreationForm):
    email = forms.EmailField(label='E-mail:',
                             required=True,
                             widget=forms.TextInput(attrs={'id': 'id_username',
                                                           'class': 'form-control floating',
                                                           'aria-describedby': 'emailHelp'}),)

    password1 = forms.CharField(label='Пароль:',
                                strip=False,
                                widget=forms.PasswordInput(attrs={'class': 'form-control floating',
                                                                  'autocomplete': 'new-password',
                                                                  'aria-describedby': 'password1Help'}),
                                help_text=password_validation.password_validators_help_text_html(),)
    
    password2 = forms.CharField(label='Пароль еще раз:',
                                widget=forms.PasswordInput(attrs={'class': 'form-control floating',
                                                                  'autocomplete': 'new-password',
                                                                  'aria-describedby': 'password2Help'}),
                                strip=False,
                                help_text="Введите тот же пароль, что ввели выше.",)
    
    is_staff = forms.BooleanField(required=False,
                                  label='В команде',
                                  widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    is_active = forms.BooleanField(required=False,
                                   label='Активный',
                                   widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        # Если nic_name не задан и есть email
        if not user.nic_name and user.email:
            base_nic_name = user.email.split('@')[0]
            user.nic_name = re.sub(r'[^a-zA-Z0-9]', '', base_nic_name).upper()
            # Проверка на уникальность
            original_nic_name = user.nic_name
            counter = 1
            while Profile.objects.filter(nic_name=user.nic_name).exists():
                # Формируем новое имя с порядковым номером
                user.nic_name = f"{original_nic_name}_{counter:03}"
                counter += 1
        if commit:
            user.save()
        return user

    
    class Meta:
        model = Profile
        fields = ('email', 'password1', 'password2', 'is_staff', 'is_active')


class ProfileChangeForm(UserChangeForm):
    """
    Форма изменения пользователя.
    """

    class Meta:
        model = Profile
        fields = ('email',)
        widgets = {
            'groups': forms.CheckboxSelectMultiple,
            'user_permissions': forms.CheckboxSelectMultiple,
        }


class ProfileUpdateForm(forms.ModelForm):
    """
    Форма обновления данных пользователя в модели Profile.
    """

    nic_name = forms.CharField(required=False,
                               label='Псевдоним:',
                               widget=forms.TextInput(attrs={'class': 'form-control floating',
                                                             'id': 'nic_name',
                                                             'placeholder': 'Псевдоним'}))

    last_name = forms.CharField(required=False,
                                label='Фамилия:',
                                widget=forms.TextInput(attrs={'class': 'form-control floating',
                                                              'id': 'last_name',
                                                              'placeholder': 'Фамилия'}))

    first_name = forms.CharField(required=False,
                                 label='Имя:',
                                 widget=forms.TextInput(attrs={'class': 'form-control floating',
                                                               'id': 'first_name',
                                                               'placeholder': 'Имя'}))

    middle_name = forms.CharField(required=False,
                                  label='Отчество:',
                                  widget=forms.TextInput(attrs={'class': 'form-control floating',
                                                                'id': 'middle_name',
                                                                'placeholder': 'Отчество'}))

    image = forms.ImageField(required=False,
                              label='Аватар:',
                              widget=forms.FileInput(attrs={'class': 'form-control form-control-sm field_hidden',
                                                            'id': 'image_field',
                                                            'accept': '.jpg, .png, .gif',
                                                            'type': 'file'}))

    phone = forms.CharField(required=False,
                            label='Телефон:',
                            widget=forms.TextInput(attrs={'class': 'tel form-control floating',
                                                          'id': 'phone',
                                                          'placeholder': 'Телефон'}))

    email = forms.EmailField(label='E-mail:',
                             required=True,
                             widget=forms.TextInput(attrs={'class': 'form-control floating',
                                                           'id': 'email',
                                                           'placeholder': 'user@mail.ru'}),
                             error_messages={'unique': ("Пользователь с таким e-mail уже зарегистрирован"),
                                             'invalid': ("Введите корректное значение")})

    class Meta:
        model = Profile
        fields = (
            'nic_name',
            'last_name',
            'first_name',
            'middle_name',
            'image',
            'phone',
            'email',
        )

    def clean_nic_name(self):
        nic_name = self.cleaned_data.get('nic_name')
        upper_nic_name = nic_name.upper()
        # Проверяем, если форма редактирует существующий объект
        if self.instance.pk:  # Если объект существует (редактирование)
            # Проверяем, существует ли другой объект с таким же ником
            if Profile.objects.filter(nic_name=upper_nic_name).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(
                    f"Ник '{nic_name}' уже существует.")
        else:  # Если это создание нового объекта
            if Profile.objects.filter(nic_name=upper_nic_name).exists():
                raise forms.ValidationError(
                    f"Ник '{nic_name}' уже существует.")

        return nic_name
