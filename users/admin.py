from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from .forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Админ-панель для кастомной модели пользователя"""

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = ('emails', 'username', 'first_name', 'last_name', 'phone', 'country', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'country')
    search_fields = ('emails', 'username', 'first_name', 'last_name', 'phone')

    fieldsets = (
        (None, {'fields': ('emails', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone', 'country', 'avatar')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('emails', 'username', 'password1', 'password2',
                       'first_name', 'last_name', 'phone', 'country',
                       'avatar', 'is_active', 'is_staff')}
         ),
    )

    ordering = ('emails',)