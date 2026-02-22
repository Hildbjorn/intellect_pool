from django.db import models

class ProgrammingLanguage(models.Model):
    """
    Языки программирования
    """
    name = models.CharField('Название языка', max_length=50, unique=True)

    class Meta:
        verbose_name = 'Язык программирования'
        verbose_name_plural = 'Языки программирования'
        ordering = ['name']

    def __str__(self):
        return self.name


class DBMS(models.Model):
    """
    Системы управления базами данных
    """
    name = models.CharField('Название СУБД', max_length=50, unique=True)

    class Meta:
        verbose_name = 'СУБД'
        verbose_name_plural = 'СУБД'
        ordering = ['name']

    def __str__(self):
        return self.name


class OperatingSystem(models.Model):
    """
    Операционные системы
    """
    name = models.CharField('Название ОС', max_length=50, unique=True)

    class Meta:
        verbose_name = 'Операционная система'
        verbose_name_plural = 'Операционные системы'
        ordering = ['name']

    def __str__(self):
        return self.name