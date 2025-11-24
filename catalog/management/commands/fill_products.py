from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Заполняет базу тестовыми данными с очисткой старых"

    def handle(self, *args, **options):
        self.stdout.write("Запуск команды fill_products...")

        # Импортируем модели
        try:
            from catalog.models import Category, Product

            self.stdout.write("Модели успешно импортированы!")

            # Получаем текущие данные
            cat_count = Category.objects.count()
            prod_count = Product.objects.count()
            self.stdout.write(f"В базе: {cat_count} категорий, {prod_count} продуктов")

            # Очищаем базу данных
            self.stdout.write("Очистка базы данных...")
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write("Старые данные удалены!")

            # Создаем тестовые категории
            self.stdout.write("Создание категорий...")
            categories_data = [
                ("Электроника", "Техника и гаджеты"),
                ("Одежда", "Мужская и женская одежда"),
                ("Книги", "Художественная литература"),
            ]

            categories = {}
            for name, description in categories_data:
                category = Category.objects.create(name=name, description=description)
                categories[name] = category
                self.stdout.write(f"Создана категория: {name}")

            # Создаем тестовые продукты
            self.stdout.write("Создание продуктов...")
            products_data = [
                ("iPhone 15", "Смартфон Apple", categories["Электроника"], 89999),
                ("MacBook Air", "Ноутбук Apple", categories["Электроника"], 119999),
                ("Футболка", "Хлопковая футболка", categories["Одежда"], 1999),
                ("Джинсы", "Классические джинсы", categories["Одежда"], 4599),
                ("Война и мир", "Роман Толстого", categories["Книги"], 1500),
                ("Python книги", "Учебник по Python", categories["Книги"], 2500),
            ]

            for name, description, category, price in products_data:
                Product.objects.create(
                    name=name, description=description, category=category, price=price
                )
                self.stdout.write(f"Создан продукт: {name} - {price} руб.")

            # Финальная статистика
            new_cat_count = Category.objects.count()
            new_prod_count = Product.objects.count()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Готово! Создано: {new_cat_count} категорий, {new_prod_count} продуктов"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
