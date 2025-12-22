import time

from django.core.management.base import BaseCommand
from django_redis import get_redis_connection


class Command(BaseCommand):
    help = 'Проверяет подключение к Redis'

    def handle(self, *args, **options):
        self.stdout.write('Проверка подключения к Redis...')

        try:
            # Проверяем подключение к default кешу
            cache = get_redis_connection('default')
            cache.ping()
            self.stdout.write(self.style.SUCCESS('Подключение к Redis успешно!'))

            # Тестируем запись и чтение
            test_key = 'test_connection'
            test_value = f'test_{time.time()}'

            cache.set(test_key, test_value, ex=10)  # ex=10 секунд
            retrieved_value = cache.get(test_key)

            if retrieved_value.decode() == test_value:
                self.stdout.write(self.style.SUCCESS('Запись и чтение данных работают'))
            else:
                self.stdout.write(self.style.ERROR('Ошибка при чтении данных'))

            # Проверяем другие кеши
            for alias in ['default', 'session', 'database']:
                try:
                    conn = get_redis_connection(alias)
                    conn.ping()
                    self.stdout.write(self.style.SUCCESS(f'Кеш "{alias}" работает'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Кеш "{alias}" недоступен: {e}'))

            # Статистика
            info = cache.info()
            self.stdout.write(f"\n Статистика Redis:")
            self.stdout.write(f"   Версия: {info.get('redis_version', 'N/A')}")
            self.stdout.write(f"   Подключений: {info.get('connected_clients', 'N/A')}")
            self.stdout.write(f"   Использовано памяти: {info.get('used_memory_human', 'N/A')}")
            self.stdout.write(f"   Ключей в базе: {info.get('db1', {}).get('keys', 'N/A')}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f' Ошибка подключения к Redis: {e}'))
            self.stdout.write('\nВозможные решения:')
            self.stdout.write('1. Убедитесь, что Redis запущен: `redis-cli ping`')
            self.stdout.write('2. Проверьте настройки в settings.py')
            self.stdout.write('3. Убедитесь, что порт 6379 доступен')