from django.urls import path
from .views import HomeView, ProductDetailView, ContactsView

app_name = 'catalog'

urlpatterns = [
    path('home/', HomeView.as_view(), name='home'),
    path('contacts/', ContactsView.as_view(), name='contacts'),
    path('product/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
]