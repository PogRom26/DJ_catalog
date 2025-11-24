from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    return render(request, "catalog/home.html")


def contacts(request):
    if request.method == "POST":
        name = request.POST.get("name")
        message = request.POST.get("message")

        return HttpResponse(f"Спасибо {name}, сообщение получено!")
    return render(request, "catalog/contacts.html")
