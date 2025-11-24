from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Простая команда для тестирования'

    def handle(self, *args, **options):
        self.stdout.write('Простая команда запущена!')

        # Попробуем импортировать модели здесь
        try:
            from catalog.models import Category, Product
            self.stdout.write('Модели успешно импортированы!')

            # Простой счет
            cat_count = Category.objects.count()
            prod_count = Product.objects.count()
            self.stdout.write(f'В базе: {cat_count} категорий, {prod_count} продуктов')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка: {e}'))