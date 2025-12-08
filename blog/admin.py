from django.contrib import admin
from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_published', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('title', 'content', 'author')}),
        ('Публикация', {'fields': ('is_published', 'published_at')}),
        ('Даты', {'fields': ('created_at', 'updated_at')}),
    )