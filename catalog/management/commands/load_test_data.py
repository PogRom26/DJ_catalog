from django.core.management.base import BaseCommand
from django.core.management import call_command
import os


class Command(BaseCommand):
    help = 'Загружает тестовые данные для каталога'

    def handle(self, *args, **options):
        self.stdout.write('Загрузка тестовых данных...')

        # Список фикстур для загрузки (в правильном порядке зависимостей)
        fixtures = [
            'categories.json',  # Сначала категории
            'users.json',  # Потом пользователи
            'groups.json',  # Потом группы
            'products.json',  # Потом продукты
        ]

        fixture_dir = 'catalog/fixtures'

        for fixture in fixtures:
            fixture_path = os.path.join(fixture_dir, fixture)
            if os.path.exists(fixture_path):
                try:
                    call_command('loaddata', fixture_path)
                    self.stdout.write(self.style.SUCCESS(f'✓ Загружено: {fixture}'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'⚠ Ошибка при загрузке {fixture}: {str(e)[:100]}...'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ Файл не найден: {fixture}'))

        # Итог
        try:
            from catalog.models import Category, Product
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Загрузка завершена!\n'
                f'   Категорий: {Category.objects.count()}\n'
                f'   Товаров: {Product.objects.count()}'
            ))
        except:
            self.stdout.write(self.style.SUCCESS('\n✅ Загрузка фикстур завершена!'))