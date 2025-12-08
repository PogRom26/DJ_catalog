from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from catalog.models import Product


class Command(BaseCommand):
    help = 'Создает группы и разрешения для системы товаров'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Создание групп и разрешений...'))

        # Получаем ContentType для модели Product
        content_type = ContentType.objects.get_for_model(Product)

        # Создаем кастомные разрешения, если их нет
        custom_permissions = [
            ("can_publish_product", _("Может публиковать товары")),
            ("can_unpublish_product", _("Может отменять публикацию товаров")),
            ("can_change_publish_status", _("Может изменять статус публикации")),
            ("can_view_all_products", _("Может просматривать все товары")),
        ]

        for codename, name in custom_permissions:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                name=name,
                content_type=content_type,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создано разрешение: {name}'))

        # Создаем группу "Модератор продуктов"
        moderator_group, created = Group.objects.get_or_create(
            name='Модератор продуктов'
        )

        # Назначаем разрешения модератору
        moderator_permissions = [
            'delete_product',  # Удаление любого продукта
            'change_product',  # Редактирование любых товаров
            'view_product',  # Просмотр всех товаров
            'can_unpublish_product',  # Отмена публикации
            'can_change_publish_status',  # Изменение статуса
            'can_view_all_products',  # Просмотр всех товаров
            'can_publish_product',  # Публикация товаров
        ]

        for perm_codename in moderator_permissions:
            try:
                permission = Permission.objects.get(
                    codename=perm_codename,
                    content_type=content_type
                )
                moderator_group.permissions.add(permission)
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'Разрешение {perm_codename} не найдено'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Группа "Модератор продуктов" {"создана" if created else "обновлена"}'
        ))

        # Создаем группу "Продавец"
        seller_group, created = Group.objects.get_or_create(
            name='Продавец'
        )

        seller_permissions = [
            'add_product',  # Добавление товаров
            'change_product',  # Редактирование своих товаров
            'delete_product',  # Удаление своих товаров
            'view_product',  # Просмотр товаров
        ]

        for perm_codename in seller_permissions:
            try:
                permission = Permission.objects.get(
                    codename=perm_codename,
                    content_type=content_type
                )
                seller_group.permissions.add(permission)
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'Разрешение {perm_codename} не найдено'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Группа "Продавец" {"создана" if created else "обновлена"}'
        ))

        self.stdout.write(self.style.SUCCESS('\nГруппы и разрешения успешно настроены!'))