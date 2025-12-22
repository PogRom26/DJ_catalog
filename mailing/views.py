from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView,
    UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Case, When, IntegerField
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
import hashlib
import json

from .models import Client, Message, Mailing, MailingAttempt
from .forms import ClientForm, MessageForm, MailingForm


class OwnerRequiredMixin:
    """Миксин для проверки владельца объекта"""

    def test_func(self):
        obj = self.get_object()
        user = self.request.user

        # Менеджеры и суперпользователи могут всё
        if user.is_staff or user.is_superuser:
            return True

        # Проверка владельца
        if hasattr(obj, 'owner'):
            return obj.owner == user

        return False

    def handle_no_permission(self):
        messages.error(self.request, 'У вас нет прав для выполнения этого действия.')
        return redirect('mailing:mailing_list')


class ManagerRequiredMixin(UserPassesTestMixin):
    """Миксин для проверки прав менеджера"""

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, 'Только менеджеры могут выполнять это действие.')
        return redirect('mailing:mailing_list')


# =================== КЛАССЫ ДЛЯ РАБОТЫ С КЕШЕМ ===================

class CacheManager:
    """Менеджер для работы с кешем"""

    @staticmethod
    def generate_key(base_key, *args):
        """Генерация ключа кеша"""
        key_string = f"{base_key}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_string.encode()).hexdigest()

    @staticmethod
    def get_set_keys(base_key):
        """Получение всех ключей набора для данного base_key"""
        keys_key = f"keys:{base_key}"
        keys_data = cache.get(keys_key)
        return set(json.loads(keys_data)) if keys_data else set()

    @staticmethod
    def add_to_set(base_key, key):
        """Добавление ключа в набор"""
        keys_key = f"keys:{base_key}"
        keys = CacheManager.get_set_keys(base_key)
        keys.add(key)
        cache.set(keys_key, json.dumps(list(keys)), timeout=None)

    @staticmethod
    def clear_set(base_key):
        """Очистка всех ключей набора"""
        keys = CacheManager.get_set_keys(base_key)
        for key in keys:
            cache.delete(key)
        cache.delete(f"keys:{base_key}")


class MailingCacheManager(CacheManager):
    """Специализированный менеджер кеша для рассылок"""

    @staticmethod
    def get_dashboard_key(user):
        """Ключ для дашборда"""
        if user.is_staff or user.is_superuser:
            return CacheManager.generate_key('dashboard', 'admin', timezone.now().strftime("%Y%m%d%H"))
        return CacheManager.generate_key('dashboard', user.id, timezone.now().strftime("%Y%m%d%H"))

    @staticmethod
    def get_statistics_key(user):
        """Ключ для статистики"""
        if user.is_staff or user.is_superuser:
            return CacheManager.generate_key('statistics', 'admin', timezone.now().strftime("%Y%m%d%H"))
        return CacheManager.generate_key('statistics', user.id, timezone.now().strftime("%Y%m%d%H"))

    @staticmethod
    def get_mailing_detail_key(mailing_id):
        """Ключ для детальной страницы рассылки"""
        return CacheManager.generate_key('mailing_detail', mailing_id)

    @staticmethod
    def get_mailing_context_key(mailing_id):
        """Ключ для контекста детальной страницы"""
        return CacheManager.generate_key('mailing_context', mailing_id)

    @staticmethod
    def invalidate_mailing_cache(mailing_id):
        """Инвалидация кеша для конкретной рассылки"""
        CacheManager.clear_set('dashboard')
        CacheManager.clear_set('statistics')
        CacheManager.clear_set('mailing_list')
        CacheManager.clear_set('api_stats')

        # Удаляем детальную страницу
        detail_key = CacheManager.generate_key('mailing_detail', mailing_id)
        cache.delete(detail_key)

        # Удаляем контекст
        context_key = CacheManager.generate_key('mailing_context', mailing_id)
        cache.delete(context_key)

    @staticmethod
    def invalidate_all_mailing_cache():
        """Инвалидация всего кеша рассылок"""
        CacheManager.clear_set('dashboard')
        CacheManager.clear_set('statistics')
        CacheManager.clear_set('mailing_list')
        CacheManager.clear_set('client_list')
        CacheManager.clear_set('mailing_detail')
        CacheManager.clear_set('mailing_context')
        CacheManager.clear_set('api_stats')


# =================== DASHBOARD WITH CACHING ===================

class DashboardView(LoginRequiredMixin, TemplateView):
    """Дашборд с основной статистикой и кешированием"""
    template_name = 'mailing/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Ключ кеша
        cache_key = MailingCacheManager.get_dashboard_key(user)

        # Регистрируем ключ в наборе
        CacheManager.add_to_set('dashboard', cache_key)

        # Пробуем получить данные из кеша
        cached_data = cache.get(cache_key)

        if cached_data:
            context.update(cached_data)
            context['cached'] = True
            return context

        # Определяем, чьи данные показывать
        if user.is_staff or user.is_superuser:
            mailings = Mailing.objects.all()
            clients = Client.objects.all()
        else:
            mailings = Mailing.objects.filter(owner=user)
            clients = Client.objects.filter(owner=user)

        # Основные показатели
        total_mailings = mailings.count()

        # Активные рассылки
        now = timezone.now()
        active_mailings = mailings.filter(
            start_time__lte=now,
            end_time__gte=now,
            status=Mailing.STATUS_STARTED,
            is_active=True
        ).count()

        unique_clients = clients.values('email').distinct().count()

        # Сегодняшние попытки
        today = timezone.now().date()
        today_attempts = MailingAttempt.objects.filter(
            attempt_time__date=today
        )
        if not user.is_staff and not user.is_superuser:
            today_attempts = today_attempts.filter(mailing__owner=user)

        today_attempts_count = today_attempts.count()
        today_success = today_attempts.filter(
            status=MailingAttempt.STATUS_SUCCESS
        ).count()

        # Ближайшие рассылки
        upcoming_mailings = list(mailings.filter(
            start_time__gt=now,
            is_active=True
        ).order_by('start_time')[:5].values('id', 'message__subject', 'start_time'))

        # Последние рассылки
        recent_mailings = list(mailings.order_by('-created_at')[:5].values(
            'id', 'message__subject', 'status', 'created_at'
        ))

        # Подготавливаем данные для кеширования
        data_to_cache = {
            'total_mailings': total_mailings,
            'active_mailings': active_mailings,
            'unique_clients': unique_clients,
            'today_attempts': today_attempts_count,
            'today_success': today_success,
            'upcoming_mailings': upcoming_mailings,
            'recent_mailings': recent_mailings,
            'last_updated': timezone.now().isoformat(),
        }

        # Кешируем на 5 минут
        cache.set(cache_key, data_to_cache, 300)

        context.update(data_to_cache)
        context['cached'] = False

        return context


# =================== CLIENT VIEWS ===================

class ClientListView(LoginRequiredMixin, ListView):
    """Список клиентов"""
    model = Client
    template_name = 'mailing/client_list.html'
    context_object_name = 'clients'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return Client.objects.all().select_related('owner')

        return Client.objects.filter(owner=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_clients'] = self.get_queryset().count()
        context['active_clients'] = self.get_queryset().filter(is_active=True).count()
        return context


class ClientCreateView(LoginRequiredMixin, CreateView):
    """Создание клиента"""
    model = Client
    form_class = ClientForm
    template_name = 'mailing/client_form.html'
    success_url = reverse_lazy('mailing:client_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Клиент успешно создан.')
        return super().form_valid(form)


class ClientUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование клиента"""
    model = Client
    form_class = ClientForm
    template_name = 'mailing/client_form.html'
    success_url = reverse_lazy('mailing:client_list')

    def form_valid(self, form):
        messages.success(self.request, 'Клиент успешно обновлен.')
        return super().form_valid(form)


class ClientDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    """Удаление клиента"""
    model = Client
    template_name = 'mailing/client_confirm_delete.html'
    success_url = reverse_lazy('mailing:client_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Клиент успешно удален.')
        return super().delete(request, *args, **kwargs)


# =================== MESSAGE VIEWS ===================

class MessageListView(LoginRequiredMixin, ListView):
    """Список сообщений"""
    model = Message
    template_name = 'mailing/message_list.html'
    context_object_name = 'messages'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return Message.objects.all().select_related('owner')

        return Message.objects.filter(owner=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_messages'] = self.get_queryset().count()
        return context


class MessageCreateView(LoginRequiredMixin, CreateView):
    """Создание сообщения"""
    model = Message
    form_class = MessageForm
    template_name = 'mailing/message_form.html'
    success_url = reverse_lazy('mailing:message_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Сообщение успешно создан.')
        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование сообщения"""
    model = Message
    form_class = MessageForm
    template_name = 'mailing/message_form.html'
    success_url = reverse_lazy('mailing:message_list')

    def form_valid(self, form):
        messages.success(self.request, 'Сообщение успешно обновлен.')
        return super().form_valid(form)


class MessageDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    """Удаление сообщения"""
    model = Message
    template_name = 'mailing/message_confirm_delete.html'
    success_url = reverse_lazy('mailing:message_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Сообщение успешно удален.')
        return super().delete(request, *args, **kwargs)


# =================== MAILING VIEWS ===================

class MailingListView(LoginRequiredMixin, ListView):
    """Список рассылок"""
    model = Mailing
    template_name = 'mailing/mailing_list.html'
    context_object_name = 'mailings'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        queryset = Mailing.objects.all().select_related(
            'message', 'owner'
        ).prefetch_related('clients', 'attempts')

        if not user.is_staff and not user.is_superuser:
            queryset = queryset.filter(owner=user)

        # Обновляем статусы при загрузке списка
        for mailing in queryset:
            mailing.update_status()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_mailings'] = self.get_queryset().count()
        context['active_mailings'] = self.get_queryset().filter(
            is_active=True,
            status=Mailing.STATUS_STARTED
        ).count()
        return context


class MailingCreateView(LoginRequiredMixin, CreateView):
    """Создание рассылки"""
    model = Mailing
    form_class = MailingForm
    template_name = 'mailing/mailing_form.html'
    success_url = reverse_lazy('mailing:mailing_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Рассылка успешно создана.')
        response = super().form_valid(form)
        return response


class MailingUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование рассылки"""
    model = Mailing
    form_class = MailingForm
    template_name = 'mailing/mailing_form.html'
    success_url = reverse_lazy('mailing:mailing_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Рассылка успешно обновлена.')
        return super().form_valid(form)


class MailingDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    """Удаление рассылки"""
    model = Mailing
    template_name = 'mailing/mailing_confirm_delete.html'
    success_url = reverse_lazy('mailing:mailing_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Рассылка успешно удалена.')
        return super().delete(request, *args, **kwargs)


class MailingDetailView(LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    """Детальный просмотр рассылки"""
    model = Mailing
    template_name = 'mailing/mailing_detail.html'
    context_object_name = 'mailing'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.update_status()  # Обновляем статус при просмотре
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mailing = self.get_object()

        # Получаем статистику по попыткам
        attempts = mailing.attempts.all()
        context['attempts'] = attempts
        context['success_count'] = attempts.filter(status=MailingAttempt.STATUS_SUCCESS).count()
        context['failed_count'] = attempts.filter(status=MailingAttempt.STATUS_FAILED).count()

        # Получаем клиентов рассылки
        context['clients'] = mailing.clients.all()

        return context


class MailingStartView(LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    """Ручной запуск рассылки"""
    model = Mailing
    template_name = 'mailing/mailing_start.html'

    def get(self, request, *args, **kwargs):
        mailing = self.get_object()

        # Проверяем, можно ли запустить рассылку
        now = timezone.now()
        if not mailing.is_active:
            messages.error(request, 'Рассылка отключена.')
        elif now < mailing.start_time:
            messages.error(request, 'Время запуска рассылки еще не наступило.')
        elif now > mailing.end_time:
            messages.error(request, 'Время рассылки истекло.')
        else:
            # Запускаем отправку
            success_count = self.send_mailing(mailing)
            messages.success(request, f'Рассылка запущена. Успешно отправлено: {success_count}')

        return redirect('mailing:mailing_detail', pk=mailing.pk)

    def send_mailing(self, mailing):
        """Отправка рассылки"""
        success_count = 0
        mailing.update_status()

        if mailing.status != Mailing.STATUS_STARTED:
            return success_count

        for client in mailing.clients.filter(is_active=True):
            try:
                send_mail(
                    subject=mailing.message.subject,
                    message=mailing.message.body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[client.email],
                    fail_silently=False,
                )
                MailingAttempt.log_attempt(
                    mailing=mailing,
                    client=client,
                    status=MailingAttempt.STATUS_SUCCESS,
                    response='200 OK'
                )
                success_count += 1
            except Exception as e:
                MailingAttempt.log_attempt(
                    mailing=mailing,
                    client=client,
                    status=MailingAttempt.STATUS_FAILED,
                    response=str(e)
                )

        # Если это периодическая рассылка, обновляем следующую отправку
        if mailing.frequency != 'once':
            mailing.calculate_next_send()

        return success_count


# =================== STATISTICS VIEWS ===================

class StatisticsView(LoginRequiredMixin, TemplateView):
    """Страница статистики"""
    template_name = 'mailing/statistics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Определяем, чьи данные показывать
        if user.is_staff or user.is_superuser:
            mailings = Mailing.objects.all()
            attempts = MailingAttempt.objects.all()
            clients = Client.objects.all()
        else:
            mailings = Mailing.objects.filter(owner=user)
            attempts = MailingAttempt.objects.filter(mailing__owner=user)
            clients = Client.objects.filter(owner=user)

        # Общая статистика
        context['total_mailings'] = mailings.count()
        context['active_mailings'] = mailings.filter(
            is_active=True,
            status=Mailing.STATUS_STARTED
        ).count()
        context['total_clients'] = clients.count()

        # Статистика по попыткам
        context['total_attempts'] = attempts.count()
        context['successful_attempts'] = attempts.filter(
            status=MailingAttempt.STATUS_SUCCESS
        ).count()
        context['failed_attempts'] = attempts.filter(
            status=MailingAttempt.STATUS_FAILED
        ).count()

        # Последние 10 попыток
        context['recent_attempts'] = attempts.select_related(
            'mailing', 'client'
        ).order_by('-attempt_time')[:10]

        # Рассылки по статусам
        context['mailings_by_status'] = mailings.values(
            'status'
        ).annotate(
            count=Count('id')
        ).order_by('status')

        # Статистика по дням (последние 7 дней)
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        context['attempts_by_day'] = attempts.filter(
            attempt_time__gte=seven_days_ago
        ).annotate(
            day=TruncDate('attempt_time')
        ).values('day').annotate(
            total=Count('id'),
            success=Count(Case(When(status=MailingAttempt.STATUS_SUCCESS, then=1))),
            failed=Count(Case(When(status=MailingAttempt.STATUS_FAILED, then=1)))
        ).order_by('day')

        return context


# =================== MANAGER VIEWS ===================

class AllMailingsView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Все рассылки для менеджера"""
    model = Mailing
    template_name = 'mailing/manager/all_mailings.html'
    context_object_name = 'mailings'
    paginate_by = 20

    def get_queryset(self):
        return Mailing.objects.all().select_related(
            'message', 'owner'
        ).prefetch_related('clients').order_by('-created_at')


class AllClientsView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Все клиенты для менеджера"""
    model = Client
    template_name = 'mailing/manager/all_clients.html'
    context_object_name = 'clients'
    paginate_by = 20

    def get_queryset(self):
        return Client.objects.all().select_related('owner').order_by('-created_at')


class MailingToggleView(LoginRequiredMixin, ManagerRequiredMixin, DetailView):
    """Включение/выключение рассылки менеджером"""
    model = Mailing

    def get(self, request, *args, **kwargs):
        mailing = self.get_object()
        mailing.is_active = not mailing.is_active
        mailing.save()

        action = "включена" if mailing.is_active else "выключена"
        messages.success(request, f'Рассылка #{mailing.id} {action}.')

        return redirect('mailing:manager_all_mailings')


# =================== API VIEWS ===================

def mailing_stats_api(request):
    """API для получения статистики (для AJAX)"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    user = request.user

    if user.is_staff or user.is_superuser:
        mailings = Mailing.objects.all()
        attempts = MailingAttempt.objects.all()
    else:
        mailings = Mailing.objects.filter(owner=user)
        attempts = MailingAttempt.objects.filter(mailing__owner=user)

    # Обновляем статусы
    for mailing in mailings:
        mailing.update_status()

    data = {
        'total_mailings': mailings.count(),
        'active_mailings': mailings.filter(
            status=Mailing.STATUS_STARTED,
            is_active=True
        ).count(),
        'total_attempts': attempts.count(),
        'successful_attempts': attempts.filter(
            status=MailingAttempt.STATUS_SUCCESS
        ).count(),
        'failed_attempts': attempts.filter(
            status=MailingAttempt.STATUS_FAILED
        ).count(),
        'last_updated': timezone.now().isoformat(),
    }

    return JsonResponse(data)