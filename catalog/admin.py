from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")  # Поля для отображения в списке
    list_display_links = ("id", "name")  # Поля-ссылки для перехода к редактированию
    search_fields = ("name", "description")  # Поля для поиска


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'category', 'view_product_link')
    list_display_links = ('id', 'name')
    list_filter = ('category',)
    search_fields = ('name', 'description')

    def view_product_link(self, obj):
        url = reverse('catalog:product_detail', args=[obj.pk])
        return format_html('<a href="{}">Посмотреть</a>', url)

    view_product_link.short_description = 'Ссылка на страницу'


    # Дополнительные настройки для удобства
    list_per_page = 20  # Количество элементов на странице
    list_select_related = ("category",)  # Оптимизация запросов к БД

    # Поля только для чтения
    readonly_fields = ("created_at", "updated_at")

    # Группировка полей в форме редактирования
    fieldsets = (
        (
            "Основная информация",
            {"fields": ("name", "description", "category", "price")},
        ),
        (
            "Изображение",
            {"fields": ("image",), "classes": ("collapse",)},  # Сворачиваемая секция
        ),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
