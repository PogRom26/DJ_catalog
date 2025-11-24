from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')  # Поля для отображения в списке
    list_display_links = ('id', 'name')  # Поля-ссылки для перехода к редактированию
    search_fields = ('name', 'description')  # Поля для поиска


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'category')  # Поля для отображения в списке
    list_display_links = ('id', 'name')  # Поля-ссылки для перехода к редактированию
    list_filter = ('category',)  # Фильтрация по категории
    search_fields = ('name', 'description')  # Поля для поиска

    # Дополнительные настройки для удобства
    list_per_page = 20  # Количество элементов на странице
    list_select_related = ('category',)  # Оптимизация запросов к БД

    # Поля только для чтения
    readonly_fields = ('created_at', 'updated_at')

    # Группировка полей в форме редактирования
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'category', 'price')
        }),
        ('Изображение', {
            'fields': ('image',),
            'classes': ('collapse',)  # Сворачиваемая секция
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )