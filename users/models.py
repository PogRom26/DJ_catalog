from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Кастомная модель пользователя
    """
    # Делаем email обязательным и уникальным для авторизации
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _("A user with that email already exists."),
        },
    )

    # Дополнительные поля
    avatar = models.ImageField(
        upload_to='users/avatars/',
        verbose_name=_('Avatar'),
        blank=True,
        null=True,
        help_text=_('Upload profile picture')
    )

    phone = models.CharField(
        max_length=20,
        verbose_name=_('Phone number'),
        blank=True,
        null=True,
        help_text=_('Enter phone number')
    )

    country = models.CharField(
        max_length=100,
        verbose_name=_('Country'),
        blank=True,
        null=True,
        help_text=_('Enter country')
    )

    # Настройка полей для авторизации через email
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['email']

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Полное имя пользователя"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        """Короткое имя пользователя"""
        return self.first_name or self.email.split('@')[0]