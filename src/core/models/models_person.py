from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from common.utils import TextUtils


class Person(models.Model):
    """
    Физическое лицо (руководитель предприятия)
    С двусторонней синхронизацией полей ФИО
    """
    ceo_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='ID руководителя'
    )
    ceo = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='ФИО полностью',
        help_text='Фамилия Имя Отчество (заполняется автоматически или вручную)',
        blank=True,
        null=True
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name='Фамилия',
        db_index=True,
        blank=True,
        null=True
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name='Имя',
        db_index=True,
        blank=True,
        null=True
    )
    middle_name = models.CharField(
        max_length=100,
        verbose_name='Отчество',
        blank=True,
        null=True
    )
    slug = models.SlugField(
        max_length=220,
        unique=True,
        verbose_name='URL-идентификатор',
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Руководитель'
        verbose_name_plural = 'Руководители'
        ordering = ['last_name', 'first_name', 'middle_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['ceo']),
        ]

    def __str__(self):
        return self.get_full_name()

    def clean(self):
        """Валидация данных"""
        super().clean()
        
        # Проверяем, что хотя бы одна группа полей заполнена
        if not self.ceo and not (self.last_name or self.first_name):
            raise ValidationError(
                'Необходимо заполнить либо поле "ФИО полностью", '
                'либо поля "Фамилия" и "Имя"'
            )

    def _parse_full_name(self):
        """Разбирает полное ФИО на составные части"""
        if not self.ceo:
            return
        
        # Убираем лишние пробелы
        full_name = ' '.join(self.ceo.strip().split())
        parts = full_name.split()
        
        if len(parts) >= 1:
            self.last_name = parts[0]
        if len(parts) >= 2:
            self.first_name = parts[1]
        if len(parts) >= 3:
            # Объединяем остаток в отчество (на случай, если отчество составное)
            self.middle_name = ' '.join(parts[2:])
        else:
            self.middle_name = None

    def _build_full_name(self):
        """Собирает полное ФИО из составных частей"""
        parts = []
        if self.last_name:
            parts.append(self.last_name.strip())
        if self.first_name:
            parts.append(self.first_name.strip())
        if self.middle_name:
            parts.append(self.middle_name.strip())
        
        if parts:
            self.ceo = ' '.join(parts)
        else:
            self.ceo = None

    def save(self, *args, **kwargs):
        """
        Переопределенный save с двусторонней синхронизацией:
        1. Если есть ceo, но нет составных частей - разбираем ceo
        2. Если есть составные части, но нет ceo - собираем ceo
        3. Если есть и то и другое - проверяем соответствие
        4. Если заполнены оба набора, но они не соответствуют друг другу - приоритет у составных частей
        """
        # Очищаем строки от лишних пробелов
        if self.ceo:
            self.ceo = ' '.join(self.ceo.strip().split())
        if self.last_name:
            self.last_name = self.last_name.strip()
        if self.first_name:
            self.first_name = self.first_name.strip()
        if self.middle_name:
            self.middle_name = self.middle_name.strip()

        # Случай 1: Заполнено только полное ФИО
        if self.ceo and not (self.last_name or self.first_name):
            self._parse_full_name()
        
        # Случай 2: Заполнены только составные части
        elif (self.last_name or self.first_name) and not self.ceo:
            self._build_full_name()
        
        # Случай 3: Заполнены оба набора - проверяем соответствие
        elif self.ceo and (self.last_name or self.first_name):
            # Временно собираем ФИО из составных частей для сравнения
            temp_parts = []
            if self.last_name:
                temp_parts.append(self.last_name)
            if self.first_name:
                temp_parts.append(self.first_name)
            if self.middle_name:
                temp_parts.append(self.middle_name)
            
            constructed_ceo = ' '.join(temp_parts) if temp_parts else None
            
            # Если собранное ФИО отличается от сохраненного,
            # приоритет у составных частей
            if constructed_ceo and constructed_ceo != self.ceo:
                self.ceo = constructed_ceo

        # Генерируем slug, если его нет
        if not self.slug:
            # Для slug используем составные части или разбираем ceo
            if self.last_name and self.first_name:
                base = f"{self.last_name}-{self.first_name}"
                if self.middle_name:
                    base += f"-{self.middle_name}"
            elif self.ceo:
                # Разбираем ceo для slug
                temp_parts = self.ceo.split()
                base = '-'.join(temp_parts)
            else:
                base = f"person-{self.ceo_id}"
            
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:220]

        super().save(*args, **kwargs)

    def get_short_name(self):
        """Возвращает сокращенное ФИО (Иванов И.И.)"""
        if self.last_name:
            short = self.last_name
            if self.first_name:
                short += f" {self.first_name[0]}."
            if self.middle_name:
                short += f" {self.middle_name[0]}."
            return short
        elif self.ceo:
            # Если нет составных частей, но есть ceo - пробуем разобрать на лету
            parts = self.ceo.split()
            if len(parts) >= 1:
                short = parts[0]
                if len(parts) >= 2:
                    short += f" {parts[1][0]}."
                if len(parts) >= 3:
                    short += f" {parts[2][0]}."
                return short
        return self.ceo or ""

    def get_full_name(self):
        """Возвращает полное ФИО"""
        if self.ceo:
            return self.ceo
        return self._build_full_name() or ""

    def get_initials(self):
        """Возвращает инициалы (И.И. Иванов)"""
        initials = []
        if self.first_name:
            initials.append(self.first_name[0].upper())
        if self.middle_name:
            initials.append(self.middle_name[0].upper())
        
        if initials and self.last_name:
            return f"{'.'.join(initials)}. {self.last_name}"
        elif self.ceo:
            parts = self.ceo.split()
            if len(parts) >= 3:
                return f"{parts[1][0]}.{parts[2][0]}. {parts[0]}"
            elif len(parts) == 2:
                return f"{parts[1][0]}. {parts[0]}"
            return parts[0]
        return ""