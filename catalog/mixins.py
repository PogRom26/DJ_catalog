from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class OwnerRequiredMixin(UserPassesTestMixin):
    """
    Миксин для проверки, что пользователь является владельцем объекта.
    Используется для редактирования товаров.
    """
    permission_denied_message = _('Вы не являетесь владельцем этого товара')
    redirect_url = None

    def test_func(self):
        """Проверка, является ли пользователь владельцем"""
        obj = self.get_object()
        return obj.owner == self.request.user

    def handle_no_permission(self):
        """Обработка отказа в доступе"""
        messages.error(self.request, self.permission_denied_message)

        if self.redirect_url:
            return HttpResponseRedirect(self.redirect_url)

        # Пытаемся перенаправить на детальную страницу объекта
        try:
            obj = self.get_object()
            return HttpResponseRedirect(
                reverse('products:detail', kwargs={'pk': obj.pk})
            )
        except:
            # Если не получилось, перенаправляем на список товаров
            return HttpResponseRedirect(reverse('products:list'))


class ModeratorRequiredMixin(UserPassesTestMixin):
    """
    Миксин для проверки, что пользователь является модератором.
    Используется для действий, требующих прав модератора.
    """
    permission_denied_message = _('Требуются права модератора')
    permission_codename = None

    def test_func(self):
        """Проверка прав модератора"""
        if self.permission_codename:
            return self.request.user.has_perm(self.permission_codename)
        return False

    def handle_no_permission(self):
        """Обработка отказа в доступе"""
        messages.error(self.request, self.permission_denied_message)
        return HttpResponseRedirect(reverse('products:list'))


class ProductPermissionMixin:
    """
    Миксин с утилитами для проверки прав доступа к товарам.
    Используется в представлениях и шаблонах.
    """

    @staticmethod
    def can_view_product(user, product):
        """Может ли пользователь просматривать товар"""
        if not product.is_active:
            return False

        if product.publish_status == product.PublishStatus.PUBLISHED:
            return True

        if not user.is_authenticated:
            return False

        if product.owner == user:
            return True

        if user.has_perm('catalog.can_view_all_products'):
            return True

        return False

    @staticmethod
    def can_edit_product(user, product):
        """Может ли пользователь редактировать товар"""
        if not user.is_authenticated:
            return False

        # Владелец может редактировать свои товары
        if product.owner == user:
            return True

        # Модераторы могут редактировать любые товары
        if user.has_perm('catalog.change_product'):
            return True

        return False

    @staticmethod
    def can_delete_product(user, product):
        """Может ли пользователь удалить товар"""
        if not user.is_authenticated:
            return False

        # Владелец может удалять свои товары
        if product.owner == user:
            return True

        # Модераторы могут удалять любые товары
        if user.has_perm('catalog.delete_product'):
            return True

        return False

    @staticmethod
    def can_publish_product(user):
        """Может ли пользователь публиковать товары"""
        return user.is_authenticated and user.has_perm('catalog.can_publish_product')

    @staticmethod
    def can_unpublish_product(user):
        """Может ли пользователь отменять публикацию"""
        return user.is_authenticated and user.has_perm('catalog.can_unpublish_product')

    @staticmethod
    def can_change_status(user):
        """Может ли пользователь изменять статус публикации"""
        return user.is_authenticated and user.has_perm('catalog.can_change_publish_status')

    @staticmethod
    def can_manage_all_products(user):
        """Может ли пользователь управлять всеми товарами"""
        return user.is_authenticated and (
                user.has_perm('products.can_view_all_products') or
                user.has_perm('products.delete_product') or
                user.is_superuser
        )

    @staticmethod
    def get_available_statuses(user):
        """Получить доступные статусы для пользователя"""
        all_statuses = [
            ('draft', 'Черновик'),
            ('pending_review', 'На проверке'),
        ]

        if ProductPermissionMixin.can_publish_product(user):
            all_statuses.extend([
                ('published', 'Опубликовано'),
                ('rejected', 'Отклонено'),
                ('archived', 'Архивирован'),
            ])

        return all_statuses


class ProductContextMixin:
    """
    Миксин для добавления контекста прав доступа в шаблоны
    """

    def get_context_data(self, **kwargs):
        """Добавляем информацию о правах доступа в контекст"""
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Основные флаги прав доступа
        context['can_create'] = user.is_authenticated
        context['is_moderator'] = ProductPermissionMixin.can_change_status(user)
        context['can_manage_all'] = ProductPermissionMixin.can_manage_all_products(user)

        # Если есть объект товара, добавляем специфичные права
        if hasattr(self, 'object') and self.object:
            product = self.object
            context['can_edit'] = ProductPermissionMixin.can_edit_product(user, product)
            context['can_delete'] = ProductPermissionMixin.can_delete_product(user, product)
            context['can_unpublish'] = ProductPermissionMixin.can_unpublish_product(user)
            context['can_change_status'] = ProductPermissionMixin.can_change_status(user)
            context['can_publish'] = ProductPermissionMixin.can_publish_product(user)

        return context


class FilterMixin:
    """
    Миксин для обработки фильтрации в списках товаров
    """

    def get_filter_form(self):
        """Получить форму фильтрации"""
        from .forms import ProductFilterForm
        return ProductFilterForm(self.request.GET or None)

    def get_filtered_queryset(self, queryset):
        """Применить фильтры к queryset"""
        filter_form = self.get_filter_form()

        if filter_form.is_valid():
            data = filter_form.cleaned_data

            # Поиск по тексту
            if data.get('q'):
                queryset = queryset.filter(
                    models.Q(name__icontains=data['q']) |
                    models.Q(description__icontains=data['q'])
                )

            # Фильтр по статусу
            if data.get('status'):
                queryset = queryset.filter(publish_status=data['status'])

            # Фильтр по категории
            if data.get('category'):
                queryset = queryset.filter(category=data['category'])

            # Фильтр по цене
            if data.get('min_price'):
                queryset = queryset.filter(price__gte=data['min_price'])

            if data.get('max_price'):
                queryset = queryset.filter(price__lte=data['max_price'])

        return queryset