from django.contrib.auth.decorators import user_passes_test


def content_manager_required(view_func=None):
    actual_decorator = user_passes_test(
        lambda u: u.groups.filter(name='Контент-менеджер').exists() or u.is_superuser
    )
    return actual_decorator(view_func)