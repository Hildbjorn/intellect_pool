from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse


class IPType(models.Model):
    """
    Справочник видов РИД (изобретения, полезные модели, промобразцы, ПЭВМ, БД, ТИМС)
    """
    name = models.CharField('Наименование вида РИД', max_length=100)
    code = models.CharField('Код', max_length=20, unique=True, help_text='Код для использования в API/отчетах')
    legal_protection_form = models.CharField('Вид правовой охраны по ГК', max_length=100, blank=True)
    order = models.PositiveSmallIntegerField('Порядок сортировки', default=0)

    class Meta:
        verbose_name = 'Вид РИД'
        verbose_name_plural = 'Виды РИД'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


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


class Person(models.Model):
    """
    Физическое лицо (автор, изобретатель)
    """
    last_name = models.CharField('Фамилия', max_length=100)
    first_name = models.CharField('Имя', max_length=100)
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    last_name_en = models.CharField('Фамилия (латиница)', max_length=100, blank=True)
    first_name_en = models.CharField('Имя (латиница)', max_length=100, blank=True)
    
    # Для идентификации
    snils = models.CharField('СНИЛС', max_length=14, blank=True, unique=True, null=True)
    
    # Контактные данные (опционально)
    email = models.EmailField('Email', blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)

    class Meta:
        verbose_name = 'Физическое лицо'
        verbose_name_plural = 'Физические лица'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
        ]

    def __str__(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return ' '.join(filter(None, parts))


class Organization(models.Model):
    """
    Юридическое лицо (правообладатель, организация автора)
    """
    name = models.CharField('Полное наименование', max_length=500)
    name_short = models.CharField('Краткое наименование', max_length=255, blank=True)
    name_en = models.CharField('Наименование на английском', max_length=500, blank=True)
    
    # Реквизиты
    inn = models.CharField('ИНН', max_length=12, blank=True, db_index=True)
    kpp = models.CharField('КПП', max_length=9, blank=True)
    ogrn = models.CharField('ОГРН', max_length=13, blank=True)
    
    # Адрес
    country = models.ForeignKey(Country, on_delete=models.PROTECT, verbose_name='Страна', 
                                related_name='organizations', null=True, blank=True)
    city = models.CharField('Город', max_length=100, blank=True)
    address = models.TextField('Юридический адрес', blank=True)
    
    # Контакты
    email = models.EmailField('Email', blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    website = models.URLField('Сайт', blank=True)

    class Meta:
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'
        ordering = ['name']
        indexes = [
            models.Index(fields=['inn']),
        ]

    def __str__(self):
        return self.name_short or self.name


class IntellectualAsset(models.Model):
    """
    Основная модель — объект интеллектуальной собственности (РИД)
    """
    # Тип РИД
    ip_type = models.ForeignKey(IPType, on_delete=models.PROTECT, verbose_name='Вид РИД',
                                related_name='assets')
    
    # Основные идентификаторы
    registration_number = models.CharField('Регистрационный номер', max_length=50, unique=True, db_index=True)
    name = models.CharField('Наименование РИД', max_length=1000)
    
    # Даты
    registration_date = models.DateField('Дата государственной регистрации', null=True, blank=True)
    application_date = models.DateField('Дата подачи заявки', null=True, blank=True)
    patent_starting_date = models.DateField('Дата начала отсчета срока действия', null=True, blank=True)
    expiration_date = models.DateField('Дата истечения срока действия', null=True, blank=True)
    
    # Статус
    actual = models.BooleanField('Признак действия правовой охраны', default=True, db_index=True)
    
    # Дополнительные даты (для разных типов РИД)
    creation_year = models.PositiveSmallIntegerField('Год создания', null=True, blank=True,
                                                      validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    publication_year = models.PositiveSmallIntegerField('Год обнародования', null=True, blank=True,
                                                         validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    update_year = models.PositiveSmallIntegerField('Год обновления', null=True, blank=True,
                                                    validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    
    # Топологии (первые использования)
    first_usage_date = models.DateField('Дата первого использования топологии', null=True, blank=True)
    
    # URL
    publication_url = models.URLField('URL публикации в реестрах ФИПС', max_length=500, blank=True)
    
    # Специальные поля
    revoked_patent_number = models.CharField('Номер аннулированного патента', max_length=50, blank=True)
    information_about_the_obligation_to_conclude_contract_of_alienation = models.TextField(
        'Сведения об обязательстве заключить договор об отчуждении', blank=True
    )
    
    # Полнотекстовые поля
    abstract = models.TextField('Реферат', blank=True)
    claims = models.TextField('Формула', blank=True)
    description = models.TextField('Описание', blank=True)
    source_code_deposit = models.TextField('Исходный код (депонируемые материалы)', blank=True)
    
    # Связи со справочниками (многие ко многим через дополнительные таблицы, кроме тех, где нужны доп. поля)
    # Для простых many-to-many используем встроенное поле ManyToManyField
    
    class Meta:
        verbose_name = 'Объект интеллектуальной собственности'
        verbose_name_plural = 'Объекты интеллектуальной собственности'
        ordering = ['-registration_date', 'name']
        indexes = [
            models.Index(fields=['registration_number']),
            models.Index(fields=['name']),
            models.Index(fields=['actual', 'expiration_date']),
        ]

    def __str__(self):
        return f'{self.registration_number} - {self.name[:50]}'


class Authorship(models.Model):
    """
    Связь РИД с авторами (многие ко многим с дополнительными полями)
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='РИД',
                              related_name='authorships')
    person = models.ForeignKey(Person, on_delete=models.PROTECT, verbose_name='Автор',
                               related_name='authorships')
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, 
                                     verbose_name='Организация автора', 
                                     null=True, blank=True, related_name='authorships')
    author_order = models.PositiveSmallIntegerField('Порядок автора', default=1)
    is_refused_to_be_mentioned = models.BooleanField('Отказался быть упомянутым', default=False)

    class Meta:
        verbose_name = 'Авторство'
        verbose_name_plural = 'Авторство'
        ordering = ['author_order']
        unique_together = [['asset', 'person']]  # Один автор не может быть дважды по одному РИД

    def __str__(self):
        return f'{self.asset} - {self.person}'


class Ownership(models.Model):
    """
    Связь РИД с правообладателями (многие ко многим с дополнительными полями)
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='РИД',
                              related_name='ownerships')
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, 
                                     verbose_name='Правообладатель (организация)',
                                     null=True, blank=True, related_name='ownerships')
    person = models.ForeignKey(Person, on_delete=models.PROTECT, 
                               verbose_name='Правообладатель (физлицо)',
                               null=True, blank=True, related_name='ownerships')
    share_percentage = models.DecimalField('Доля владения, %', max_digits=5, decimal_places=2,
                                            null=True, blank=True)
    start_date = models.DateField('Дата начала владения', null=True, blank=True)
    end_date = models.DateField('Дата прекращения владения', null=True, blank=True)

    class Meta:
        verbose_name = 'Правообладание'
        verbose_name_plural = 'Правообладание'
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(organization__isnull=False, person__isnull=True) |
                    models.Q(organization__isnull=True, person__isnull=False)
                ),
                name='either_org_or_person'
            )
        ]

    def __str__(self):
        holder = self.organization or self.person
        return f'{self.asset} - {holder}'


class AdditionalPatent(models.Model):
    """
    Информация о дополнительном патенте (продление срока)
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='Основной РИД',
                              related_name='additional_patents')
    extended_until = models.DateField('Срок продлен до')
    decision_date = models.DateField('Дата решения о продлении')
    formula_numbers = models.CharField('Номера пунктов формулы', max_length=255, blank=True,
                                       help_text='Номера пунктов формулы, в отношении которых продлен срок')
    description = models.TextField('Описание', blank=True)

    class Meta:
        verbose_name = 'Дополнительный патент'
        verbose_name_plural = 'Дополнительные патенты'

    def __str__(self):
        return f'Продление для {self.asset} до {self.extended_until}'


class Image(models.Model):
    """
    Изображения (для промышленных образцов, чертежи для изобретений)
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='РИД',
                              related_name='images')
    image = models.ImageField('Изображение', upload_to='patent_images/%Y/%m/')
    caption = models.CharField('Подпись', max_length=255, blank=True)
    order = models.PositiveSmallIntegerField('Порядок', default=1)
    is_main = models.BooleanField('Главное изображение', default=False)

    class Meta:
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'
        ordering = ['order']

    def __str__(self):
        return f'Изображение для {self.asset}'


class FirstUsageCountry(models.Model):
    """
    Страны первого использования топологии (один ко многим)
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='РИД',
                              related_name='first_usage_countries')
    country = models.ForeignKey(Country, on_delete=models.PROTECT, verbose_name='Страна')

    class Meta:
        verbose_name = 'Страна первого использования'
        verbose_name_plural = 'Страны первого использования'
        unique_together = [['asset', 'country']]

    def __str__(self):
        return f'{self.asset} - {self.country}'


class ParisConventionPriority(models.Model):
    """
    Приоритет по Парижской конвенции
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='РИД',
                              related_name='paris_priorities')
    country = models.ForeignKey(Country, on_delete=models.PROTECT, verbose_name='Страна подачи')
    priority_date = models.DateField('Дата подачи первой заявки')
    priority_number = models.CharField('Номер первой заявки', max_length=50)

    class Meta:
        verbose_name = 'Конвенционный приоритет'
        verbose_name_plural = 'Конвенционные приоритеты'
        ordering = ['priority_date']

    def __str__(self):
        return f'{self.asset} - {self.country} {self.priority_date}'


class PCTApplication(models.Model):
    """
    Информация о PCT заявке
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='РИД',
                              related_name='pct_applications')
    application_number = models.CharField('Номер PCT заявки', max_length=50)
    application_date = models.DateField('Дата подачи PCT заявки')
    publish_date = models.DateField('Дата публикации PCT заявки', null=True, blank=True)
    publish_number = models.CharField('Номер публикации PCT заявки', max_length=50, blank=True)
    examination_start_date = models.DateField('Дата начала рассмотрения на национальной фазе', 
                                               null=True, blank=True)

    class Meta:
        verbose_name = 'PCT заявка'
        verbose_name_plural = 'PCT заявки'

    def __str__(self):
        return f'PCT {self.application_number} для {self.asset}'


class EurasianApplication(models.Model):
    """
    Информация о евразийской заявке
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='РИД',
                              related_name='ea_applications')
    application_number = models.CharField('Номер евразийской заявки', max_length=50)
    application_date = models.DateField('Дата подачи евразийской заявки')
    publish_date = models.DateField('Дата публикации евразийской заявки', null=True, blank=True)
    publish_number = models.CharField('Номер публикации евразийской заявки', max_length=50, blank=True)

    class Meta:
        verbose_name = 'Евразийская заявка'
        verbose_name_plural = 'Евразийские заявки'

    def __str__(self):
        return f'ЕА {self.application_number} для {self.asset}'


class AssetProgrammingLanguage(models.Model):
    """
    Связь РИД (ПЭВМ) с языками программирования
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='РИД',
                              related_name='programming_languages')
    language = models.ForeignKey(ProgrammingLanguage, on_delete=models.PROTECT, 
                                 verbose_name='Язык программирования')

    class Meta:
        verbose_name = 'Язык программирования РИД'
        verbose_name_plural = 'Языки программирования РИД'
        unique_together = [['asset', 'language']]

    def __str__(self):
        return f'{self.asset} - {self.language}'


class AssetDBMS(models.Model):
    """
    Связь РИД (БД) с СУБД
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='РИД',
                              related_name='dbms_list')
    dbms = models.ForeignKey(DBMS, on_delete=models.PROTECT, verbose_name='СУБД')

    class Meta:
        verbose_name = 'СУБД РИД'
        verbose_name_plural = 'СУБД РИД'
        unique_together = [['asset', 'dbms']]

    def __str__(self):
        return f'{self.asset} - {self.dbms}'


class AssetOperatingSystem(models.Model):
    """
    Связь РИД (ПЭВМ) с операционными системами
    """
    asset = models.ForeignKey(IntellectualAsset, on_delete=models.CASCADE, verbose_name='РИД',
                              related_name='operating_systems')
    os = models.ForeignKey(OperatingSystem, on_delete=models.PROTECT, verbose_name='ОС')

    class Meta:
        verbose_name = 'ОС РИД'
        verbose_name_plural = 'ОС РИД'
        unique_together = [['asset', 'os']]

    def __str__(self):
        return f'{self.asset} - {self.os}'