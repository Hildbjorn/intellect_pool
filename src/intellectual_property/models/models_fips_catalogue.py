from django.db import models

from intellectual_property.models.models_ip import IPType


class FipsOpenDataCatalogue(models.Model):
    """
    Модель для хранения данных из каталога открытых данных ФИПС Роспатента.
    """
    
    ip_type = models.ForeignKey(
        IPType,
        on_delete=models.PROTECT,
        verbose_name='Тип РИД',
        help_text='Тип РИД, к которому относится каталог',
        related_name='catalogues',
        db_index=True
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name='Название каталога',
        help_text='Название каталога (автоматически извлекается из имени файла)',
        blank=False,
        null=False
    )
    
    catalogue_file = models.FileField(
        upload_to='ip_catalogue/%Y/%m/',
        verbose_name='CSV файл каталога',
        help_text='CSV файл каталога с сайта Роспатента',
        blank=True,
        null=True
    )
    
    publication_date = models.DateField(
        verbose_name='Дата публикации каталога',
        help_text='Дата публикации каталога на сайте Роспатента',
        blank=True,
        null=True,
        db_index=True
    )
    
    upload_date = models.DateTimeField(
        verbose_name='Дата загрузки',
        help_text='Дата и время загрузки файла в систему',
        auto_now_add=True
    )
    
    last_modified = models.DateTimeField(
        verbose_name='Дата последнего изменения',
        help_text='Дата и время последнего изменения записи',
        auto_now=True
    )
    
    description = models.TextField(
        verbose_name='Описание',
        help_text='Дополнительная информация о каталоге',
        blank=True
    )
    
    def __str__(self):
        if self.name:
            return self.name
        date_str = self.publication_date.strftime('%d.%m.%Y') if self.publication_date else 'Дата неизвестна'
        return f"Каталог {self.ip_type.name} от {date_str}"
    
    class Meta:
        verbose_name = 'Каталог открытых данных ФИПС'
        verbose_name_plural = 'Каталоги открытых данных ФИПС'
        ordering = ['-publication_date', '-upload_date']
        indexes = [
            models.Index(fields=['ip_type', 'publication_date']),
            models.Index(fields=['publication_date']),
            models.Index(fields=['name']),
        ]
        unique_together = ['id', 'publication_date']
