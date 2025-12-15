from django.urls import path
from . import views

app_name = 'mailing'

urlpatterns = [
    # Главная страница
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Клиенты
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    path('clients/create/', views.ClientCreateView.as_view(), name='client_create'),
    path('clients/<int:pk>/update/', views.ClientUpdateView.as_view(), name='client_update'),
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),

    # Сообщения
    path('messages/', views.MessageListView.as_view(), name='message_list'),
    path('messages/create/', views.MessageCreateView.as_view(), name='message_create'),
    path('messages/<int:pk>/update/', views.MessageUpdateView.as_view(), name='message_update'),
    path('messages/<int:pk>/delete/', views.MessageDeleteView.as_view(), name='message_delete'),

    # Рассылки
    path('mailings/', views.MailingListView.as_view(), name='mailing_list'),
    path('mailings/create/', views.MailingCreateView.as_view(), name='mailing_create'),
    path('mailings/<int:pk>/', views.MailingDetailView.as_view(), name='mailing_detail'),
    path('mailings/<int:pk>/update/', views.MailingUpdateView.as_view(), name='mailing_update'),
    path('mailings/<int:pk>/delete/', views.MailingDeleteView.as_view(), name='mailing_delete'),
    path('mailings/<int:pk>/start/', views.MailingStartView.as_view(), name='mailing_start'),

    # Статистика
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),

    # API
    path('api/stats/', views.mailing_stats_api, name='api_stats'),

    # Менеджерские урлы
    path('manager/mailings/', views.AllMailingsView.as_view(), name='manager_all_mailings'),
    path('manager/clients/', views.AllClientsView.as_view(), name='manager_all_clients'),
    path('manager/mailings/<int:pk>/toggle/', views.MailingToggleView.as_view(), name='manager_mailing_toggle'),
]