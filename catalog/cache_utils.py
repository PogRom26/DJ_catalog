import hashlib
import json

from django.core.cache import cache
from django_redis import get_redis_connection


class ProductCacheManager:
    """Менеджер для управления кешем продуктов"""

    @staticmethod
    def invalidate_product_cache(product_id):
        """Полная инвалидация кеша для продукта"""
        redis_conn = get_redis_connection('default')

        # Паттерны для поиска ключей кеша
        patterns = [
            f'product_detail_*_{product_id}_*',
            f'product_object_{product_id}',
            f'product_context_{product_id}_*',
            f'product_additional_{product_id}',
            f'product_stats_{product_id}',
            f'product_queryset_*',
            f'product_template_{product_id}_*',
            f'product_views_*_{product_id}_*',
            f'product_views_increment_{product_id}',
            f'product_last_save_{product_id}',
        ]

        deleted_keys = []

        for pattern in patterns:
            # Ищем ключи по паттерну
            keys = redis_conn.keys(f'dj_catalog:{pattern}')
            if keys:
                redis_conn.delete(*keys)
                deleted_keys.extend([k.decode() for k in keys])

        return deleted_keys

    @staticmethod
    def invalidate_user_cache(user_id):
        """Инвалидация кеша, связанного с пользователем"""
        redis_conn = get_redis_connection('default')
        patterns = [
            f'*_user_{user_id}',
            f'product_context_*_user_{user_id}',
            f'product_queryset_user_{user_id}',
        ]

        for pattern in patterns:
            keys = redis_conn.keys(f'dj_catalog:{pattern}')
            if keys:
                redis_conn.delete(*keys)

    @staticmethod
    def get_cache_stats():
        """Статистика по кешу продуктов"""
        redis_conn = get_redis_connection('default')

        # Получаем все ключи с префиксом dj_catalog
        all_keys = redis_conn.keys('dj_catalog:*')

        stats = {
            'total_keys': len(all_keys),
            'product_keys': 0,
            'user_keys': 0,
            'category_keys': 0,
            'memory_usage': redis_conn.info().get('used_memory_human', 'N/A'),
        }

        for key in all_keys:
            key_str = key.decode()
            if 'product_' in key_str:
                stats['product_keys'] += 1
            if '_user_' in key_str:
                stats['user_keys'] += 1
            if 'category_' in key_str:
                stats['category_keys'] += 1

        return stats

    @staticmethod
    def warmup_product_cache(product_ids):
        """Предварительная загрузка кеша для продуктов"""
        from catalog.models import Product

        products = Product.objects.filter(id__in=product_ids).select_related('owner', 'category')

        for product in products:
            # Кешируем объект
            cache_key = f'product_object_{product.id}'
            cache.set(cache_key, product, 60 * 30)

            # Кешируем дополнительные данные
            # ... можно добавить кеширование похожих товаров и т.д.