from django.contrib import admin
from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_published', 'created_at')  # Убрали 'status'
    list_filter = ('is_published', 'created_at')  # Убрали 'status'
    search_fields = ('title', 'content', 'author__username')
    readonly_fields = ('created_at', 'updated_at')  # Убрали 'published_at'

    fieldsets = (
        (None, {'fields': ('title', 'content', 'author')}),
        ('Публикация', {'fields': ('is_published',)}),  # Убрали 'status', 'published_at'
        ('Даты', {'fields': ('created_at', 'updated_at')}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Контент-менеджеры видят все записи
        if request.user.groups.filter(name='Контент-менеджер').exists():
            return qs
        # Обычные пользователи видят только свои записи
        return qs.filter(author=request.user)