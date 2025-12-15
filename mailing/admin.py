from django.contrib import admin
from .models import Client, Message, Mailing, MailingAttempt

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'owner', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'owner')
    search_fields = ('email', 'full_name')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'owner', 'created_at')
    list_filter = ('created_at', 'owner')
    search_fields = ('subject', 'body')

@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'message', 'owner', 'is_active', 'start_time')
    list_filter = ('status', 'is_active', 'frequency', 'owner')
    filter_horizontal = ('clients',)

@admin.register(MailingAttempt)
class MailingAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'mailing', 'client', 'status', 'attempt_time')
    list_filter = ('status', 'attempt_time')
    readonly_fields = ('attempt_time',)