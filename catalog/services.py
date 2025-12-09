import hashlib
import json
import logging
import pickle
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Avg, Count, Prefetch, Q, Sum
from django.utils import timezone
from django_redis import get_redis_connection

from .models import Category, Product

User = get_user_model()
logger = logging.getLogger(__name__)


class ProductService:
    """Сервис для работы с продуктами с кешированием"""

    @staticmethod
    def get_products_by_category(
            category_id: int,
            include_unpublished: bool = False,
            user: Optional[User] = None
    ) -> List[Product]:
        """
        Возвращает список продуктов в указанной категории с кешированием

        Args:
            category_id: ID категории
            include_unpublished: Включать ли неопубликованные товары
            user: Пользователь (для проверки прав)

        Returns:
            Список продуктов
        """
        # Генерируем ключ кеша
        user_id = user.id if user and user.is_authenticated else 'anon'
        cache_key = f'category_products_{category_id}_{include_unpublished}_{user_id}'

        # Пытаемся получить из кеша
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f'Возвращаем продукты категории {category_id} из кеша')
            return cached_result

        try:
            # Получаем категорию
            category = Category.objects.get(pk=category_id, is_active=True)

            # Базовый queryset
            if include_unpublished and user and user.has_perm('catalog.can_view_all_products'):
                products = Product.objects.filter(
                    category=category,
                    is_active=True
                ).select_related('owner', 'category')
            else:
                products = Product.get_published_products().filter(
                    category=category
                ).select_related('owner', 'category')

            # Преобразуем в список для кеширования
            products_list = list(products)

            # Кешируем на 10 минут
            cache.set(cache_key, products_list, 60 * 10)
            logger.debug(f'Продукты категории {category_id} закешированы')

            return products_list

        except Category.DoesNotExist:
            logger.error(f'Категория {category_id} не найдена или неактивна')
            return []

    @staticmethod
    def get_category_stats(category_id: int) -> Dict[str, Any]:
        """
        Возвращает статистику по категории с кешированием

        Args:
            category_id: ID категории

        Returns:
            Словарь со статистикой
        """
        cache_key = f'category_stats_{category_id}'
        stats = cache.get(cache_key)

        if stats:
            return stats

        try:
            category = Category.objects.get(pk=category_id)

            # Получаем статистику
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)

            products = Product.get_published_products().filter(category=category)

            stats = {
                'total_products': products.count(),
                'total_views': products.aggregate(Sum('views_count'))['views_count__sum'] or 0,
                'avg_price': products.aggregate(Avg('price'))['price__avg'] or 0,
                'new_last_week': products.filter(created_at__gte=week_ago).count(),
                'most_viewed': products.order_by('-views_count').first(),
                'most_expensive': products.order_by('-price').first(),
                'cheapest': products.order_by('price').first(),
                'last_updated': timezone.now().isoformat(),
            }

            # Кешируем на 30 минут
            cache.set(cache_key, stats, 60 * 30)

            return stats

        except Category.DoesNotExist:
            return {}

    @staticmethod
    def clear_category_cache(category_id: int) -> None:
        """Очищает кеш для категории"""
        from django_redis import get_redis_connection

        # Удаляем все связанные ключи
        cache_keys = [
            f'category_products_{category_id}_*',
            f'category_stats_{category_id}',
        ]

        cache.delete_many(cache_keys)

        # Также удаляем с помощью паттерна в Redis
        redis_conn = get_redis_connection('default')

        for pattern in cache_keys:
            keys = redis_conn.keys(f'dj_catalog:{pattern}')
            if keys:
                redis_conn.delete(*keys)

        logger.info(f'Кеш категории {category_id} очищен')


class ProductCacheService:
    """Сервис для низкоуровневого кеширования продуктов"""

    @staticmethod
    def get_cached_products(
            queryset,
            cache_key: str,
            timeout: int = 300,  # 5 минут по умолчанию
            force_refresh: bool = False,
            **filters
    ) -> List[Product]:
        """
        Низкоуровневое кеширование queryset продуктов

        Args:
            queryset: Базовый QuerySet
            cache_key: Ключ кеша
            timeout: Время жизни кеша в секундах
            force_refresh: Принудительно обновить кеш
            filters: Дополнительные фильтры

        Returns:
            Список продуктов
        """
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                try:
                    # Десериализуем из кеша
                    return pickle.loads(cached)
                except (pickle.PickleError, TypeError, AttributeError) as e:
                    logger.warning(f'Ошибка десериализации кеша {cache_key}: {e}')

        # Применяем фильтры
        if filters:
            queryset = queryset.filter(**filters)

        # Выполняем запрос и сериализуем для кеша
        result = list(queryset)

        try:
            cache.set(cache_key, pickle.dumps(result), timeout)
        except Exception as e:
            logger.error(f'Ошибка кеширования {cache_key}: {e}')

        return result

    @staticmethod
    def cache_product_list(view_name: str, timeout: int = 600):
        """
        Декоратор для кеширования списка продуктов в представлениях

        Args:
            view_name: Имя view для логирования
            timeout: Время жизни кеша в секундах

        Returns:
            Декоратор
        """

        def decorator(view_func):
            def wrapper(request, *args, **kwargs):
                # Генерируем уникальный ключ кеша на основе параметров
                cache_params = {
                    'view': view_name,
                    'path': request.path,
                    'query': request.GET.urlencode(),
                    'user_id': request.user.id if request.user.is_authenticated else 'anon',
                    'user_groups': list(request.user.groups.values_list('id', flat=True))
                    if request.user.is_authenticated else [],
                }

                cache_key = hashlib.md5(
                    json.dumps(cache_params, sort_keys=True).encode()
                ).hexdigest()

                full_cache_key = f'product_list_{cache_key}'

                # Проверяем кеш (игнорируем если есть параметр nocache)
                if not request.GET.get('nocache'):
                    cached_response = cache.get(full_cache_key)
                    if cached_response:
                        logger.debug(f'Возвращаем кешированный список для {view_name}')
                        return cached_response

                # Выполняем view и кешируем результат
                response = view_func(request, *args, **kwargs)

                # Кешируем только успешные GET ответы
                if request.method == 'GET' and response.status_code == 200:
                    try:
                        cache.set(full_cache_key, response, timeout)
                        logger.debug(f'Закеширован список для {view_name}')
                    except Exception as e:
                        logger.error(f'Ошибка кеширования {view_name}: {e}')

                return response

            return wrapper

        return decorator

    @staticmethod
    def get_homepage_products(limit: int = 8) -> List[Product]:
        """
        Кеширование товаров для главной страницы

        Args:
            limit: Количество товаров

        Returns:
            Список продуктов
        """
        cache_key = f'homepage_products_{limit}'
        products = cache.get(cache_key)

        if products is None:
            products = list(
                Product.get_published_products()
                .select_related('category', 'owner')
                .order_by('-views_count', '-created_at')[:limit]
            )

            # Кешируем на 5 минут
            cache.set(cache_key, products, 300)
            logger.debug(f'Закешированы товары для главной страницы')

        return products

    @staticmethod
    def get_new_products(days: int = 7, limit: int = 6) -> List[Product]:
        """
        Получение новых товаров с кешированием

        Args:
            days: За сколько дней считать новыми
            limit: Количество товаров

        Returns:
            Список новых продуктов
        """
        cache_key = f'new_products_{days}_{limit}'
        products = cache.get(cache_key)

        if products is None:
            date_threshold = timezone.now() - timedelta(days=days)

            products = list(
                Product.get_published_products()
                .filter(created_at__gte=date_threshold)
                .select_related('category', 'owner')
                .order_by('-created_at')[:limit]
            )

            # Кешируем на 15 минут
            cache.set(cache_key, products, 900)

        return products

    @staticmethod
    def get_popular_products(limit: int = 6) -> List[Product]:
        """
        Получение популярных товаров с кешированием

        Args:
            limit: Количество товаров

        Returns:
            Список популярных продуктов
        """
        cache_key = f'popular_products_{limit}'
        products = cache.get(cache_key)

        if products is None:
            products = list(
                Product.get_published_products()
                .select_related('category', 'owner')
                .order_by('-views_count')[:limit]
            )

            # Кешируем на 10 минут
            cache.set(cache_key, products, 600)

        return products

    @staticmethod
    def get_related_products(product: Product, limit: int = 4) -> List[Product]:
        """
        Получение связанных товаров с кешированием

        Args:
            product: Товар для которого ищем связанные
            limit: Количество товаров

        Returns:
            Список связанных продуктов
        """
        cache_key = f'related_products_{product.id}_{limit}'
        related = cache.get(cache_key)

        if related is None:
            # Ищем по категории
            if product.category:
                related = list(
                    Product.get_published_products()
                    .filter(category=product.category)
                    .exclude(pk=product.pk)
                    .select_related('owner', 'category')[:limit]
                )
            else:
                # Если нет категории, ищем по ключевым словам в названии
                words = product.name.split()[:3]
                query = Q()
                for word in words:
                    if len(word) > 3:  # Только слова длиннее 3 символов
                        query |= Q(name__icontains=word) | Q(description__icontains=word)

                if query:
                    related = list(
                        Product.get_published_products()
                        .filter(query)
                        .exclude(pk=product.pk)
                        .select_related('owner', 'category')[:limit]
                    )
                else:
                    related = []

            # Кешируем на 30 минут
            cache.set(cache_key, related, 1800)

        return related

    @staticmethod
    def invalidate_product_cache(product_id: int) -> None:
        """Инвалидация кеша для конкретного продукта"""
        from django_redis import get_redis_connection

        patterns = [
            f'*product*{product_id}*',
            f'*related*{product_id}*',
            f'homepage_products_*',
            f'new_products_*',
            f'popular_products_*',
        ]

        redis_conn = get_redis_connection('default')

        for pattern in patterns:
            keys = redis_conn.keys(f'dj_catalog:{pattern}')
            if keys:
                redis_conn.delete(*keys)

        logger.info(f'Кеш продукта {product_id} инвалидирован')

    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """Получение статистики кеша"""
        redis_conn = get_redis_connection('default')

        try:
            info = redis_conn.info()

            # Получаем ключи с префиксом
            pattern = 'dj_catalog:*product*'
            product_keys = redis_conn.keys(pattern)

            pattern = 'dj_catalog:*category*'
            category_keys = redis_conn.keys(pattern)

            stats = {
                'redis_version': info.get('redis_version', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'N/A'),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'product_cache_keys': len(product_keys),
                'category_cache_keys': len(category_keys),
                'uptime_days': info.get('uptime_in_days', 0),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': (
                                    info.get('keyspace_hits', 0) /
                                    max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1)
                            ) * 100,
            }

            return stats

        except Exception as e:
            logger.error(f'Ошибка получения статистики Redis: {e}')
            return {}


class CacheManager:
    """Управление кешем для всего приложения"""

    @staticmethod
    def warmup_cache() -> Dict[str, int]:
        """
        Предварительная загрузка кеша (warmup)

        Returns:
            Словарь с количеством закешированных элементов
        """
        results = {
            'homepage_products': 0,
            'new_products': 0,
            'popular_products': 0,
            'categories': 0,
        }

        try:
            # Кешируем товары для главной
            ProductCacheService.get_homepage_products(12)
            results['homepage_products'] = 12

            # Кешируем новые товары
            ProductCacheService.get_new_products(7, 8)
            results['new_products'] = 8

            # Кешируем популярные товары
            ProductCacheService.get_popular_products(8)
            results['popular_products'] = 8

            # Кешируем статистику категорий
            categories = Category.objects.filter(is_active=True)
            for category in categories:
                ProductService.get_category_stats(category.id)
                results['categories'] += 1

            logger.info(f'Кеш успешно разогрет: {results}')

        except Exception as e:
            logger.error(f'Ошибка при разогреве кеша: {e}')

        return results

    @staticmethod
    def clear_all_cache() -> Dict[str, int]:
        """
        Очистка всего кеша приложения

        Returns:
            Словарь с количеством удаленных ключей
        """
        from django_redis import get_redis_connection

        redis_conn = get_redis_connection('default')

        # Получаем все ключи с префиксом нашего приложения
        pattern = 'dj_catalog:*'
        keys = redis_conn.keys(pattern)

        if keys:
            deleted = redis_conn.delete(*keys)
            logger.info(f'Удалено {deleted} ключей кеша')
            return {'deleted_keys': deleted}

        return {'deleted_keys': 0}

    @staticmethod
    def optimize_cache() -> Dict[str, Any]:
        """
        Оптимизация кеша (удаление устаревших ключей, сжатие и т.д.)

        Returns:
            Словарь с результатами оптимизации
        """
        from django_redis import get_redis_connection

        redis_conn = get_redis_connection('default')

        results = {
            'memory_before': redis_conn.info().get('used_memory_human', 'N/A'),
            'keys_before': len(redis_conn.keys('dj_catalog:*')),
        }

        try:
            # Запускаем очистку устаревших ключей
            redis_conn.bgrewriteaof()  # Фоновая оптимизация

            results['memory_after'] = redis_conn.info().get('used_memory_human', 'N/A')
            results['keys_after'] = len(redis_conn.keys('dj_catalog:*'))
            results['optimization'] = 'completed'

            logger.info(f'Оптимизация кеша завершена: {results}')

        except Exception as e:
            logger.error(f'Ошибка оптимизации кеша: {e}')
            results['optimization'] = 'failed'
            results['error'] = str(e)

        return results


# Экспорт основных классов
__all__ = [
    'ProductService',
    'ProductCacheService',
    'CacheManager',
    'logger',
]