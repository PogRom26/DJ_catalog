from django.db import models

from config import settings


class Category(models.Model):
    """
    Модель категории товаров
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Наименование',
        help_text='Введите наименование категории'
    )
    description = models.TextField(
        verbose_name='Описание',
        help_text='Введите описание категории',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name='Наименование',
        help_text='Введите наименование товара'
    )
    description = models.TextField(
        verbose_name='Описание',
        help_text='Введите описание товара',
        blank=True,
        null=True
    )
    image = models.ImageField(
        upload_to='products/',
        verbose_name='Изображение',
        help_text='Загрузите изображение товара',
        blank=True,
        null=True
    )
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        verbose_name='Категория',
        help_text='Выберите категорию товара',
        null=True,
        blank=True
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена за покупку',
        help_text='Введите цену товара'
    )

    # Поле owner - внешний ключ на пользователя
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name='Владелец',
        null=True,
        blank=True,
        related_name='products'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего изменения'
    )

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name', 'created_at']

    def __str__(self):
        return f"{self.name} - {self.price}"