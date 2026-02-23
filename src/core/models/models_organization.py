from django.db import models
from django.utils.text import slugify
from core.models.models_geo import City
from core.models.models_industry import Industry
from core.models.models_person import Person
from common.utils import TextUtils


# core/models/models_organization_normalization.py
from django.db import models

class OrganizationNormalizationRule(models.Model):
    """
    Правила нормализации названий организаций
    """
    original_text = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Исходный текст',
        db_index=True,
        help_text='Текст, который нужно заменить (например, "федеральное государственное унитарное предприятие")'
    )
    
    replacement_text = models.CharField(
        max_length=100,
        verbose_name='Текст для замены',
        help_text='На что заменить (например, "фгуп")'
    )
    
    RULE_TYPES = [
        ('full', 'Полная форма → аббревиатура'),
        ('abbr', 'Аббревиатура → аббревиатура'),
        ('variant', 'Вариант написания → норматив'),
        ('suffix', 'Суффикс/окончание'),
        ('prefix', 'Префикс'),
        ('ignore', 'Игнорировать при поиске'),
    ]
    rule_type = models.CharField(
        max_length=20,
        choices=RULE_TYPES,
        default='full',
        verbose_name='Тип правила',
        db_index=True
    )
    
    priority = models.PositiveSmallIntegerField(
        default=100,
        verbose_name='Приоритет (меньше = раньше)',
        help_text='Правила с меньшим приоритетом применяются раньше'
    )
    
    class Meta:
        verbose_name = 'Правило нормализации'
        verbose_name_plural = 'Правила нормализации'
        ordering = ['priority', 'original_text']
        indexes = [
            models.Index(fields=['original_text']),
            models.Index(fields=['rule_type']),
        ]
    
    def __str__(self):
        return f"{self.original_text} → {self.replacement_text}"


class ActivityType(models.Model):
    """
    Тип деятельности предприятия (Промышленное, Научное, Прочее)
    """
    activity_type_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID типа деятельности'
    )
    activity_type = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Тип деятельности'
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
        verbose_name = 'Тип деятельности'
        verbose_name_plural = 'Типы деятельности'
        ordering = ['activity_type_id']

    def __str__(self):
        return self.activity_type


class CeoPosition(models.Model):
    """
    Должность руководителя (Генеральный директор, Директор и т.д.)
    """
    ceo_position_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID должности'
    )
    ceo_position = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Должность'
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
        verbose_name = 'Должность руководителя'
        verbose_name_plural = 'Должности руководителей'
        ordering = ['ceo_position_id']

    def __str__(self):
        return self.ceo_position


class Organization(models.Model):
    """
    Предприятие/организация (основная модель)
    """
    organization_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='ID организации'
    )
    
    # Коды и идентификаторы
    okpo = models.CharField(
        max_length=20,
        verbose_name='ОКПО',
        blank=True,
        null=True,
        db_index=True
    )
    ogrn = models.CharField(
        max_length=20,
        verbose_name='ОГРН',
        blank=True,
        null=True,
        db_index=True
    )
    inn = models.CharField(
        max_length=20,
        verbose_name='ИНН',
        blank=True,
        null=True,
        db_index=True
    )
    kpp = models.CharField(
        max_length=20,
        verbose_name='КПП',
        blank=True,
        null=True
    )
    okato = models.CharField(
        max_length=20,
        verbose_name='ОКАТО',
        blank=True,
        null=True
    )
    
    # Названия
    name = models.CharField(
        max_length=500,
        verbose_name='Краткое название',
        help_text='Название как в первой колонке'
    )
    full_name = models.TextField(
        verbose_name='Полное название',
        blank=True,
        null=True
    )
    short_name = models.CharField(
        max_length=500,
        verbose_name='Сокращенное название',
        blank=True,
        null=True
    )
    
    # Связи
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='Город',
        db_column='city_id',
        null=True,
        blank=True
    )
    address = models.TextField(
        verbose_name='Адрес',
        blank=True,
        null=True
    )
    url = models.URLField(
        max_length=500,
        verbose_name='Сайт',
        blank=True,
        null=True
    )
    
    # Холдинги (самоссылающиеся связи)
    holding_1 = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='subsidiaries_1',
        verbose_name='Холдинг 1 уровня',
        null=True,
        blank=True,
        db_column='holding_1_id'
    )
    holding_2 = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='subsidiaries_2',
        verbose_name='Холдинг 2 уровня',
        null=True,
        blank=True,
        db_column='holding_2_id'
    )
    holding_3 = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='subsidiaries_3',
        verbose_name='Холдинг 3 уровня',
        null=True,
        blank=True,
        db_column='holding_3_id'
    )
    
    # Классификаторы
    industry = models.ForeignKey(
        Industry,
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='Отрасль',
        db_column='industry_id',
        null=True,
        blank=True
    )
    activity_type = models.ForeignKey(
        ActivityType,
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='Тип деятельности',
        db_column='activity_type_id',
        null=True,
        blank=True
    )
    activity_description = models.TextField(
        verbose_name='Описание деятельности',
        blank=True,
        null=True
    )
    
    # Регистрационные флаги
    register_opk = models.BooleanField(
        default=False,
        verbose_name='Реестр ОПК',
        help_text='Находится в реестре организаций ОПК',
        db_index=True
    )
    strategic = models.BooleanField(
        default=False,
        verbose_name='Стратегическое предприятие',
        help_text='Входит в перечень стратегических предприятий (Распоряжение Правительства РФ)',
        db_index=True
    )
    
    # Контактная информация
    email = models.EmailField(
        max_length=200,
        verbose_name='Email',
        blank=True,
        null=True
    )
    phone = models.CharField(
        max_length=200,
        verbose_name='Телефон',
        blank=True,
        null=True
    )
    
    # Руководство
    ceo_position = models.ForeignKey(
        CeoPosition,
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='Должность руководителя',
        db_column='ceo_position_id',
        null=True,
        blank=True
    )
    ceo = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name='organizations',
        verbose_name='Руководитель',
        db_column='ceo_id',
        null=True,
        blank=True
    )
    
    # Дополнительные идентификаторы
    gisp_catalogue_id = models.CharField(
        max_length=50,
        verbose_name='ID каталога ГИСП',
        blank=True,
        null=True,
        db_index=True
    )
    
    # Системные поля
    slug = models.SlugField(
        max_length=520,
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
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['city', 'industry']),
            models.Index(fields=['register_opk']),
            models.Index(fields=['strategic']),
            models.Index(fields=['okpo']),
            models.Index(fields=['inn']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
        super().save(*args, **kwargs)

    def get_full_hierarchy(self):
        """Возвращает полную иерархию холдингов"""
        hierarchy = []
        if self.holding_3:
            hierarchy.append(str(self.holding_3))
        if self.holding_2:
            hierarchy.append(str(self.holding_2))
        if self.holding_1:
            hierarchy.append(str(self.holding_1))
        hierarchy.append(str(self))
        return " → ".join(hierarchy)

    def get_strategic_status_display(self):
        """Возвращает статус стратегического предприятия"""
        if self.strategic:
            return "Стратегическое"
        return "Не стратегическое"