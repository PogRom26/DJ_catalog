from django.contrib.auth.decorators import user_passes_test
from functools import wraps
from django.core.cache import cache
from django.db import transaction


def content_manager_required(view_func=None):
    actual_decorator = user_passes_test(
        lambda u: u.groups.filter(name='Контент-менеджер').exists() or u.is_superuser
    )
    return actual_decorator(view_func)


def cache_product_detail(timeout=900):
    """
    Декоратор для кеширования детальной страницы продукта
    с автоматической инвалидацией при изменении
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from catalog.cache_utils import ProductCacheManager

            # Генерируем ключ кеша
            cache_key = f'product_detail_{kwargs.get("pk")}_{request.user.id if request.user.is_authenticated else "anon"}'

            # Проверяем кеш для GET запросов
            if request.method == 'GET':
                cached_response = cache.get(cache_key)
                if cached_response:
                    return cached_response

            # Выполняем view
            response = view_func(request, *args, **kwargs)

            # Кешируем GET ответы
            if request.method == 'GET' and response.status_code == 200:
                cache.set(cache_key, response, timeout)

            # При POST/PUT/DELETE инвалидируем кеш
            elif request.method in ['POST', 'PUT', 'DELETE']:
                product_id = kwargs.get('pk')
                if product_id:
                    ProductCacheManager.invalidate_product_cache(product_id)

            return response

        return wrapper

    return decorator