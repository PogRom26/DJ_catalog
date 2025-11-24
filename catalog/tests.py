from django.test import TestCase
from catalog.models import Category, Product


class CatalogTestCase(TestCase):
    fixtures = ['categories.json', 'products.json']

    def test_fixtures_loaded(self):
        """Проверка что фикстуры загрузились"""
        self.assertEqual(Category.objects.count(), 5)
        self.assertEqual(Product.objects.count(), 10)