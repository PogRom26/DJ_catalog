from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import Product
from .forms import ProductForm


class HomeView(ListView):
    """CBV для главной страницы со списком товаров - доступно всем"""
    model = Product
    template_name = 'catalog/home.html'
    context_object_name = 'products'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Skystore - Главная'
        return context


class ProductDetailView(DetailView):
    """CBV для детальной страницы товара - доступно всем"""
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'{self.object.name} - Skystore'
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    """CBV для создания нового товара - только для авторизованных"""
    model = Product
    form_class = ProductForm
    template_name = 'catalog/product_form.html'
    success_url = reverse_lazy('catalog:home')
    login_url = '/users/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание товара - Skystore'
        context['submit_text'] = 'Создать товар'
        return context


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    """CBV для редактирования товара - только для авторизованных"""
    model = Product
    form_class = ProductForm
    template_name = 'catalog/product_form.html'
    login_url = '/users/login/'

    def get_success_url(self):
        return reverse_lazy('catalog:product_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование {self.object.name} - Skystore'
        context['submit_text'] = 'Сохранить изменения'
        return context


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """CBV для удаления товара - только для авторизованных"""
    model = Product
    template_name = 'catalog/product_confirm_delete.html'
    success_url = reverse_lazy('catalog:home')
    login_url = '/users/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Удаление {self.object.name} - Skystore'
        return context


class ContactsView(TemplateView):
    """CBV для страницы контактов - доступно всем"""
    template_name = 'catalog/contacts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Контакты - Skystore'
        return context