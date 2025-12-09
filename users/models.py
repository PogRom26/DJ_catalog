from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    phone = models.CharField(
        max_length=15, blank=True, null=True, verbose_name="Телефон"
    )
    country = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Страна"
    )
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, verbose_name="Аватар"
    )
    email = models.EmailField(
        unique=True, blank=False, null=False, verbose_name="Email"
    )

    # Настройка полей для авторизации через emails
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["email"]

    def __str__(self):
        return self.email or self.username

    def get_full_name(self):
        """Полное имя пользователя"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        """Короткое имя пользователя"""
        return self.first_name or self.email.split("@")[0]
