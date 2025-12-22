from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
import json


class Client(models.Model):
    """Модель получателя рассылки"""
    email = models.EmailField(
        verbose_name='Email',
        unique=True,
        error_messages={
            'unique': 'Клиент с таким email уже существует.'
        }
    )
    full_name = models.CharField(
        verbose_name='ФИО',
        max_length=255,
        help_text='Введите полное имя получателя'
    )
    comment = models.TextField(
        verbose_name='Комментарий',
        blank=True,
        help_text='Дополнительная информация о получателе'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Владелец',
        related_name='clients',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name='Дата обновления',
        auto_now=True
    )
    is_active = models.BooleanField(
        verbose_name='Активен',
        default=True
    )

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['-created_at']
        permissions = [
            ('can_view_all_clients', 'Может просматривать всех клиентов'),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def clean(self):
        """Валидация модели"""
        if Client.objects.filter(email=self.email).exclude(pk=self.pk).exists():
            raise ValidationError({'email': 'Клиент с таким email уже существует.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Message(models.Model):
    """Модель сообщения для рассылки"""
    subject = models.CharField(
        verbose_name='Тема письма',
        max_length=255,
        help_text='Введите тему письма'
    )
    body = models.TextField(
        verbose_name='Текст письма',
        help_text='Введите текст письма'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Владелец',
        related_name='messages',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name='Дата обновления',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['-created_at']

    def __str__(self):
        return self.subject

    @property
    def preview(self):
        """Короткий превью текста"""
        return self.body[:100] + '...' if len(self.body) > 100 else self.body


class Mailing(models.Model):
    """Модель рассылки"""
    STATUS_CREATED = 'CREATED'
    STATUS_STARTED = 'STARTED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CHOICES = [
        (STATUS_CREATED, 'Создана'),
        (STATUS_STARTED, 'Запущена'),
        (STATUS_COMPLETED, 'Завершена'),
    ]

    FREQUENCY_CHOICES = [
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно'),
        ('once', 'Однократно'),
    ]

    start_time = models.DateTimeField(
        verbose_name='Дата и время начала',
        help_text='Укажите дату и время начала рассылки'
    )
    end_time = models.DateTimeField(
        verbose_name='Дата и время окончания',
        help_text='Укажите дату и время окончания рассылки'
    )
    status = models.CharField(
        verbose_name='Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        editable=False
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        verbose_name='Сообщение',
        related_name='mailings'
    )
    clients = models.ManyToManyField(
        Client,
        verbose_name='Получатели',
        related_name='mailings'
    )
    frequency = models.CharField(
        verbose_name='Периодичность',
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='once'
    )
    is_active = models.BooleanField(
        verbose_name='Активна',
        default=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Владелец',
        related_name='mailings',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name='Дата обновления',
        auto_now=True
    )
    next_send = models.DateTimeField(
        verbose_name='Следующая отправка',
        null=True,
        blank=True,
        help_text='Дата и время следующей отправки (автоматически рассчитывается)'
    )

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        ordering = ['-created_at']
        permissions = [
            ('can_disable_mailing', 'Может отключать рассылки'),
            ('can_view_all_mailings', 'Может просматривать все рассылки'),
        ]

    def __str__(self):
        return f"Рассылка #{self.id} - {self.message.subject}"

    def clean(self):
        """Валидация дат рассылки"""
        now = timezone.now()

        # Проверка, что дата начала не в прошлом (только для новых объектов)
        if self.pk is None and self.start_time < now:
            raise ValidationError({
                'start_time': 'Дата начала не может быть в прошлом.'
            })

        # Проверка, что дата начала раньше даты окончания
        if self.start_time >= self.end_time:
            raise ValidationError({
                'end_time': 'Дата окончания должна быть позже даты начала.'
            })

    def save(self, *args, **kwargs):
        """Сохранение с обновлением статуса"""
        self.full_clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Если это новая рассылка, устанавливаем следующую отправку
        if is_new:
            self.update_status()
            self.calculate_next_send()

    def update_status(self):
        """Обновление статуса рассылки"""
        now = timezone.now()

        if not self.is_active:
            if self.status != self.STATUS_COMPLETED:
                self.status = self.STATUS_COMPLETED
                self.save(update_fields=['status'])
            return self.status

        if now < self.start_time:
            new_status = self.STATUS_CREATED
        elif self.start_time <= now <= self.end_time:
            new_status = self.STATUS_STARTED
        else:
            new_status = self.STATUS_COMPLETED

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])

        return self.status

    def calculate_next_send(self):
        """Расчет даты следующей отправки"""
        if self.frequency == 'once' or self.status == self.STATUS_COMPLETED:
            self.next_send = None
        elif self.frequency == 'daily':
            self.next_send = timezone.now() + timezone.timedelta(days=1)
        elif self.frequency == 'weekly':
            self.next_send = timezone.now() + timezone.timedelta(weeks=1)
        elif self.frequency == 'monthly':
            self.next_send = timezone.now() + timezone.timedelta(days=30)

        if self.next_send and self.next_send > self.end_time:
            self.next_send = None

        self.save(update_fields=['next_send'])
        return self.next_send

    @property
    def clients_count(self):
        """Количество получателей"""
        return self.clients.count()

    @property
    def successful_attempts(self):
        """Количество успешных попыток"""
        return self.attempts.filter(status=MailingAttempt.STATUS_SUCCESS).count()

    @property
    def failed_attempts(self):
        """Количество неуспешных попыток"""
        return self.attempts.filter(status=MailingAttempt.STATUS_FAILED).count()


class MailingAttempt(models.Model):
    """Модель попытки отправки рассылки"""
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Успешно'),
        (STATUS_FAILED, 'Не успешно'),
    ]

    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        verbose_name='Рассылка',
        related_name='attempts'
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name='Клиент',
        related_name='attempts',
        null=True,
        blank=True
    )
    attempt_time = models.DateTimeField(
        verbose_name='Дата и время попытки',
        auto_now_add=True
    )
    status = models.CharField(
        verbose_name='Статус',
        max_length=20,
        choices=STATUS_CHOICES
    )
    server_response = models.TextField(
        verbose_name='Ответ сервера',
        blank=True
    )
    created_at = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Попытка отправки'
        verbose_name_plural = 'Попытки отправки'
        ordering = ['-attempt_time']

    def __str__(self):
        return f"Попытка #{self.id} - {self.get_status_display()}"

    @classmethod
    def log_attempt(cls, mailing, client, status, response=''):
        """Создание записи о попытке отправки"""
        return cls.objects.create(
            mailing=mailing,
            client=client,
            status=status,
            server_response=response
        )


# =================== СИГНАЛЫ ДЛЯ ИНВАЛИДАЦИИ КЕША ===================

def clear_cache_set(set_name):
    """Очистка всех ключей в наборе"""
    keys_data = cache.get(f'keys:{set_name}')
    if keys_data:
        keys = json.loads(keys_data)
        for key in keys:
            cache.delete(key)
        cache.delete(f'keys:{set_name}')


@receiver(post_save, sender=Mailing)
@receiver(post_delete, sender=Mailing)
def invalidate_mailing_cache_signal(sender, instance, **kwargs):
    """Сигнал для инвалидации кеша при изменении рассылки"""
    # Очищаем кеш списков рассылок
    clear_cache_set('mailing_list')

    # Очищаем дашборд и статистику
    clear_cache_set('dashboard')
    clear_cache_set('statistics')
    clear_cache_set('api_stats')

    # Очищаем кеш детальной страницы этой рассылки
    cache.delete_pattern = getattr(cache, 'delete_pattern', None)
    if cache.delete_pattern:
        try:
            # Пробуем использовать delete_pattern если бэкенд его поддерживает
            cache.delete_pattern(f'*mailing_detail*{instance.id}*')
            cache.delete_pattern(f'*mailing_context*{instance.id}*')
        except:
            # Если не поддерживается, удаляем по известным ключам
            mailing_context_keys = json.loads(cache.get('keys:mailing_context') or '[]')
            for key in mailing_context_keys:
                if str(instance.id) in key:
                    cache.delete(key)


@receiver(post_save, sender=Client)
@receiver(post_delete, sender=Client)
def invalidate_client_cache_signal(sender, instance, **kwargs):
    """Сигнал для инвалидации кеша при изменении клиента"""
    # Очищаем кеш списков клиентов
    clear_cache_set('client_list')

    # Очищаем дашборд и статистику
    clear_cache_set('dashboard')
    clear_cache_set('statistics')

    # Инвалидируем кеш рассылок, где участвует этот клиент
    if hasattr(instance, 'mailings'):
        for mailing in instance.mailings.all():
            # Очищаем кеш детальной страницы рассылки
            cache.delete_pattern = getattr(cache, 'delete_pattern', None)
            if cache.delete_pattern:
                try:
                    cache.delete_pattern(f'*mailing_context*{mailing.id}*')
                except:
                    pass


@receiver(post_save, sender=Message)
@receiver(post_delete, sender=Message)
def invalidate_message_cache_signal(sender, instance, **kwargs):
    """Сигнал для инвалидации кеша при изменении сообщения"""
    # Очищаем кеш списков сообщений
    clear_cache_set('dashboard')
    clear_cache_set('statistics')

    # Инвалидируем кеш рассылок с этим сообщением
    if hasattr(instance, 'mailings'):
        for mailing in instance.mailings.all():
            clear_cache_set('mailing_list')

            # Очищаем кеш детальной страницы рассылки
            cache.delete_pattern = getattr(cache, 'delete_pattern', None)
            if cache.delete_pattern:
                try:
                    cache.delete_pattern(f'*mailing_context*{mailing.id}*')
                except:
                    pass


@receiver(post_save, sender=MailingAttempt)
@receiver(post_delete, sender=MailingAttempt)
def invalidate_attempt_cache_signal(sender, instance, **kwargs):
    """Сигнал для инвалидации кеша при изменении попытки отправки"""
    # Очищаем дашборд и статистику
    clear_cache_set('dashboard')
    clear_cache_set('statistics')
    clear_cache_set('api_stats')

    # Инвалидируем кеш конкретной рассылки
    if instance.mailing_id:
        cache.delete_pattern = getattr(cache, 'delete_pattern', None)
        if cache.delete_pattern:
            try:
                cache.delete_pattern(f'*mailing_context*{instance.mailing_id}*')
            except:
                pass


@receiver(m2m_changed, sender=Mailing.clients.through)
def invalidate_mailing_clients_cache(sender, instance, action, **kwargs):
    """Сигнал для инвалидации кеша при изменении связи клиенты-рассылки"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Очищаем кеш детальной страницы рассылки
        cache.delete_pattern = getattr(cache, 'delete_pattern', None)
        if cache.delete_pattern:
            try:
                cache.delete_pattern(f'*mailing_context*{instance.id}*')
            except:
                pass

        # Очищаем дашборд и статистику
        clear_cache_set('dashboard')
        clear_cache_set('statistics')