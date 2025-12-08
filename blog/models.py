from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class BlogPost(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('Заголовок'))
    content = models.TextField(verbose_name=_('Содержание'))
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Автор'),
        related_name='blog_posts'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))
    is_published = models.BooleanField(default=False, verbose_name=_('Опубликовано'))
    published_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Дата публикации'))

    class Meta:
        verbose_name = _('Запись блога')
        verbose_name_plural = _('Записи блога')
        ordering = ['-created_at']
        permissions = [
            ("can_publish_blog", _("Может публиковать записи блога")),
            ("can_moderate_blog", _("Может модерировать блог")),
        ]

    def __str__(self):
        return self.title