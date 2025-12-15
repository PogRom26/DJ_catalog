from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Client, Message, Mailing
from django.contrib.auth import get_user_model

User = get_user_model()


class ClientForm(forms.ModelForm):
    """Форма для создания/редактирования клиента"""

    class Meta:
        model = Client
        fields = ['email', 'full_name', 'comment', 'is_active']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@mail.ru'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Иванов Иван Иванович'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Дополнительная информация...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'email': 'Email адрес',
            'full_name': 'ФИО',
            'comment': 'Комментарий',
            'is_active': 'Активен',
        }


class MessageForm(forms.ModelForm):
    """Форма для создания/редактирования сообщения"""

    class Meta:
        model = Message
        fields = ['subject', 'body']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Тема письма'
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Текст письма...'
            }),
        }
        labels = {
            'subject': 'Тема письма',
            'body': 'Текст письма',
        }


class MailingForm(forms.ModelForm):
    """Форма для создания/редактирования рассылки"""
    clients = forms.ModelMultipleChoiceField(
        queryset=Client.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        label='Получатели',
        required=True
    )

    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            },
            format='%Y-%m-%dT%H:%M'
        ),
        label='Дата и время начала'
    )

    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            },
            format='%Y-%m-%dT%H:%M'
        ),
        label='Дата и время окончания'
    )

    class Meta:
        model = Mailing
        fields = ['start_time', 'end_time', 'message', 'clients', 'frequency', 'is_active']
        widgets = {
            'message': forms.Select(attrs={'class': 'form-control'}),
            'frequency': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'message': 'Сообщение',
            'frequency': 'Периодичность',
            'is_active': 'Активна',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Фильтруем клиентов и сообщения по владельцу
        if self.user:
            if not self.user.is_staff and not self.user.is_superuser:
                self.fields['clients'].queryset = Client.objects.filter(owner=self.user)
                self.fields['message'].queryset = Message.objects.filter(owner=self.user)
            else:
                self.fields['clients'].queryset = Client.objects.all()
                self.fields['message'].queryset = Message.objects.all()

        # Устанавливаем начальные значения для datetime полей
        if not self.instance.pk:
            now = timezone.now()
            self.fields['start_time'].initial = now
            self.fields['end_time'].initial = now + timezone.timedelta(days=1)

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            now = timezone.now()

            # Проверка, что дата начала не в прошлом
            if self.instance.pk is None and start_time < now:
                self.add_error('start_time', 'Дата начала не может быть в прошлом.')

            # Проверка, что дата начала раньше даты окончания
            if start_time >= end_time:
                self.add_error('end_time', 'Дата окончания должна быть позже даты начала.')

        return cleaned_data