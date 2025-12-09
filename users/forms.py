from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from .models import User

# User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        # ИСПРАВИТЬ: 'email' вместо 'emails'
        fields = ('email', 'username', 'first_name', 'last_name', 'phone', 'country', 'avatar')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        # ИСПРАВИТЬ: 'email' вместо 'emails'
        fields = ('email', 'username', 'first_name', 'last_name', 'phone', 'country', 'avatar')


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введите email'})
    )

    username = forms.CharField(
        label='Имя пользователя',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите имя пользователя'})
    )

    first_name = forms.CharField(
        label='Имя',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите имя'})
    )

    last_name = forms.CharField(
        label='Фамилия',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите фамилию'})
    )

    phone = forms.CharField(
        label='Телефон',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите телефон'})
    )

    country = forms.CharField(
        label='Страна',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите страну'})
    )

    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введите пароль'})
    )

    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Подтвердите пароль'})
    )

    class Meta:
        model = User
        # ИСПРАВИТЬ: 'email' вместо 'emails'
        fields = ('email', 'username', 'first_name', 'last_name', 'phone', 'country', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует')
        return username


class UserLoginForm(forms.Form):
    username = forms.CharField(
        label='Имя пользователя или Email',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите имя пользователя или email'})
    )

    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введите пароль'})
    )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        # ИСПРАВИТЬ: 'email' вместо 'emails'
        fields = ('email', 'username', 'first_name', 'last_name', 'phone', 'country', 'avatar')

        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Проверяем, что email уникален, кроме текущего пользователя
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует')
        return email