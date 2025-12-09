from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """
    Модель категории товаров
    """
    name = models.CharField(
        max_length=100,
        verbose_name=_('Наименование'),
        help_text=_('Введите наименование категории')
    )
    description = models.TextField(
        verbose_name=_('Описание'),
        help_text=_('Введите описание категории'),
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активная'),
        help_text=_('Отметьте, если категория активна')
    )

    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """URL для просмотра товаров категории"""
        return reverse('products:list') + f'?category={self.id}'


class Product(models.Model):
    """
    Модель товара с системой публикаций и владением
    """

    # Статусы публикации
    class PublishStatus(models.TextChoices):
        DRAFT = 'draft', _('Черновик')
        PENDING_REVIEW = 'pending_review', _('На проверке')
        PUBLISHED = 'published', _('Опубликовано')
        REJECTED = 'rejected', _('Отклонено')
        ARCHIVED = 'archived', _('Архивирован')

    # Базовые поля
    name = models.CharField(
        max_length=100,
        verbose_name=_('Наименование'),
        help_text=_('Введите наименование товара')
    )
    description = models.TextField(
        verbose_name=_('Описание'),
        help_text=_('Введите описание товара'),
        blank=True,
        null=True
    )
    image = models.ImageField(
        upload_to='products/%Y/%m/%d/',
        verbose_name=_('Изображение'),
        help_text=_('Загрузите изображение товара'),
        blank=True,
        null=True
    )
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        verbose_name=_('Категория'),
        help_text=_('Выберите категорию товара'),
        null=True,
        blank=True
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Цена за покупку'),
        help_text=_('Введите цену товара')
    )

    # Поля для системы публикаций
    publish_status = models.CharField(
        max_length=20,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
        verbose_name=_('Статус публикации'),
        help_text=_('Выберите статус публикации товара')
    )

    # Владелец продукта
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        verbose_name=_('Владелец'),
        null=True,
        blank=True,
        related_name='products'
    )

    # Поля даты и времени
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата последнего изменения')
    )

    # Дата публикации
    published_at = models.DateTimeField(
        verbose_name=_('Дата публикации'),
        null=True,
        blank=True
    )

    # Дополнительные метаданные
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активный'),
        help_text=_('Отметьте, если товар активен')
    )

    # Количество просмотров
    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Количество просмотров')
    )

    class Meta:
        verbose_name = _('Товар')
        verbose_name_plural = _('Товары')
        ordering = ['-created_at', 'name']
        permissions = [
            ("can_publish_product", _("Может публиковать товары")),
            ("can_unpublish_product", _("Может отменять публикацию товаров")),
            ("can_change_publish_status", _("Может изменять статус публикации")),
            ("can_view_all_products", _("Может просматривать все товары")),
        ]

    def __str__(self):
        return f"{self.name} - {self.price}"

    def get_absolute_url(self):
        """URL для детального просмотра товара"""
        return reverse('products:detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """Автоматически устанавливаем дату публикации при изменении статуса"""
        if self.publish_status == self.PublishStatus.PUBLISHED and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        elif self.publish_status != self.PublishStatus.PUBLISHED:
            self.published_at = None

        super().save(*args, **kwargs)

    @property
    def is_published(self):
        """Проверка, опубликован ли товар"""
        return (self.publish_status == self.PublishStatus.PUBLISHED and
                self.is_active and
                (not self.category or self.category.is_active))

    @property
    def is_owner_active(self):
        """Проверка, активен ли владелец"""
        return self.owner and self.owner.is_active

    @classmethod
    def get_published_products(cls):
        """Получить все опубликованные товары"""
        return cls.objects.filter(
            publish_status=cls.PublishStatus.PUBLISHED,
            is_active=True,
            category__is_active=True
        ).select_related('category', 'owner')

    @classmethod
    def get_products_for_user(cls, user):
        """Получить товары, доступные для конкретного пользователя"""
        if user.is_authenticated and user.has_perm('products.can_view_all_products'):
            return cls.objects.all().select_related('category', 'owner')
        elif user.is_authenticated:
            # Владелец видит свои товары + опубликованные
            from django.db.models import Q
            return cls.objects.filter(
                Q(owner=user) |
                Q(publish_status=cls.PublishStatus.PUBLISHED, is_active=True)
            ).select_related('category', 'owner')
        else:
            # Анонимные пользователи видят только опубликованные
            return cls.get_published_products()

    def increment_views(self):
        """Увеличить счетчик просмотров"""
        self.views_count += 1
        self.save(update_fields=['views_count'])