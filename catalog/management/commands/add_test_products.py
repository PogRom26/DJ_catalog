from django.core.management.base import BaseCommand
from catalog.models import Category, Product


class Command(BaseCommand):
    help = 'Добавляет тестовые товары в базу данных'

    def handle(self, *args, **options):
        self.stdout.write('Добавление тестовых товаров...')

        # Создаем категории если их нет
        categories_data = [
            ('Электроника', 'Техника и гаджеты'),
            ('Одежда', 'Мужская и женская одежда'),
            ('Книги', 'Художественная литература'),
            ('Спорт', 'Спортивный инвентарь'),
            ('Мебель', 'Мебель для дома и офиса'),
        ]

        categories = {}
        for name, description in categories_data:
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            categories[name] = category
            if created:
                self.stdout.write(f'Создана категория: {name}')

        # Добавляем товары
        products_data = [
            ('iPhone 15 Pro', 'Смартфон Apple с камерой 48 МП', 89999.99, 'Электроника'),
            ('MacBook Air M2', 'Ноутбук Apple на чипе M2', 119999.00, 'Электроника'),
            ('Samsung Galaxy S23', 'Смартфон Samsung', 69999.99, 'Электроника'),
            ('Наушники Sony', 'Беспроводные наушники', 12999.50, 'Электроника'),
            ('Футболка хлопковая', 'Комфортная футболка', 1999.99, 'Одежда'),
            ('Джинсы классические', 'Классические джинсы', 4599.99, 'Одежда'),
            ('Куртка зимняя', 'Теплая куртка', 8999.99, 'Одежда'),
            ('Кроссовки спортивные', 'Удобные кроссовки', 5999.50, 'Одежда'),
            ('Война и мир', 'Роман Льва Толстого', 1500.00, 'Книги'),
            ('Python для начинающих', 'Учебник по Python', 2500.00, 'Книги'),
            ('Гарри Поттер', 'Фэнтези роман', 1800.00, 'Книги'),
            ('Детектив Агаты Кристи', 'Классический детектив', 1200.00, 'Книги'),
        ]

        created_count = 0
        for name, description, price, category_name in products_data:
            category = categories.get(category_name)
            if category and not Product.objects.filter(name=name).exists():
                Product.objects.create(
                    name=name,
                    description=description,
                    price=price,
                    category=category
                )
                created_count += 1

        total_products = Product.objects.count()
        total_categories = Category.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Готово!\n'
            f'Всего категорий: {total_categories}\n'
            f'Всего товаров: {total_products}\n'
            f'Добавлено новых: {created_count}'
        ))