from django.db import models
from django.utils.text import slugify


class Industry(models.Model):
    """
    Отрасль промышленности (например: Авиационная, Судостроительная и т.д.)
    """
    industry_id = models.PositiveSmallIntegerField(
        primary_key=True,
        verbose_name='ID отрасли'
    )
    industry = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Отрасль'
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
        verbose_name = 'Отрасль промышленности'
        verbose_name_plural = 'Отрасли промышленности'
        ordering = ['industry']

    def __str__(self):
        return self.industry

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.industry)[:120]
        super().save(*args, **kwargs)