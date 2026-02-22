import re

from django.db import models
from django.utils.text import slugify
from core.models.models_geo import City
from common.utils import TextUtils


class FOIVType(models.Model):
    """
    Тип федерального органа исполнительной власти
    (Министерство, Служба, Агентство)
    """
    foiv_type_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID типа ФОИВ'
    )
    foiv_type = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Тип ФОИВ'
    )
    foiv_type_short = models.CharField(
        max_length=20,
        verbose_name='Краткое обозначение типа',
        help_text='Министерство, Служба, Агентство'
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
        verbose_name = 'Тип ФОИВ'
        verbose_name_plural = 'Типы ФОИВ'
        ordering = ['foiv_type_id']

    def __str__(self):
        return self.foiv_type


class FOIV(models.Model):
    """
    Федеральный орган исполнительной власти (ФОИВ)
    """
    foiv_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='ID ФОИВ'
    )
    
    # Порядковый номер в классификации
    sequence_number = models.PositiveSmallIntegerField(
        verbose_name='Порядковый номер',
        help_text='Номер в таблице ФОИВ'
    )
    
    # Коды и идентификаторы
    okogu_code = models.CharField(
        max_length=20,
        verbose_name='Код ОКОГУ',
        help_text='Буквенный код по классификатору ОКОГУ',
        db_index=True
    )
    
    # Названия
    short_name = models.CharField(
        max_length=200,
        verbose_name='Краткое наименование',
        help_text='Краткое название как в таблице (Минпромторг России)',
        db_index=True
    )
    full_name = models.TextField(
        verbose_name='Полное наименование',
        help_text='Полное официальное наименование'
    )
    name_for_sort = models.CharField(
        max_length=200,
        verbose_name='Наименование для сортировки',
        help_text='Название без кавычек и служебных слов для корректной сортировки',
        blank=True,
        null=True
    )
    
    # URL-идентификаторы
    slug = models.SlugField(
        max_length=220,
        unique=True,
        verbose_name='URL-идентификатор',
        blank=True,
        help_text='Идентификатор для URL (из столбца slug таблицы)'
    )
    
    # Тип ФОИВ
    foiv_type = models.ForeignKey(
        FOIVType,
        on_delete=models.PROTECT,
        related_name='foivs',
        verbose_name='Тип ФОИВ',
        db_column='foiv_type_id',
        null=True,
        blank=True
    )
    
    # Руководство (связь с существующей моделью Person)
    head_position = models.CharField(
        max_length=200,
        verbose_name='Должность руководителя',
        blank=True,
        null=True
    )
    head = models.ForeignKey(
        'core.Person',  # Используем существующую модель Person
        on_delete=models.SET_NULL,
        related_name='headed_foivs',
        verbose_name='Руководитель',
        db_column='head_id',
        null=True,
        blank=True
    )
    
    # Иерархия (подчиненность)
    parent_foiv = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='subordinate_foivs',
        verbose_name='Вышестоящий ФОИВ',
        null=True,
        blank=True,
        db_column='parent_foiv_id'
    )
    
    # Контактная информация
    address = models.TextField(
        verbose_name='Адрес',
        blank=True,
        null=True
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='foivs',
        verbose_name='Город',
        db_column='city_id',
        null=True,
        blank=True
    )
    phone = models.CharField(
        max_length=200,
        verbose_name='Телефон',
        blank=True,
        null=True
    )
    email = models.EmailField(
        max_length=200,
        verbose_name='Email',
        blank=True,
        null=True
    )
    website = models.URLField(
        max_length=500,
        verbose_name='Официальный сайт',
        blank=True,
        null=True
    )
    
    # Дополнительная информация
    foundation_date = models.DateField(
        verbose_name='Дата основания',
        null=True,
        blank=True
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True,
        null=True
    )
    
    # Системные поля
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        db_index=True
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
        verbose_name = 'Федеральный орган исполнительной власти'
        verbose_name_plural = 'Федеральные органы исполнительной власти'
        ordering = ['sequence_number']
        indexes = [
            models.Index(fields=['short_name']),
            models.Index(fields=['okogu_code']),
            models.Index(fields=['sequence_number']),
            models.Index(fields=['foiv_type']),
            models.Index(fields=['parent_foiv']),
        ]
        unique_together = [['okogu_code'], ['sequence_number']]

    def __str__(self):
        return self.short_name

    def save(self, *args, **kwargs):
        # Генерация name_for_sort для правильной сортировки
        if not self.name_for_sort and self.short_name:
            # Убираем кавычки и слова "России", "Федеральное" для сортировки
            name_for_sort = self.short_name
            name_for_sort = name_for_sort.replace('"', '')
            name_for_sort = name_for_sort.replace('России', '').strip()
            name_for_sort = name_for_sort.replace('Федеральная', '')
            name_for_sort = name_for_sort.replace('Федеральное', '')
            name_for_sort = name_for_sort.replace('Федеральный', '')
            self.name_for_sort = name_for_sort.strip()
        
        # Генерация slug, если не указан
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
        
        super().save(*args, **kwargs)

    def get_full_hierarchy(self):
        """
        Возвращает полную иерархию подчиненности
        """
        hierarchy = []
        current = self
        while current:
            hierarchy.append(str(current))
            current = current.parent_foiv
        return " → ".join(reversed(hierarchy))
    

class RFRepresentative(models.Model):
    """
    Представительство Российской Федерации в лице ФОИВ
    Например: "Российская Федерация, от имени которой выступает Министерство промышленности и торговли Российской Федерации"
    """
    rf_representative_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='ID представительства'
    )
    
    foiv = models.ForeignKey(
        FOIV,
        on_delete=models.CASCADE,
        related_name='rf_representatives',
        verbose_name='ФОИВ',
        db_index=True
    )
    
    # Полная строка как в исходных данных
    full_text = models.TextField(
        unique=True,
        verbose_name='Полный текст',
        help_text='Полная строка из каталога (например: "Российская Федерация, от имени которой выступает Минпромторг России")',
        db_index=True
    )
    
    # Варианты написания для поиска
    search_text = models.TextField(
        verbose_name='Текст для поиска',
        help_text='Нормализованный текст для поиска (без кавычек, лишних пробелов)',
        db_index=True
    )
    
    # Сокращенный вариант для отображения
    display_name = models.CharField(
        max_length=500,
        verbose_name='Отображаемое название',
        help_text='Краткое название для отображения'
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
        verbose_name = 'Представительство РФ'
        verbose_name_plural = 'Представительства РФ'
        ordering = ['foiv__short_name']
        indexes = [
            models.Index(fields=['search_text']),
            models.Index(fields=['full_text']),
        ]
    
    def __str__(self):
        return self.display_name or f"РФ в лице {self.foiv.short_name}"
    
    def save(self, *args, **kwargs):
        if not self.search_text and self.full_text:
            # Нормализуем текст для поиска
            self.search_text = self.normalize_text(self.full_text)
        if not self.display_name and self.foiv:
            self.display_name = f"РФ в лице {self.foiv.short_name}"
        super().save(*args, **kwargs)
    
    @staticmethod
    def normalize_text(text):
        """Нормализация текста для поиска"""
        if not text:
            return text
        # Приводим к нижнему регистру, убираем лишние пробелы
        text = ' '.join(text.lower().split())
        # Убираем кавычки и скобки
        text = re.sub(r'["\'\(\)]', '', text)
        return text