from django.http import HttpResponse
from django.shortcuts import render

from django.shortcuts import render
from .models import Product


def home(request):
    """Контроллер для главной страницы"""
    products = Product.objects.all()

    context = {
        'products': products,
        'title': 'Skystore - Главная'
    }

    return render(request, 'catalog/home.html', context)


# def contacts(request):
#     if request.method == "POST":
#         name = request.POST.get("name")
#         message = request.POST.get("message")
#
#         return HttpResponse(f"Спасибо {name}, сообщение получено!")
#     return render(request, "catalog/contacts.html")

def contacts(request):
    """Контроллер для страницы контактов"""
    return render(request, 'catalog/contacts.html')


def product_detail(request):
    """Контроллер для отображения подробной информации о товаре"""
    return render(request, 'catalog/product_detail.html')


