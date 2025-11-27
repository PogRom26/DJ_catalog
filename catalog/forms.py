from django import forms
from django.core.exceptions import ValidationError
from .models import Product


class ProductForm(forms.ModelForm):
    """Форма для создания и редактирования продуктов с валидацией"""

    class Meta:
        model = Product
        fields = ['name', 'description', 'image', 'category', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название товара'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Введите описание товара'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(
                attrs={'class': 'form-control', 'placeholder': 'Введите цену', 'min': '0', 'step': '0.01'}),
        }
        labels = {
            'name': 'Название товара',
            'description': 'Описание товара',
            'image': 'Изображение товара',
            'category': 'Категория',
            'price': 'Цена товара',
        }
        help_texts = {
            'price': 'Цена должна быть положительным числом',
        }

    # Список запрещенных слов
    FORBIDDEN_WORDS = [
        'казино', 'криптовалюта', 'крипта', 'биржа',
        'дешево', 'бесплатно', 'обман', 'полиция', 'радар'
    ]

    def clean_name(self):
        """Валидация названия продукта"""
        name = self.cleaned_data['name'].lower()

        for word in self.FORBIDDEN_WORDS:
            if word in name:
                raise ValidationError(
                    f'Название содержит запрещенное слово: "{word}"'
                )

        return self.cleaned_data['name']

    def clean_description(self):
        """Валидация описания продукта"""
        description = self.cleaned_data.get('description', '').lower()

        if description:  # Проверяем только если описание не пустое
            for word in self.FORBIDDEN_WORDS:
                if word in description:
                    raise ValidationError(
                        f'Описание содержит запрещенное слово: "{word}"'
                    )

        return self.cleaned_data['description']

    def clean_price(self):
        """Валидация цены продукта - проверка на отрицательные и нулевые значения"""
        price = self.cleaned_data.get('price')

        if price is None:
            raise ValidationError('Поле цены обязательно для заполнения.')

        if price < 0:
            raise ValidationError(
                'Цена не может быть отрицательной. Пожалуйста, введите положительное значение.'
            )

        if price == 0:
            raise ValidationError(
                'Цена не может быть нулевой. Пожалуйста, введите положительное значение.'
            )

        return price