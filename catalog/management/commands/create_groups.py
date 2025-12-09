from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _


class Command(BaseCommand):
    help = 'Создает группы и разрешения для системы товаров'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Создание групп и разрешений...'))

        # Получаем ContentType для модели Product из catalog
        try:
            from catalog.models import Product
            product_content_type = ContentType.objects.get_for_model(Product)
            self.stdout.write(self.style.SUCCESS('Модель Product найдена в catalog.models'))
        except ImportError:
            self.stdout.write(self.style.ERROR('Не удалось найти модель Product в catalog.models!'))
            return
        except ContentType.DoesNotExist:
            self.stdout.write(self.style.ERROR('ContentType для Product не найден!'))
            return

        # Создаем кастомные разрешения для продуктов, если их нет
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
                content_type=product_content_type,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создано разрешение: {name}'))

        # ==============================================
        # Группа 1: Модератор продуктов
        # ==============================================
        moderator_group, created = Group.objects.get_or_create(
            name='Модератор продуктов'
        )

        # Назначаем разрешения модератору
        moderator_permissions = [
            'delete_product',  # Удаление любого продукта
            'change_product',  # Редактирование любых товаров
            'view_product',  # Просмотр всех товаров
            'can_unpublish_product',  # Отмена публикации (ТРЕБОВАНИЕ ЗАДАНИЯ)
            'can_change_publish_status',  # Изменение статуса
            'can_view_all_products',  # Просмотр всех товаров
            'can_publish_product',  # Публикация товаров
        ]

        for perm_codename in moderator_permissions:
            try:
                permission = Permission.objects.get(
                    codename=perm_codename,
                    content_type=product_content_type
                )
                moderator_group.permissions.add(permission)
                self.stdout.write(self.style.SUCCESS(f'Добавлено право модератору: {perm_codename}'))
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'Разрешение {perm_codename} не найдено'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Группа "Модератор продуктов" {"создана" if created else "обновлена"}'
        ))

        # ==============================================
        # Группа 2: Продавец (владелец товаров)
        # ==============================================
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
                    content_type=product_content_type
                )
                seller_group.permissions.add(permission)
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'Разрешение {perm_codename} не найдено'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Группа "Продавец" {"создана" if created else "обновлена"}'
        ))

        # ==============================================
        # ДОПОЛНИТЕЛЬНОЕ ЗАДАНИЕ: Группа Контент-менеджер
        # ==============================================
        try:
            # Пытаемся найти модель BlogPost в приложении blog
            blog_content_type = ContentType.objects.get(app_label='blog', model='blogpost')
            blog_permissions = Permission.objects.filter(content_type=blog_content_type)

            content_manager_group, created = Group.objects.get_or_create(
                name='Контент-менеджер'
            )

            # Добавляем ВСЕ разрешения для модели BlogPost
            for perm in blog_permissions:
                content_manager_group.permissions.add(perm)
                self.stdout.write(self.style.SUCCESS(
                    f'Добавлено право контент-менеджеру: {perm.codename}'
                ))

            self.stdout.write(self.style.SUCCESS(
                f'Группа "Контент-менеджер" {"создана" if created else "обновлена"}'
            ))

        except ContentType.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                'Модель BlogPost не найдена. Для создания группы "Контент-менеджер" '
                'создайте приложение blog с моделью BlogPost.'
            ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f'Ошибка при создании группы контент-менеджера: {e}'
            ))

        # ==============================================
        # Сводка по созданным группам
        # ==============================================
        self.stdout.write(self.style.MIGRATE_HEADING('\nСводка по созданным группам:'))

        for group in Group.objects.all():
            perm_count = group.permissions.count()
            self.stdout.write(f"  • {group.name}: {perm_count} разрешений")

            # Детали для группы "Модератор продуктов"
            if group.name == 'Модератор продуктов':
                has_unpublish = group.permissions.filter(codename='can_unpublish_product').exists()
                has_delete = group.permissions.filter(codename='delete_product').exists()
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ Право can_unpublish_product: {"ДА" if has_unpublish else "НЕТ"}'
                ))
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ Право delete_product: {"ДА" if has_delete else "НЕТ"}'
                ))

        self.stdout.write(self.style.SUCCESS('\nГруппы и разрешения успешно настроены!'))