from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import User


class CustomUserCreationForm(UserCreationForm):
    """Форма для создания пользователя (для админки)"""

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name')


class CustomUserChangeForm(UserChangeForm):
    """Форма для изменения данных пользователя (для админки)"""

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name')


# Для публичных форм пока используем заглушки
class UserRegisterForm(UserCreationForm):
    """Форма регистрации пользователя (публичная)"""
    pass


class UserLoginForm(AuthenticationForm):
    """Форма авторизации пользователя"""
    pass