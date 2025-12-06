from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import User


# Формы для админки
class CustomUserCreationForm(UserCreationForm):
    """Форма для создания пользователя (для админки)"""

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'phone', 'country', 'avatar')


class CustomUserChangeForm(UserChangeForm):
    """Форма для изменения данных пользователя (для админки)"""

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'phone', 'country', 'avatar')


# Формы для публичного использования
class UserRegisterForm(UserCreationForm):
    """Форма регистрации пользователя (публичная)"""

    email = forms.EmailField(
        label=_('Email'),
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email'),
            'autocomplete': 'email'
        }),
        help_text=_('Required. Enter a valid email address.')
    )

    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Create a password'),
            'autocomplete': 'new-password'
        }),
        help_text=_('Your password must contain at least 8 characters.')
    )

    password2 = forms.CharField(
        label=_('Password confirmation'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Repeat your password'),
            'autocomplete': 'new-password'
        }),
        help_text=_('Enter the same password as before, for verification.')
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'phone', 'country')

        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Choose a username'),
                'autocomplete': 'username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your first name'),
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your last name'),
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your phone number'),
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your country'),
            }),
        }

        help_texts = {
            'username': _('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        }

    def clean_email(self):
        """Проверка уникальности email"""
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email


class UserLoginForm(AuthenticationForm):
    """Форма авторизации пользователя по email"""

    username = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email'),
            'autocomplete': 'email'
        })
    )

    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password'),
            'autocomplete': 'current-password'
        })
    )

    error_messages = {
        'invalid_login': _(
            "Please enter a correct email and password."
        ),
        'inactive': _("This account is inactive."),
    }


class UserProfileForm(forms.ModelForm):
    """Форма редактирования профиля пользователя"""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'country', 'avatar')

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }