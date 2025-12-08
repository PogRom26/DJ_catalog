from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Q

from .models import Product, Category
from .forms import ProductForm, ProductStatusForm, ProductFilterForm
from .mixins import OwnerRequiredMixin, ProductPermissionMixin, ProductContextMixin, FilterMixin


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
    """Детальная информация о товаре - ТЕПЕРЬ ТРЕБУЕТ АВТОРИЗАЦИИ"""
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        """Ограничиваем доступ к товарам"""
        user = self.request.user
        return Product.get_products_for_user(user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        user = self.request.user

        context['can_edit'] = ProductPermissionMixin.can_edit_product(user, product)
        context['can_delete'] = ProductPermissionMixin.can_delete_product(user, product)
        context['can_unpublish'] = ProductPermissionMixin.can_unpublish_product(user)
        context['can_change_status'] = ProductPermissionMixin.can_change_status(user)
        context['can_publish'] = ProductPermissionMixin.can_publish_product(user)

        if context['can_change_status']:
            context['status_form'] = ProductStatusForm(instance=product)

        return context


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
    template_name = 'products/product_confirm_delete.html'

    def test_func(self):
        """Проверка прав на удаление"""
        product = self.get_object()
        user = self.request.user

        # Владелец или модератор могут удалять
        return (
                product.owner == user or
                user.has_perm('products.delete_product')
        )

    def get_success_url(self):
        # Если пользователь модератор, возвращаем в список товаров
        # Если владелец - в список своих товаров
        if self.request.user.has_perm('products.delete_product'):
            return reverse_lazy('products:list')
        return reverse_lazy('products:my_products')

    def delete(self, request, *args, **kwargs):
        """Обработка удаления с уведомлением"""
        product = self.get_object()
        product_name = product.name
        product_owner = product.owner

        response = super().delete(request, *args, **kwargs)

        # Отправляем уведомление владельцу, если удалил модератор
        if (request.user.has_perm('products.delete_product') and
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
@permission_required('products.can_publish_product', raise_exception=True)
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
@permission_required('products.can_unpublish_product', raise_exception=True)
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
@permission_required('products.can_change_publish_status', raise_exception=True)
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