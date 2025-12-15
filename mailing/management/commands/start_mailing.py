import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from mailing.models import Mailing, MailingAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Команда для запуска рассылок с инвалидацией кеша"""
    help = 'Запускает все активные рассылки, которые должны быть отправлены сейчас'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Запустить все активные рассылки, игнорируя время'
        )

    def invalidate_cache_for_mailing(self, mailing_id):
        """Инвалидация кеша для рассылки"""
        cache.delete(f'mailing_detail_{mailing_id}')
        cache.delete(f'mailing_detail_context_{mailing_id}')
        cache.delete_pattern('mailing_stats_*')
        cache.delete_pattern('api_stats_*')
        cache.delete_pattern('dashboard_stats_*')
        cache.delete_pattern('statistics_data_*')

    def handle(self, *args, **options):
        force = options.get('force', False)
        now = timezone.now()

        # Находим рассылки для отправки
        if force:
            mailings = Mailing.objects.filter(
                is_active=True,
                status__in=[Mailing.STATUS_CREATED, Mailing.STATUS_STARTED]
            )
            self.stdout.write(
                self.style.WARNING(f'Принудительный запуск {mailings.count()} рассылок')
            )
        else:
            mailings = Mailing.objects.filter(
                is_active=True,
                status__in=[Mailing.STATUS_CREATED, Mailing.STATUS_STARTED],
                start_time__lte=now,
                end_time__gte=now
            )

        total_sent = 0
        total_failed = 0

        for mailing in mailings:
            # Обновляем статус рассылки
            mailing.update_status()

            if mailing.status != Mailing.STATUS_STARTED:
                continue

            self.stdout.write(f'Обработка рассылки #{mailing.id}...')

            # Отправляем каждому клиенту
            for client in mailing.clients.filter(is_active=True):
                try:
                    send_mail(
                        subject=mailing.message.subject,
                        message=mailing.message.body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[client.email],
                        fail_silently=False,
                    )

                    MailingAttempt.objects.create(
                        mailing=mailing,
                        client=client,
                        status=MailingAttempt.STATUS_SUCCESS,
                        server_response='200 OK'
                    )

                    total_sent += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Отправлено: {client.email}')
                    )

                except Exception as e:
                    error_msg = str(e)
                    MailingAttempt.objects.create(
                        mailing=mailing,
                        client=client,
                        status=MailingAttempt.STATUS_FAILED,
                        server_response=error_msg
                    )

                    total_failed += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Ошибка для {client.email}: {error_msg}')
                    )
                    logger.error(f'Ошибка отправки: {error_msg}')

            # Обновляем следующую отправку для периодических рассылок
            if mailing.frequency != 'once':
                mailing.calculate_next_send()

            # Инвалидируем кеш после отправки
            self.invalidate_cache_for_mailing(mailing.id)

        # Итог
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(
            f'ИТОГ: Отправлено {total_sent}, Ошибок: {total_failed}'
        ))

        if total_sent == 0 and total_failed == 0:
            self.stdout.write(self.style.WARNING('Нет рассылок для отправки.'))

        # Инвалидируем общие кеши статистики
        cache.delete_pattern('api_stats_*')
        cache.delete_pattern('dashboard_stats_*')
        cache.delete_pattern('statistics_data_*')