from django.db import models
from common.utils.text import TextUtils
from core.models.models_foiv import FOIV
from core.models.models_geo import Country
from core.models.models_it import DBMS, OperatingSystem, ProgrammingLanguage
from core.models.models_organization import Organization
from core.models.models_person import Person

class ProtectionDocumentType(models.Model):
    """
    Модель для хранения видов охранных документов.
    """
    
    name = models.CharField(
        max_length=255,
        verbose_name='Наименование',
        help_text='Наименование вида охранного документа',
        unique=True,
        db_index=True
    )
    
    description = models.TextField(
        verbose_name='Описание',
        help_text='Подробное описание вида охранного документа',
        blank=True
    )
    
    slug = models.SlugField(
        max_length=255,
        verbose_name='URL-идентификатор',
        help_text='Уникальный идентификатор для использования в URL',
        unique=True,
        db_index=True
    )
    
    class Meta:
        verbose_name = 'Вид охранного документа'
        verbose_name_plural = 'Виды охранных документов'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
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


class IPType(models.Model):
    """
    Модель для хранения типов результатов интеллектуальной деятельности (РИД).
    """
    
    name = models.CharField(
        max_length=255,
        verbose_name='Наименование',
        help_text='Наименование типа РИД',
        unique=True,
        db_index=True
    )
    
    description = models.TextField(
        verbose_name='Описание',
        help_text='Подробное описание типа РИД и его характеристик',
        blank=True
    )
    
    protection_document_type = models.ForeignKey(
        ProtectionDocumentType,
        on_delete=models.PROTECT,
        verbose_name='Вид охранного документа',
        help_text='Тип документа, удостоверяющего охранные права на данный РИД',
        related_name='ip_types',
        db_index=True
    )
    
    validity_duration = models.PositiveIntegerField(
        verbose_name='Срок действия, лет',
        help_text='Количество лет действия охранного документа',
        blank=True,
        null=True
    )
    
    slug = models.SlugField(
        max_length=255,
        verbose_name='URL-идентификатор',
        help_text='Уникальный идентификатор для использования в URL',
        unique=True,
        db_index=True
    )
    
    class Meta:
        verbose_name = 'Тип РИД'
        verbose_name_plural = 'Типы РИД'
        ordering = ['id']
        indexes = [
            models.Index(fields=['name', 'protection_document_type']),
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
    
    @property
    def protection_document_name(self):
        """Возвращает наименование охранного документа."""
        return self.protection_document_type.name if self.protection_document_type else None


class AdditionalPatent(models.Model):
    """
    Дополнительные патенты, выданные для продления срока действия.
    """
    patent_number = models.CharField(
        max_length=50,
        verbose_name='Номер дополнительного патента',
        null=True,
        blank=True,
        db_index=True
    )
    patent_date = models.DateField(
        verbose_name='Дата выдачи дополнительного патента',
        null=True,
        blank=True
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )
    
    class Meta:
        verbose_name = 'Дополнительный патент'
        verbose_name_plural = 'Дополнительные патенты'
    
    def __str__(self):
        return self.patent_number


class IPImage(models.Model):
    """
    Изображения, связанные с РИД (чертежи, рендеры, скриншоты).
    """
    image = models.ImageField(
        upload_to='ip_images/%Y/%m/',
        verbose_name='Изображение'
    )
    title = models.CharField(
        max_length=255,
        verbose_name='Название',
        blank=True
    )
    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )
    is_main = models.BooleanField(
        default=False,
        verbose_name='Главное изображение'
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Порядок сортировки'
    )
    
    class Meta:
        verbose_name = 'Изображение РИД'
        verbose_name_plural = 'Изображения РИД'
        ordering = ['sort_order', 'id']
    
    def __str__(self):
        return self.title or f"Изображение {self.id}"


class IPObject(models.Model):
    """
    Основная модель для всех РИД.
    """
    
    # === Основная информация ===
    name = models.CharField(
        max_length=500,
        verbose_name='Наименование РИД',
        db_index=True
    )
    
    ip_type = models.ForeignKey(
        IPType,
        on_delete=models.PROTECT,
        verbose_name='Вид РИД',
        related_name='ip_objects',
        null=True,
        blank=True,
        db_index=True
    )
    
    actual = models.BooleanField(
        default=True,
        verbose_name='Признак действия правовой охраны',
        help_text='Отметьте, если правовая охрана действует',
        db_index=True
    )
    
    # === Авторы и правообладатели ===
    authors = models.ManyToManyField(
        Person,
        related_name='authored_ip_objects',
        verbose_name='Авторы',
        blank=True
    )
    
    owner_foivs = models.ManyToManyField(
        FOIV,
        related_name='owned_ip_objects_foiv',
        verbose_name='Правообладатели (ФОИВ)',
        blank=True
    )
    owner_organizations = models.ManyToManyField(
        Organization,
        related_name='owned_ip_objects_organization',
        verbose_name='Правообладатели (организации)',
        blank=True
    )
    owner_persons = models.ManyToManyField(
        Person,
        related_name='owned_ip_objects_person',
        verbose_name='Правообладатели (физ. лица)',
        blank=True
    )
    
    # === Даты и сроки ===
    creation_year = models.PositiveSmallIntegerField(
        verbose_name='Год создания',
        null=True,
        blank=True
    )
    
    publication_year = models.PositiveSmallIntegerField(
        verbose_name='Год обнародования',
        null=True,
        blank=True
    )
    
    update_year = models.PositiveSmallIntegerField(
        verbose_name='Год обновления',
        null=True,
        blank=True
    )
    
    application_date = models.DateField(
        verbose_name='Дата подачи заявки на государственную регистрацию',
        null=True,
        blank=True
    )
    
    registration_date = models.DateField(
        verbose_name='Дата государственной регистрации',
        null=True,
        blank=True
    )
    
    patent_starting_date = models.DateField(
        verbose_name='Дата начала отсчета срока действия патента',
        null=True,
        blank=True
    )
    
    expiration_date = models.DateField(
        verbose_name='Дата истечения срока действия патента / исключительного права',
        null=True,
        blank=True
    )
    
    # === Номера и идентификаторы ===
    registration_number = models.CharField(
        max_length=50,
        verbose_name='Регистрационный номер изобретения (номер патента)',
        blank=True,
        db_index=True
    )
    
    revoked_patent_number = models.CharField(
        max_length=50,
        verbose_name='Номер аннулированного патента, признанного недействительным частично',
        blank=True
    )
    
    publication_url = models.URLField(
        max_length=500,
        verbose_name='URL публикации в открытых реестрах сайта ФИПС',
        blank=True
    )
    
    # === Евразийская заявка ===
    ea_application_number = models.CharField(
        max_length=50,
        verbose_name='Номер евразийской заявки',
        blank=True
    )
    
    ea_application_date = models.DateField(
        verbose_name='Дата подачи евразийской заявки',
        null=True,
        blank=True
    )
    
    ea_application_publish_number = models.CharField(
        max_length=50,
        verbose_name='Номер публикации евразийской заявки',
        blank=True
    )
    
    ea_application_publish_date = models.DateField(
        verbose_name='Дата публикации евразийской заявки',
        null=True,
        blank=True
    )
    
    # === PCT заявка ===
    pct_application_number = models.CharField(
        max_length=50,
        verbose_name='Номер PCT заявки',
        blank=True
    )
    
    pct_application_date = models.DateField(
        verbose_name='Дата подачи PCT заявки',
        null=True,
        blank=True
    )
    
    pct_application_publish_number = models.CharField(
        max_length=50,
        verbose_name='Номер публикации PCT заявки',
        blank=True
    )
    
    pct_application_publish_date = models.DateField(
        verbose_name='Дата публикации PCT заявки',
        null=True,
        blank=True
    )
    
    pct_application_examination_start_date = models.DateField(
        verbose_name='Дата начала рассмотрения заявки РСТ на национальной фазе',
        null=True,
        blank=True
    )
    
    # === Парижская конвенция ===
    paris_convention_priority_number = models.CharField(
        max_length=50,
        verbose_name='Номер первой заявки в государстве - участнике Парижской конвенции',
        blank=True
    )
    
    paris_convention_priority_date = models.DateField(
        verbose_name='Дата подачи первой заявки в государстве - участнике Парижской конвенции',
        null=True,
        blank=True
    )
    
    paris_convention_priority_country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        verbose_name='Код страны подачи первой заявки',
        related_name='paris_priority_ip_objects',
        null=True,
        blank=True
    )
    
    # === Использование топологии ===
    first_usage_date = models.DateField(
        verbose_name='Дата первого использования топологии',
        null=True,
        blank=True
    )
    
    first_usage_countries = models.ManyToManyField(
        Country,
        related_name='first_usage_ip_objects',
        verbose_name='Страна (страны) первого использования топологии',
        blank=True
    )
    
    # === Документы и обязательства ===
    information_about_the_obligation_to_conclude_contract_of_alienation = models.TextField(
        verbose_name='Сведения о поданном заявлении об обязательстве заключить договор об отчуждении патента',
        blank=True
    )
    
    # === Текстовые поля ===
    abstract = models.TextField(
        verbose_name='Реферат',
        blank=True
    )
    
    claims = models.TextField(
        verbose_name='Формула',
        blank=True
    )
    
    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )
    
    source_code_deposit = models.TextField(
        verbose_name='Исходный код (депонируемые материалы)',
        blank=True
    )
    
    # === Связанные модели (One-to-Many) ===
    additional_patents = models.ManyToManyField(
        AdditionalPatent,
        related_name='ip_objects',
        verbose_name='Дополнительные патенты для продления срока действия',
        blank=True
    )
    
    images = models.ManyToManyField(
        IPImage,
        related_name='ip_objects',
        verbose_name='Фотографии или рендеры изделия',
        blank=True
    )
    
    # === IT-специфика (для программ) ===
    programming_languages = models.ManyToManyField(
        ProgrammingLanguage,
        related_name='ip_objects',
        verbose_name='Язык(и) программирования',
        blank=True
    )
    
    dbms = models.ManyToManyField(
        DBMS,
        related_name='ip_objects',
        verbose_name='Система управления базами данных',
        blank=True
    )
    
    operating_systems = models.ManyToManyField(
        OperatingSystem,
        related_name='ip_objects',
        verbose_name='Целевая операционная система',
        blank=True
    )
    
    # === Системные поля ===
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания',
        null=True,
        blank=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = 'Объект РИД'
        verbose_name_plural = 'Объекты РИД'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['registration_number']),
            models.Index(fields=['application_date']),
            models.Index(fields=['registration_date']),
            models.Index(fields=['expiration_date']),
            models.Index(fields=['ip_type', 'actual']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def all_owners(self):
        """Возвращает всех правообладателей (всех типов)"""
        from itertools import chain
        return list(chain(
            self.owner_persons.all(),
            self.owner_organizations.all(),
            self.owner_foivs.all()
        ))
    
    @property
    def is_expired(self):
        """Проверяет, истек ли срок действия"""
        from django.utils import timezone
        if self.expiration_date:
            return self.expiration_date < timezone.now().date()
        return False