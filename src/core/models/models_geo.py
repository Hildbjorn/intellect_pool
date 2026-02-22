from django.db import models
from django.utils.text import slugify
from common.utils import TextUtils


class Country(models.Model):
    """
    Справочник стран (ISO 3166)
    """
    name = models.CharField('Название страны', max_length=100)
    name_en = models.CharField('Название на английском', max_length=100, blank=True)
    code = models.CharField('Код (двухбуквенный)', max_length=2, unique=True)
    code_alpha3 = models.CharField('Код (трехбуквенный)', max_length=3, blank=True)

    class Meta:
        verbose_name = 'Страна'
        verbose_name_plural = 'Страны'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class District(models.Model):
    """
    Федеральный округ
    """
    district_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID округа'
    )
    district = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Федеральный округ'
    )
    district_short = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Аббревиатура',
        help_text='Например: ЦФО, СЗФО'
    )
    slug = models.SlugField(
        max_length=120,
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
        verbose_name = 'Федеральный округ'
        verbose_name_plural = 'Федеральные округа'
        ordering = ['district']

    def __str__(self):
        return f"{self.district} ({self.district_short})"

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
        super().save(*args, **kwargs)


class Region(models.Model):
    """
    Регион/область/республика/край
    """
    region_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID региона'
    )
    title = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Регион'
    )
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name='regions',
        verbose_name='Федеральный округ',
        db_column='district_id'
    )
    slug = models.SlugField(
        max_length=120,
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
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
        super().save(*args, **kwargs)


class City(models.Model):
    """
    Город/населенный пункт
    """
    city_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='ID города'
    )
    city = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name='Город'
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name='cities',
        verbose_name='Регион',
        db_column='region_id'
    )
    latitude = models.FloatField(
        verbose_name='Широта',
        blank=True,
        null=True
    )
    longitude = models.FloatField(
        verbose_name='Долгота',
        blank=True,
        null=True
    )
    slug = models.SlugField(
        max_length=170,
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
        verbose_name = 'Город'
        verbose_name_plural = 'Города'
        ordering = ['city']
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['region', 'city']),
        ]

    def __str__(self):
        return f"{self.city}, {self.region.title}"

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = TextUtils.generate_slug(
                self,
                slug_field_name='slug'
            )[:520]
        super().save(*args, **kwargs)

    def get_coordinates(self):
        """Возвращает кортеж (широта, долгота)"""
        if self.latitude and self.longitude:
            return (self.latitude, self.longitude)
        return None