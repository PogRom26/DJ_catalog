from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings
from .forms import UserRegisterForm, UserLoginForm, UserProfileForm


def register(request):
    """Регистрация нового пользователя"""
    if request.user.is_authenticated:
        messages.info(request, _('You are already logged in.'))
        return redirect('catalog:home')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['emails'].lower()
            user.save()

            # Автоматический вход после регистрации
            login(request, user)

            # Отправка приветственного письма
            try:
                send_welcome_email(user)
                messages.success(request, _('Welcome emails has been sent!'))
            except Exception as e:
                print(f"Email sending error: {e}")
                messages.warning(request, _('Registration successful, but welcome emails could not be sent.'))

            messages.success(request, _('Registration successful! Welcome to Skystore!'))
            return redirect('catalog:home')
    else:
        form = UserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


def user_login(request):
    """Авторизация пользователя"""
    if request.user.is_authenticated:
        messages.info(request, _('You are already logged in.'))
        return redirect('catalog:home')

    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username').lower()
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, _('You have successfully logged in!'))

                # Перенаправление на следующую страницу или домой
                next_page = request.GET.get('next', 'catalog:home')
                return redirect(next_page)
            else:
                messages.error(request, _('Invalid emails or password.'))
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form})


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


@login_required
def edit_profile(request):
    """Редактирование профиля пользователя"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Profile updated successfully!'))
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'users/edit_profile.html', {'form': form})


def send_welcome_email(user):
    """Отправка приветственного письма"""
    subject = _('Welcome to Skystore!')
    message = _(
        f'Hello {user.get_full_name() or user.email}!\n\n'
        f'Thank you for registering on Skystore. '
        f'We are glad to see you in our community!\n\n'
        f'Best regards,\n'
        f'Skystore Team'
    )
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list)