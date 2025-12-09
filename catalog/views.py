import hashlib
import json
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie, vary_on_headers
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from django_redis import get_redis_connection

from .forms import ProductFilterForm, ProductForm, ProductStatusForm
from .mixins import (FilterMixin, OwnerRequiredMixin, ProductContextMixin,
                     ProductPermissionMixin)
from .models import Category, Product


class HomeView(TemplateView):
    template_name = 'catalog/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Можно добавить контекст, например, последние товары
        context['latest_products'] = Product.get_published_products()[:4]
        context['categories'] = Category.objects.filter(is_active=True)[:6]
        return context


# Страница контактов
class ContactView(TemplateView):
    template_name = 'catalog/contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Контакты')
        return context

    def post(self, request, *args, **kwargs):
        """Обработка формы обратной связи"""
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()

        if name and email and message:
            try:
                # Отправка email
                subject = f"Новое сообщение от {name}"
                body = f"""
                Имя: {name}
                Email: {email}
                Сообщение:
                {message}
                """

                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ADMIN_EMAIL],
                    fail_silently=False,
                )

                messages.success(request, _('Ваше сообщение отправлено! Мы скоро ответим.'))
            except Exception as e:
                messages.error(request, _('Ошибка при отправке сообщения. Попробуйте позже.'))
        else:
            messages.error(request, _('Пожалуйста, заполните все поля.'))

        return render(request, self.template_name, self.get_context_data())

class ProductListView(ProductContextMixin, FilterMixin, ListView):
    """Список товаров с учётом прав доступа"""
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        """Фильтрация товаров в зависимости от прав пользователя"""
        user = self.request.user
        queryset = Product.get_products_for_user(user)

        # Применяем фильтры из миксина
        queryset = self.get_filtered_queryset(queryset)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Добавляем форму фильтрации
        context['filter_form'] = self.get_filter_form()

        # Добавляем категории для фильтра
        context['categories'] = Category.objects.filter(is_active=True)

        # Добавляем текущие параметры фильтрации для пагинации
        params = self.request.GET.copy()
        if 'page' in params:
            del params['page']
        context['query_params'] = params.urlencode()

        return context


class ProductDetailView(LoginRequiredMixin, DetailView):
    """Детальная информация о товаре с комплексным кешированием"""
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

    # Время кеширования в секундах (15 минут)
    CACHE_TIMEOUT = 60 * 15

    @method_decorator(vary_on_cookie)  # Разный кеш для разных пользователей
    @method_decorator(vary_on_headers('Authorization', 'Accept-Language'))  # Учитываем язык и авторизацию
    @method_decorator(cache_page(CACHE_TIMEOUT, cache='default'))  # Кешируем страницу
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_cache_key(self):
        """Генерирует уникальный ключ кеша для страницы продукта"""
        product_id = self.kwargs.get('pk')
        user = self.request.user

        # Создаем хэш на основе пользователя и параметров запроса
        cache_params = {
            'product_id': product_id,
            'user_id': user.id if user.is_authenticated else 'anonymous',
            'user_groups': list(user.groups.values_list('id', flat=True)) if user.is_authenticated else [],
            'user_permissions': list(user.get_all_permissions()) if user.is_authenticated else [],
            'query_params': self.request.GET.urlencode(),
            'accept_language': self.request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
        }

        # Создаем MD5 хэш из параметров
        params_str = json.dumps(cache_params, sort_keys=True)
        cache_hash = hashlib.md5(params_str.encode()).hexdigest()

        return f'product_detail_{product_id}_{cache_hash}'

    def get_queryset(self):
        """Ограничиваем доступ к товарам с кешированием"""
        user = self.request.user
        cache_key = f'product_queryset_user_{user.id if user.is_authenticated else "anon"}'

        # Пытаемся получить кешированный queryset
        cached_queryset = cache.get(cache_key)
        if cached_queryset is not None:
            return cached_queryset

        # Если нет в кеше, выполняем запрос
        queryset = Product.get_products_for_user(user)

        # Кешируем на 5 минут
        cache.set(cache_key, queryset, 60 * 5)

        return queryset

    def get_object(self, queryset=None):
        """Получаем объект с кешированием"""
        if queryset is None:
            queryset = self.get_queryset()

        product_id = self.kwargs.get('pk')
        cache_key = f'product_object_{product_id}'

        # Пытаемся получить продукт из кеша
        cached_product = cache.get(cache_key)
        if cached_product:
            return cached_product

        # Если нет в кеше, получаем из базы
        product = super().get_object(queryset)

        # Кешируем объект продукта на 10 минут
        cache.set(cache_key, product, 60 * 10)

        return product

    def get_context_data(self, **kwargs):
        """Получаем контекст с кешированием"""
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        user = self.request.user

        # Генерируем ключ кеша для контекста
        context_cache_key = f'product_context_{product.pk}_user_{user.id if user.is_authenticated else "anon"}'

        # Пытаемся получить контекст из кеша
        cached_context = cache.get(context_cache_key)
        if cached_context:
            return cached_context

        # Получаем базовые права
        can_edit = ProductPermissionMixin.can_edit_product(user, product)
        can_delete = ProductPermissionMixin.can_delete_product(user, product)
        can_unpublish = ProductPermissionMixin.can_unpublish_product(user)
        can_change_status = ProductPermissionMixin.can_change_status(user)
        can_publish = ProductPermissionMixin.can_publish_product(user)

        # Добавляем в контекст
        context.update({
            'can_edit': can_edit,
            'can_delete': can_delete,
            'can_unpublish': can_unpublish,
            'can_change_status': can_change_status,
            'can_publish': can_publish,
        })

        # Форма изменения статуса (только для тех, у кого есть права)
        if can_change_status:
            context['status_form'] = ProductStatusForm(instance=product)

        # Дополнительные данные с кешированием
        context.update(self.get_cached_additional_data(product, user))

        # Кешируем контекст на 5 минут
        cache.set(context_cache_key, context, 60 * 5)

        # Логируем попадание в кеш для отладки
        if self.request.user.is_staff:
            context['cache_info'] = self.get_cache_info(product, user)

        # Увеличиваем счетчик просмотров (с оптимизацией через кеш)
        self.increment_views_with_cache(product)

        return context

    def get_cached_additional_data(self, product, user):
        """Получаем дополнительные данные с кешированием"""
        cache_key = f'product_additional_{product.pk}'
        additional_data = cache.get(cache_key)

        if additional_data is None:
            # Получаем похожие товары
            similar_products = Product.get_published_products().filter(
                category=product.category
            ).exclude(pk=product.pk).select_related('owner')[:4]

            # Получаем историю изменений (если есть модель ProductHistory)
            try:
                from catalog.models import ProductHistory
                changes_history = ProductHistory.objects.filter(
                    product=product
                ).select_related('changed_by').order_by('-changed_at')[:5]
            except:
                changes_history = []

            # Статистика просмотров
            views_stats = {
                'total': product.views_count,
                'today': self.get_todays_views(product),
                'week': self.get_weekly_views(product),
                'popularity': self.calculate_popularity(product),
            }

            additional_data = {
                'similar_products': similar_products,
                'changes_history': changes_history,
                'views_stats': views_stats,
                'owner_info': self.get_owner_info(product.owner) if product.owner else None,
                'category_stats': self.get_category_stats(product.category) if product.category else None,
            }

            # Кешируем на 10 минут
            cache.set(cache_key, additional_data, 60 * 10)

        return additional_data

    def increment_views_with_cache(self, product):
        """Увеличиваем счетчик просмотров с оптимизацией через кеш"""
        cache_key = f'product_views_increment_{product.pk}'
        redis_conn = get_redis_connection('default')

        # Используем атомарный инкремент в Redis
        current_increment = redis_conn.incr(cache_key)

        # Сохраняем в базу только при достижении порога или через время
        save_threshold = 10  # Сохраняем каждые 10 просмотров
        last_save_key = f'product_last_save_{product.pk}'

        if current_increment >= save_threshold or not redis_conn.exists(last_save_key):
            # Обновляем в базе
            product.views_count = models.F('views_count') + current_increment
            product.save(update_fields=['views_count'])

            # Сбрасываем счетчик
            redis_conn.delete(cache_key)

            # Устанавливаем блокировку на 30 секунд
            redis_conn.setex(last_save_key, 30, 1)

            # Инвалидируем кеш статистики
            cache.delete(f'product_additional_{product.pk}')
            cache.delete(f'product_stats_{product.pk}')

        # Также инкрементируем счетчик для сессии пользователя
        if self.request.user.is_authenticated:
            session_key = f'user_{self.request.user.id}_viewed_{product.pk}'
            if not redis_conn.exists(session_key):
                redis_conn.setex(session_key, 3600, 1)  # 1 час

    def get_todays_views(self, product):
        """Получаем количество просмотров за сегодня с кешированием"""
        cache_key = f'product_views_today_{product.pk}_{timezone.now().date()}'
        todays_views = cache.get(cache_key)

        if todays_views is None:
            # Здесь можно добавить логику подсчета просмотров за день
            # Например, через отдельную модель ViewLog
            todays_views = 0
            cache.set(cache_key, todays_views, 60 * 60 * 24)  # Кешируем на сутки

        return todays_views

    def get_weekly_views(self, product):
        """Получаем количество просмотров за неделю с кешированием"""
        cache_key = f'product_views_week_{product.pk}_{timezone.now().isocalendar()[1]}'
        weekly_views = cache.get(cache_key)

        if weekly_views is None:
            # Логика подсчета просмотров за неделю
            weekly_views = 0
            cache.set(cache_key, weekly_views, 60 * 60 * 24 * 7)  # Кешируем на неделю

        return weekly_views

    def calculate_popularity(self, product):
        """Рассчитываем популярность товара"""
        total_views = product.views_count

        if total_views > 1000:
            return 'very_high'
        elif total_views > 500:
            return 'high'
        elif total_views > 100:
            return 'medium'
        elif total_views > 50:
            return 'low'
        else:
            return 'very_low'

    def get_owner_info(self, owner):
        """Получаем информацию о владельце с кешированием"""
        if not owner:
            return None

        cache_key = f'owner_info_{owner.id}'
        owner_info = cache.get(cache_key)

        if owner_info is None:
            owner_info = {
                'username': owner.username,
                'email': owner.email,
                'products_count': Product.objects.filter(owner=owner, is_active=True).count(),
                'joined': owner.date_joined.strftime('%d.%m.%Y'),
                'last_login': owner.last_login.strftime('%d.%m.%Y %H:%M') if owner.last_login else 'никогда',
            }
            cache.set(cache_key, owner_info, 60 * 30)  # 30 минут

        return owner_info

    def get_category_stats(self, category):
        """Получаем статистику по категории с кешированием"""
        if not category:
            return None

        cache_key = f'category_stats_{category.id}'
        stats = cache.get(cache_key)

        if stats is None:
            products_in_category = Product.get_published_products().filter(category=category)

            stats = {
                'total_products': products_in_category.count(),
                'avg_price': products_in_category.aggregate(models.Avg('price'))['price__avg'] or 0,
                'total_views': products_in_category.aggregate(models.Sum('views_count'))['views_count__sum'] or 0,
                'most_popular': products_in_category.order_by('-views_count').first(),
            }

            cache.set(cache_key, stats, 60 * 60)  # 1 час

        return stats

    def get_cache_info(self, product, user):
        """Информация о кеше для отладки (только для staff)"""
        cache_keys = {
            'page_cache': self.get_cache_key(),
            'object_cache': f'product_object_{product.pk}',
            'context_cache': f'product_context_{product.pk}_user_{user.id if user.is_authenticated else "anon"}',
            'additional_cache': f'product_additional_{product.pk}',
            'views_increment': f'product_views_increment_{product.pk}',
        }

        cache_status = {}
        redis_conn = get_redis_connection('default')

        for key, cache_key in cache_keys.items():
            exists = cache.get(cache_key) is not None or redis_conn.exists(f'dj_catalog:{cache_key}')
            cache_status[key] = {
                'key': cache_key,
                'exists': exists,
                'ttl': redis_conn.ttl(f'dj_catalog:{cache_key}') if exists else -2,
            }

        return cache_status

    def get_template_names(self):
        """Можно кешировать выбор шаблона"""
        cache_key = f'product_template_{self.object.pk}_{self.request.user.id if self.request.user.is_authenticated else "anon"}'
        template_name = cache.get(cache_key)

        if template_name is None:
            # Логика выбора шаблона
            if self.request.user.is_staff:
                template_name = 'products/product_detail_staff.html'
            elif self.object.owner == self.request.user:
                template_name = 'products/product_detail_owner.html'
            else:
                template_name = 'products/product_detail.html'

            cache.set(cache_key, template_name, 60 * 60)  # 1 час

        return [template_name]


class ProductCreateView(LoginRequiredMixin, CreateView):
    """Создание нового товара"""
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'

    def get_form_kwargs(self):
        """Передаем пользователя в форму"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Обработка успешного создания товара"""
        response = super().form_valid(form)

        # Отправляем уведомление администратору
        if self.object.publish_status == Product.PublishStatus.PENDING_REVIEW:
            self._send_product_submission_notification()

        messages.success(
            self.request,
            _('Товар успешно создан! Статус: {}').format(
                self.object.get_publish_status_display()
            )
        )

        return response

    def get_success_url(self):
        return reverse_lazy('products:detail', kwargs={'pk': self.object.pk})

    def _send_product_submission_notification(self):
        """Отправка уведомления о новом товаре на проверку"""
        try:
            subject = _('Новый товар ожидает проверки: {}').format(self.object.name)
            message = render_to_string('products/emails/product_submission.txt', {
                'product': self.object,
                'user': self.request.user,
                'site_url': settings.SITE_URL,
            })

            # Получаем emails админов
            from django.contrib.auth.models import User
            admin_emails = User.objects.filter(
                groups__name='Модератор продуктов',
                is_active=True
            ).values_list('emails', flat=True)

            # Фильтруем пустые emails
            admin_emails = [email for email in admin_emails if email]

            if admin_emails:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    admin_emails,
                    fail_silently=False,
                )
        except Exception as e:
            # Логируем ошибку, но не прерываем создание товара
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка отправки уведомления: {e}")


class ProductUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование товара - только владелец"""
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'

    def get_form_kwargs(self):
        """Передаем пользователя в форму"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('products:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        """Обработка успешного обновления"""
        response = super().form_valid(form)

        # Отправляем уведомление, если статус изменился на "на проверке"
        if form.cleaned_data.get('publish_status') == Product.PublishStatus.PENDING_REVIEW:
            self._send_product_update_notification()

        messages.success(self.request, _('Товар успешно обновлен!'))
        return response

    def _send_product_update_notification(self):
        """Отправка уведомления об обновлении товара"""
        try:
            subject = _('Товар обновлен и ожидает проверки: {}').format(self.object.name)
            message = render_to_string('products/emails/product_update.txt', {
                'product': self.object,
                'user': self.request.user,
                'site_url': settings.SITE_URL,
            })

            # Получаем emails админов
            from django.contrib.auth.models import User
            admin_emails = User.objects.filter(
                groups__name='Модератор продуктов',
                is_active=True
            ).values_list('emails', flat=True)

            admin_emails = [email for email in admin_emails if email]

            if admin_emails:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    admin_emails,
                    fail_silently=False,
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка отправки уведомления об обновлении: {e}")


class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление товара - владелец или модератор"""
    model = Product
    template_name = 'catalog/product_confirm_delete.html'

    def test_func(self):
        """Проверка прав на удаление"""
        product = self.get_object()
        user = self.request.user

        # Владелец или модератор могут удалять
        return (
                product.owner == user or
                user.has_perm('catalog.delete_product')
        )

    def get_success_url(self):
        # Если пользователь модератор, возвращаем в список товаров
        # Если владелец - в список своих товаров
        if self.request.user.has_perm('catalog.delete_product'):
            return reverse_lazy('catalog:list')
        return reverse_lazy('catalog:my_products')

    def delete(self, request, *args, **kwargs):
        """Обработка удаления с уведомлением"""
        product = self.get_object()
        product_name = product.name
        product_owner = product.owner

        response = super().delete(request, *args, **kwargs)

        # Отправляем уведомление владельцу, если удалил модератор
        if (request.user.has_perm('catalog.delete_product') and
                request.user != product_owner and
                product_owner and
                product_owner.email):
            self._send_product_deletion_notification(product_name, product_owner)

        messages.success(request, _('Товар успешно удален!'))
        return response

    def _send_product_deletion_notification(self, product_name, product_owner):
        """Отправка уведомления владельцу о удалении товара"""
        try:
            subject = _('Ваш товар был удален: {}').format(product_name)
            message = render_to_string('products/emails/product_deleted.txt', {
                'product_name': product_name,
                'moderator': self.request.user,
                'owner': product_owner,
                'site_url': settings.SITE_URL,
            })

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [product_owner.email],
                fail_silently=False,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка отправки уведомления об удалении: {e}")


# Декораторные представления для действий с публикацией

@login_required
@permission_required('catalog.can_publish_product', raise_exception=True)
def publish_product(request, pk):
    """Публикация товара - только модераторы"""
    product = get_object_or_404(Product, pk=pk)

    if product.publish_status != Product.PublishStatus.PUBLISHED:
        old_status = product.publish_status
        product.publish_status = Product.PublishStatus.PUBLISHED
        product.save()

        # Отправляем уведомление владельцу
        if product.owner and product.owner.email:
            _send_status_change_notification(
                product,
                product.owner,
                old_status,
                product.publish_status,
                request.user
            )

        messages.success(request, _('Товар успешно опубликован!'))
    else:
        messages.warning(request, _('Товар уже опубликован'))

    return redirect('products:detail', pk=pk)


@login_required
@permission_required('catalog.can_unpublish_product', raise_exception=True)
def unpublish_product(request, pk):
    """Отмена публикации товара - только модераторы"""
    product = get_object_or_404(Product, pk=pk)

    if product.publish_status == Product.PublishStatus.PUBLISHED:
        old_status = product.publish_status
        product.publish_status = Product.PublishStatus.DRAFT
        product.save()

        # Отправляем уведомление владельцу
        if product.owner and product.owner.email:
            _send_status_change_notification(
                product,
                product.owner,
                old_status,
                product.publish_status,
                request.user
            )

        messages.success(request, _('Публикация товара отменена'))
    else:
        messages.warning(request, _('Товар не опубликован'))

    return redirect('products:detail', pk=pk)


@login_required
@permission_required('catalog.can_change_publish_status', raise_exception=True)
def change_product_status(request, pk):
    """Изменение статуса товара - только модераторы"""
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        old_status = product.publish_status
        form = ProductStatusForm(request.POST, instance=product)
        if form.is_valid():
            form.save()

            # Отправляем уведомление владельцу
            if product.owner and product.owner.email:
                _send_status_change_notification(
                    product,
                    product.owner,
                    old_status,
                    product.publish_status,
                    request.user
                )

            messages.success(request, _('Статус товара изменен'))

    return redirect('products:detail', pk=pk)


class MyProductsView(LoginRequiredMixin, ListView):
    """Товары текущего пользователя"""
    model = Product
    template_name = 'products/my_products.html'
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        return Product.objects.filter(owner=self.request.user).order_by('-created_at')


def _send_status_change_notification(product, owner, old_status, new_status, moderator):
    """Отправка уведомления об изменении статуса"""
    try:
        subject = _('Статус вашего товара изменен: {}').format(product.name)
        message = render_to_string('products/emails/status_changed.txt', {
            'product': product,
            'old_status': Product.PublishStatus(old_status).label,
            'new_status': Product.PublishStatus(new_status).label,
            'moderator': moderator,
            'owner': owner,
            'site_url': settings.SITE_URL,
        })

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [owner.email],
            fail_silently=False,
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка отправки уведомления об изменении статуса: {e}")