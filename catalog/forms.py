from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Product, Category


class ProductForm(forms.ModelForm):
    """Форма для создания и редактирования товара"""

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'image',
            'category', 'price', 'publish_status',
            'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'publish_status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': _('Название товара'),
            'description': _('Описание'),
            'image': _('Изображение'),
            'category': _('Категория'),
            'price': _('Цена (руб.)'),
            'publish_status': _('Статус публикации'),
            'is_active': _('Активный'),
        }
        help_texts = {
            'publish_status': _('Выберите статус публикации товара'),
            'price': _('Укажите цену в рублях'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Настройка доступных статусов в зависимости от прав пользователя
        if self.user:
            if not self.user.has_perm('products.can_publish_product'):
                # Обычные пользователи могут выбирать только черновик или отправку на проверку
                self.fields['publish_status'].choices = [
                    (Product.PublishStatus.DRAFT, Product.PublishStatus.DRAFT.label),
                    (Product.PublishStatus.PENDING_REVIEW, Product.PublishStatus.PENDING_REVIEW.label),
                ]

            # Если пользователь не может изменять статус, делаем поле readonly
            if not self.user.has_perm('products.can_change_publish_status'):
                self.fields['publish_status'].widget.attrs['readonly'] = True
                self.fields['publish_status'].widget.attrs['disabled'] = True

            # Если у пользователя нет прав на просмотр всех товаров,
            # ограничиваем выбор категорий активными
            if not self.user.has_perm('products.can_view_all_products'):
                self.fields['category'].queryset = Category.objects.all()

        # Настройка класса Bootstrap для всех полей
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

    def clean_price(self):
        """Валидация цены"""
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError(_('Цена должна быть больше нуля'))
        return price

    def clean_name(self):
        """Валидация названия"""
        name = self.cleaned_data.get('name')
        if name and len(name.strip()) < 3:
            raise forms.ValidationError(_('Название должно содержать минимум 3 символа'))
        return name.strip()

    def save(self, commit=True):
        """Сохранение формы с автоматическим назначением владельца"""
        instance = super().save(commit=False)

        # Если это новый товар и у него нет владельца, назначаем текущего пользователя
        if not instance.pk and self.user and not instance.owner:
            instance.owner = self.user

        if commit:
            instance.save()

        return instance


class ProductStatusForm(forms.ModelForm):
    """Форма для изменения статуса товара (для модераторов)"""

    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': _('Причина изменения статуса (необязательно)')
        }),
        label=_('Комментарий'),
        help_text=_('Укажите причину изменения статуса')
    )

    class Meta:
        model = Product
        fields = ['publish_status']

        widgets = {
            'publish_status': forms.Select(attrs={
                'class': 'form-control',
            }),
        }
        labels = {
            'publish_status': _('Новый статус'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем все статусы для модераторов
        self.fields['publish_status'].choices = Product.PublishStatus.choices

        # Убираем текущий статус из выбора
        current_status = self.instance.publish_status if self.instance else None
        if current_status:
            choices = list(self.fields['publish_status'].choices)
            self.fields['publish_status'].choices = [
                choice for choice in choices if choice[0] != current_status
            ]
            # Добавляем текущий статус с пометкой "текущий"
            self.fields['publish_status'].choices.insert(0,
                                                         (current_status,
                                                          f"{dict(Product.PublishStatus.choices)[current_status]} (текущий)")
                                                         )

    def save(self, commit=True):
        """Сохранение формы с добавлением комментария в описание"""
        instance = super().save(commit=False)

        # Добавляем комментарий к описанию, если он указан
        comment = self.cleaned_data.get('comment')
        if comment:
            timestamp = instance.updated_at.strftime("%d.%m.%Y %H:%M")
            comment_text = f"\n\n---\nИзменение статуса {timestamp}:\n{comment}"
            instance.description = (instance.description or '') + comment_text

        if commit:
            instance.save()

        return instance


class ProductFilterForm(forms.Form):
    """Форма фильтрации товаров"""
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Поиск по названию или описанию...')
        }),
        label=_('Поиск')
    )

    status = forms.ChoiceField(
        required=False,
        choices=[('', _('Все статусы'))] + Product.PublishStatus.choices,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Статус')
    )

    category = forms.ModelChoiceField(
        required=False,
        queryset=Category.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Категория'),
        empty_label=_('Все категории')
    )

    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Мин. цена')
        }),
        label=_('Цена от'),
        min_value=0,
        decimal_places=2
    )

    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Макс. цена')
        }),
        label=_('Цена до'),
        min_value=0,
        decimal_places=2
    )

    def clean(self):
        """Валидация ценового диапазона"""
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')

        if min_price and max_price and min_price > max_price:
            self.add_error('max_price',
                           _('Максимальная цена должна быть больше или равна минимальной'))

        return cleaned_data