from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied


def content_manager_required(view_func):
    """
    Декоратор для проверки, что пользователь является контент-менеджером
    """

    def check_user(user):
        # Проверяем, что пользователь в группе "Контент-менеджер" или суперпользователь
        return user.groups.filter(name="Контент-менеджер").exists() or user.is_superuser

    def wrapper(request, *args, **kwargs):
        if not check_user(request.user):
            messages.error(
                request, "Доступ запрещен. Требуются права контент-менеджера."
            )
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper
