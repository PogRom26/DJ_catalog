from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _


def register(request):
    """Простая регистрация (позже добавим)"""
    return render(request, 'users/register.html')


def user_login(request):
    """Простой вход (позже добавим)"""
    return render(request, 'users/login.html')


@login_required
def user_logout(request):
    """Выход пользователя"""
    logout(request)
    messages.info(request, _('You have successfully logged out.'))
    return redirect('catalog:home')


@login_required
def profile(request):
    """Профиль пользователя"""
    return render(request, 'users/profile.html', {'user': request.user})