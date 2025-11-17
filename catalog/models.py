from django.db import models

class Student(models.Model):
    first_name = models.CharField(max_length=150, verbose_name='Имя')
    last_name = models.CharField(max_length=150, verbose_name='Фамилия')

    photo = models.ImageField(upload_to='photos/', verbose_name='Фотография')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = 'студент'
        verbose_name_plural = 'студенты'
        ordering = ['last_name']
        db_table = 'custom_table_name'