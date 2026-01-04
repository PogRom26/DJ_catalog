import os
from django.core.management import call_command
from django.core.management.base import BaseCommand
from catalog.models import Product, Category


class Command(BaseCommand):
    help = 'Загружает фикстуры с товарами и категориями'

    def handle(self, *args, **options):
        self.stdout.write('Загрузка фикстур...')

        # Пути к фикстурам
        fixtures_dir = 'catalog/fixtures'
        possible_fixtures = [
            'catalog_data.json',
            'categories.json',
            'products.json',
            'catalog.json'
        ]

        # Ищем существующие фикстуры
        available_fixtures = []
        for fixture in possible_fixtures:
            fixture_path = os.path.join(fixtures_dir, fixture)
            if os.path.exists(fixture_path):
                available_fixtures.append(fixture)

        if not available_fixtures:
            self.stdout.write(self.style.WARNING('Фикстуры не найдены. Создаем тестовые данные...'))
            self._create_test_data()
            return

        # Загружаем найденные фикстуры
        for fixture in available_fixtures:
            try:
                call_command('loaddata', fixture)
                self.stdout.write(self.style.SUCCESS(f'Загружено: {fixture}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Ошибка при загрузке {fixture}: {e}'))

        # Выводим статистику
        categories_count = Category.objects.count()
        products_count = Product.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f'Загрузка завершена! Категорий: {categories_count}, Товаров: {products_count}'
        ))

    def _create_test_data(self):
        """Создание тестовых данных если фикстур нет"""
        self.stdout.write('Создание тестовых категорий...')

        # Создаем категории
        categories = [
            ('Электроника', 'Смартфоны, ноутбуки, планшеты'),
            ('Одежда', 'Мужская и женская одежда'),
            ('Книги', 'Художественная литература'),
            ('Спорт', 'Спортивный инвентарь'),
            ('Мебель', 'Мебель для дома и офиса'),
        ]

        created_categories = []
        for name, description in categories:
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            created_categories.append(category)
            if created:
                self.stdout.write(f'  Создана категория: {name}')

        self.stdout.write('Создание тестовых товаров...')

        # Создаем товары
        products_data = [
            ('iPhone 15 Pro', 'Смартфон Apple с камерой 48 МП', 89999.99, 'Электроника'),
            ('MacBook Air M2', 'Ноутбук Apple на чипе M2', 119999.00, 'Электроника'),
            ('Футболка хлопковая', 'Комфортная футболка из 100% хлопка', 1999.99, 'Одежда'),
            ('Джинсы классические', 'Классические джинсы синего цвета', 4599.99, 'Одежда'),
            ('Война и мир', 'Роман Льва Толстого в твердом переплете', 1500.00, 'Книги'),
            ('Python для начинающих', 'Учебник по программированию на Python', 2500.00, 'Книги'),
            ('Беговая дорожка', 'Электрическая беговая дорожка для дома', 34999.50, 'Спорт'),
            ('Гантели 10 кг', 'Набор разборных гантелей', 2999.00, 'Спорт'),
            ('Офисное кресло', 'Эргономичное кресло для работы', 12500.00, 'Мебель'),
            ('Компьютерный стол', 'Стол для компьютера с полкой', 8900.00, 'Мебель'),
        ]

        created_count = 0
        for name, description, price, category_name in products_data:
            # Находим категорию
            category = next((cat for cat in created_categories if cat.name == category_name), None)

            if category:
                product, created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        'description': description,
                        'price': price,
                        'category': category
                    }
                )
                if created:
                    created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Создано тестовых товаров: {created_count}'
        ))