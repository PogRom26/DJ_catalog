from django.urls import path, include
from django.views.generic import RedirectView
from . import views
from .views import (
    HomeView,
    ProductListView,
    ProductDetailView,
    ContactView,
    # Теперь эти views существуют (как заглушки)
    CategoryListView,
    CategoryDetailView,
    CategoryProductsView,
    ProductCreateView,
    ProductUpdateView,
    ProductDeleteView,
    MyProductsView,
    # Views для управления кешем (заглушки)
    clear_product_cache,
    clear_similar_cache,
    cache_stats_view,
    # Представления для публикации
    publish_product,
    unpublish_product,
    change_product_status,
)

app_name = 'catalog'

urlpatterns = [
    # Основные страницы
    path('', HomeView.as_view(), name='home'),
    path('contact/', ContactView.as_view(), name='contact'),

    # Категории
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:category_id>/products/',
         CategoryProductsView.as_view(),
         name='category_products'),

    # Продукты
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/my/', MyProductsView.as_view(), name='my_products'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('products/create/', ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/update/', ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', ProductDeleteView.as_view(), name='product_delete'),

    # Управление публикацией
    path('products/<int:pk>/publish/', publish_product, name='publish_product'),
    path('products/<int:pk>/unpublish/', unpublish_product, name='unpublish_product'),
    path('products/<int:pk>/change-status/', change_product_status, name='change_product_status'),

    # Управление кешем
    path('products/<int:pk>/clear-cache/', clear_product_cache, name='clear_product_cache'),
    path('products/<int:pk>/clear-similar-cache/',
         clear_similar_cache,
         name='clear_similar_cache'),
    path('cache/stats/', cache_stats_view, name='cache_stats'),

    # Редиректы
    path('item/<int:pk>/',
         RedirectView.as_view(pattern_name='catalog:product_detail', permanent=True)),
]