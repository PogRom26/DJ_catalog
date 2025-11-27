from django import forms
from django.core.exceptions import ValidationError
from .models import Product, Category


class ProductForm(forms.ModelForm):
    """Форма для создания и редактирования продуктов с валидацией"""

    class Meta:
        model = Product
        fields = ['name', 'description', 'image', 'category', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Введите название товара'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Введите описание товара'}),
            'image': forms.FileInput(),
            'category': forms.Select(),
            'price': forms.NumberInput(attrs={'placeholder': 'Введите цену', 'min': '0', 'step': '0.01'}),
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

    def __init__(self, *args, **kwargs):
        """Инициализация формы с добавлением CSS классов"""
        super().__init__(*args, **kwargs)
        self._apply_styling()

    def _apply_styling(self):
        """Применение стилей ко всем полям формы"""
        # Базовые классы для всех полей
        base_classes = 'form-control'

        for field_name, field in self.fields.items():
            # Добавляем базовые классы
            if 'class' in field.widget.attrs:
                field.widget.attrs['class'] += f' {base_classes}'
            else:
                field.widget.attrs['class'] = base_classes

            # Специфичные стили для разных типов полей
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({
                    'class': f'{field.widget.attrs.get("class", "")} form-control-lg',
                })
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({
                    'class': f'{field.widget.attrs.get("class", "")} form-textarea-custom',
                })
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': f'{field.widget.attrs.get("class", "")} form-select',
                })
            elif isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({
                    'class': f'{field.widget.attrs.get("class", "")} form-price-input',
                })
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({
                    'class': f'{field.widget.attrs.get("class", "")} form-file-input',
                })

    def clean_name(self):
        """Валидация названия продукта"""
        name = self.cleaned_data['name']

        if not name:
            raise ValidationError('Название товара не может быть пустым.')

        name_lower = name.lower()
        for word in self.FORBIDDEN_WORDS:
            if word in name_lower:
                raise ValidationError(
                    f'Название содержит запрещенное слово: "{word}"'
                )

        return name

    def clean_description(self):
        """Валидация описания продукта"""
        description = self.cleaned_data.get('description', '')

        if description:
            description_lower = description.lower()
            for word in self.FORBIDDEN_WORDS:
                if word in description_lower:
                    raise ValidationError(
                        f'Описание содержит запрещенное слово: "{word}"'
                    )

        return description

    def clean_price(self):
        """Валидация цены продукта - проверка на отрицательные значения"""
        price = self.cleaned_data.get('price')

        if price is not None and price < 0:
            raise ValidationError(
                'Цена не может быть отрицательной. Пожалуйста, введите положительное значение.'
            )

        return price