from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('home/', views.home, name='home'),
    path('contacts/', views.contacts, name='contacts'),  # Добавляем контакты, если нужно
    path('product/<int:pk>/', views.product_detail, name='product_detail'),  # Исправляем этот путь
]