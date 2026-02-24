
# Файл: management\help.txt

```
# Режим ONLY-ACTIVE: парсинг только активных записей (actual = True)
# Режим MIN-YEAR 2020: парсинг только записей 2020 года и позже
# РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД

Для запуска по типам РИД:
--ip-type invention — изобретения
--ip-type utility-model — полезные модели
--ip-type industrial-design — промышленные образцы
--ip-type integrated-circuit-topology — топологии интегральных микросхем
--ip-type computer-program — программы для ЭВМ
--ip-type database — базы данных

python manage.py pars_fips_catalogue --only-active --min-year 2020 --ip-type invention --dry-run

# Тест для изобретений
python manage.py pars_fips_catalogue --only-active --min-year 2020 --ip-type invention --max-rows 10

# Все изобретения
python manage.py pars_fips_catalogue --only-active --ip-type invention --force

============
    HELP
============

usage: manage.py pars_fips_catalogue [-h] [--catalogue-id CATALOGUE_ID] [--ip-type {invention,utility-model,industrial-design,integrated-circuit-topology,computer-program,database}] [--dry-run] [--encoding ENCODING]
                                     [--delimiter DELIMITER] [--batch-size BATCH_SIZE] [--min-year MIN_YEAR] [--skip-filters] [--only-active] [--max-rows MAX_ROWS] [--version] [-v {0,1,2,3}] [--settings SETTINGS]      
                                     [--pythonpath PYTHONPATH] [--traceback] [--no-color] [--force-color] [--skip-checks]

Парсинг каталогов открытых данных ФИПС Роспатента

options:
  -h, --help            show this help message and exit
  --catalogue-id CATALOGUE_ID
                        ID конкретного каталога для парсинга
  --ip-type {invention,utility-model,industrial-design,integrated-circuit-topology,computer-program,database}
                        Тип РИД для парсинга (если не указан, парсятся все)
  --dry-run             Режим проверки без сохранения в БД
  --encoding ENCODING   Кодировка CSV файла
  --delimiter DELIMITER
                        Разделитель в CSV файле
  --batch-size BATCH_SIZE
                        Размер пакета для bulk-операций
  --min-year MIN_YEAR   Минимальный год регистрации для фильтрации
  --skip-filters        Пропустить фильтрацию (обработать все записи)
  --only-active         Парсить только активные патенты (actual = True)
  --max-rows MAX_ROWS   Максимальное количество строк для обработки (для тестирования)
  --version             Show program's version number and exit.
  -v, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output
  --settings SETTINGS   The Python path to a settings module, e.g. "myproject.settings.main". If this isn't provided, the DJANGO_SETTINGS_MODULE environment variable will be used.
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g. "/home/djangoprojects/myproject".
  --traceback           Display a full stack trace on CommandError exceptions.
  --no-color            Don't colorize the command output.
  --force-color         Force colorization of the command output.
  --skip-checks         Skip system checks.

```


-----

# Файл: management\__init__.py

```

```


-----

# Файл: management\commands\pars_fips_catalogue.py

```
"""
Команда для парсинга каталогов открытых данных ФИПС Роспатента.
Обертка, которая делегирует выполнение соответствующим парсерам.
"""

import logging
import os

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import pandas as pd

from intellectual_property.models import FipsOpenDataCatalogue

# Импортируем парсеры из нового пакета
from ..parsers import (
    InventionParser, UtilityModelParser, IndustrialDesignParser,
    IntegratedCircuitTopologyParser, ComputerProgramParser, DatabaseParser
)
from ..utils.csv_loader import load_csv_with_strategies
from ..utils.filters import apply_filters

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Парсинг каталогов открытых данных ФИПС Роспатента'

    def add_arguments(self, parser):
        parser.add_argument('--catalogue-id', type=int, help='ID конкретного каталога для парсинга')
        parser.add_argument('--ip-type', type=str,
                        choices=['invention', 'utility-model', 'industrial-design',
                                'integrated-circuit-topology', 'computer-program', 'database'],
                        help='Тип РИД для парсинга (если не указан, парсятся все)')
        parser.add_argument('--dry-run', action='store_true', help='Режим проверки без сохранения в БД')
        parser.add_argument('--encoding', type=str, default='utf-8', help='Кодировка CSV файла')
        parser.add_argument('--delimiter', type=str, default=',', help='Разделитель в CSV файле')
        parser.add_argument('--batch-size', type=int, default=100, help='Размер пакета для bulk-операций')
        parser.add_argument('--min-year', type=int, default=2000, help='Минимальный год регистрации для фильтрации')
        parser.add_argument('--skip-filters', action='store_true', help='Пропустить фильтрацию (обработать все записи)')
        parser.add_argument('--only-active', action='store_true', help='Парсить только активные патенты (actual = True)')
        parser.add_argument('--max-rows', type=int, help='Максимальное количество строк для обработки (для тестирования)')
        parser.add_argument('--force', action='store_true', help='Принудительный парсинг даже если каталог уже обработан')
        parser.add_argument('--mark-processed', action='store_true',
                        help='Пометить каталог как обработанный (даже если были ошибки)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parsers = {
            'invention': InventionParser(self),
            'utility-model': UtilityModelParser(self),
            'industrial-design': IndustrialDesignParser(self),
            'integrated-circuit-topology': IntegratedCircuitTopologyParser(self),
            'computer-program': ComputerProgramParser(self),
            'database': DatabaseParser(self),
        }

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.encoding = options['encoding']
        self.delimiter = options['delimiter']
        self.batch_size = options['batch_size']
        self.min_year = options['min_year']
        self.skip_filters = options['skip_filters']
        self.only_active = options['only_active']
        self.max_rows = options.get('max_rows')
        self.force = options.get('force', False)
        self.mark_processed = options.get('mark_processed', False)

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД\n"))

        if self.only_active:
            self.stdout.write(self.style.WARNING("📌 Режим: парсинг только активных записей (actual = True)"))

        if self.force:
            self.stdout.write(self.style.WARNING("⚠️  Режим: принудительный парсинг (игнорирование даты обработки)"))

        catalogues = self.get_catalogues(options.get('catalogue_id'), options.get('ip_type'))

        if not catalogues:
            raise CommandError('Не найдены каталоги для парсинга')

        total_stats = {
            'catalogues': len(catalogues),
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        for catalogue in catalogues:
            self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
            self.stdout.write(self.style.SUCCESS(f"📁 Обработка каталога: {catalogue.name}"))
            self.stdout.write(self.style.SUCCESS(f"   ID: {catalogue.id}, Тип: {catalogue.ip_type.name if catalogue.ip_type else 'Неизвестно'}"))
            self.stdout.write(self.style.SUCCESS(f"{'='*60}"))

            stats = self.process_catalogue(catalogue)

            for key in ['processed', 'created', 'updated', 'skipped', 'errors']:
                total_stats[key] += stats.get(key, 0)
            total_stats['skipped_by_date'] += stats.get('skipped_by_date', 0)

        self.print_final_stats(total_stats)

    def get_catalogues(self, catalogue_id=None, ip_type_slug=None):
        queryset = FipsOpenDataCatalogue.objects.all()

        if catalogue_id:
            queryset = queryset.filter(id=catalogue_id)
        elif ip_type_slug:
            queryset = queryset.filter(ip_type__slug=ip_type_slug)
        else:
            queryset = queryset.exclude(catalogue_file='')

        return queryset.order_by('ip_type__id', '-publication_date')

    def process_catalogue(self, catalogue):
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        if not catalogue.catalogue_file:
            self.stdout.write(self.style.ERROR(f"  ❌ У каталога ID={catalogue.id} не загружен файл"))
            stats['errors'] += 1
            return stats

        if not self.force and hasattr(catalogue, 'parsed_date') and catalogue.parsed_date:
            self.stdout.write(self.style.WARNING(
                f"  ⚠️ Каталог уже был обработан {catalogue.parsed_date.strftime('%d.%m.%Y %H:%M')}"
            ))
            self.stdout.write(self.style.WARNING(f"     Используйте --force для повторного парсинга"))
            stats['skipped'] += 1
            return stats

        ip_type_slug = catalogue.ip_type.slug if catalogue.ip_type else None

        if ip_type_slug not in self.parsers:
            self.stdout.write(self.style.ERROR(f"  ❌ Нет парсера для типа РИД: {ip_type_slug}"))
            stats['errors'] += 1
            return stats

        parser = self.parsers[ip_type_slug]
        df = self.load_csv(catalogue)

        if df is None or df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Файл пуст или не удалось загрузить"))
            stats['skipped'] += 1
            return stats

        self.stdout.write(f"  📊 Загружено записей: {len(df)}")

        missing_columns = self.check_required_columns(df, parser.get_required_columns())
        if missing_columns:
            self.stdout.write(self.style.ERROR(f"  ❌ Отсутствуют обязательные колонки: {missing_columns}"))
            stats['errors'] += 1
            return stats

        if not self.skip_filters:
            df = apply_filters(df, self.min_year, self.only_active, self.stdout)

        if df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Нет данных после фильтрации"))
            stats['skipped'] += 1
            return stats

        self.stdout.write(f"  📊 После фильтрации: {len(df)} записей")

        if self.max_rows and len(df) > self.max_rows:
            df = df.head(self.max_rows)
            self.stdout.write(self.style.WARNING(f"  ⚠️ Ограничено до {self.max_rows} записей"))

        try:
            parser_stats = parser.parse_dataframe(df, catalogue)
            stats.update(parser_stats)

            if not self.dry_run and hasattr(catalogue, 'parsed_date'):
                if stats['errors'] == 0 or self.mark_processed:
                    catalogue.parsed_date = timezone.now()
                    catalogue.save(update_fields=['parsed_date'])
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Каталог помечен как обработанный"))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠️ Каталог не помечен как обработанный из-за ошибок"
                    ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка при парсинге: {e}"))
            logger.error(f"Error parsing catalogue {catalogue.id}: {e}", exc_info=True)
            stats['errors'] += 1

        return stats

    def load_csv(self, catalogue):
        file_path = catalogue.catalogue_file.path

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"  ❌ Файл не найден: {file_path}"))
            return None

        df = load_csv_with_strategies(file_path, self.encoding, self.delimiter, self.stdout)
        return df

    def check_required_columns(self, df, required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        return missing

    def print_final_stats(self, stats):
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("📊 ИТОГОВАЯ СТАТИСТИКА"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
        self.stdout.write(f"📁 Обработано каталогов: {stats['catalogues']}")
        self.stdout.write(f"📝 Всего записей обработано: {stats['processed']}")
        self.stdout.write(f"✅ Создано: {stats['created']}")
        self.stdout.write(f"🔄 Обновлено: {stats['updated']}")
        self.stdout.write(f"⏭️  Пропущено всего: {stats['skipped']}")
        self.stdout.write(f"   └─ по дате обновления: {stats.get('skipped_by_date', 0)}")

        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Ошибок: {stats['errors']}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Ошибок: {stats['errors']}"))

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены в БД"))

        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))

```


-----

# Файл: management\commands\pars_fips_catalogue_archive.py

```
"""
Команда для парсинга каталогов открытых данных ФИПС Роспатента.
Поддерживает все типы РИД: изобретения, полезные модели, промышленные образцы,
топологии интегральных микросхем, программы для ЭВМ и базы данных.
"""

import logging
import re
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Set
from collections import defaultdict

from django.db import models
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.utils import timezone
from tqdm import tqdm
import pandas as pd
import os

# Импорты natasha
from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,
    Doc,
    NamesExtractor
)

from intellectual_property.models import (
    FipsOpenDataCatalogue, IPType, ProtectionDocumentType,
    IPObject, AdditionalPatent, IPImage
)
from core.models import (
    City, Region, District, Person, Organization,
    FOIV, Country, RFRepresentative,
    OrganizationNormalizationRule, ActivityType, CeoPosition
)
from common.utils.text import TextUtils
from common.utils.dates import DateUtils

logger = logging.getLogger(__name__)


class RussianTextProcessor:
    """
    Процессор для русских текстов с использованием natasha
    """

    # Список римских цифр
    ROMAN_NUMERALS = {
        'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
        'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
        'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXX', 'XL', 'L', 'LX', 'XC',
        'C', 'CD', 'D', 'DC', 'CM', 'M'
    }

    # Аббревиатуры для поиска организаций
    ORG_ABBR = {
        'ООО', 'ЗАО', 'ОАО', 'АО', 'ПАО', 'НАО',
        'ФГУП', 'ФГБУ', 'ФГАОУ', 'ФГАУ', 'ФГКУ',
        'НИИ', 'КБ', 'ОКБ', 'СКБ', 'ЦКБ', 'ПКБ',
        'НПО', 'НПП', 'НПФ', 'НПЦ', 'НИЦ',
        'МУП', 'ГУП', 'ИЧП', 'ТОО', 'АОЗТ', 'АООТ',
        'РФ', 'РАН', 'СО РАН', 'УрО РАН', 'ДВО РАН',
        'МГУ', 'СПбГУ', 'МФТИ', 'МИФИ', 'МГТУ', 'МАИ',
        'ЛТД', 'ИНК', 'КО', 'ГМБХ', 'АГ', 'СА', 'НВ', 'БВ', 'СЕ',
        'Ко', 'Ltd', 'Inc', 'GmbH', 'AG', 'SA', 'NV', 'BV', 'SE',
    }

    def __init__(self):
        # Инициализация компонентов natasha
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.emb = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(self.emb)
        self.syntax_parser = NewsSyntaxParser(self.emb)
        self.ner_tagger = NewsNERTagger(self.emb)
        self.names_extractor = NamesExtractor(self.morph_vocab)

        # Кэши для производительности
        self.doc_cache = {}
        self.morph_cache = {}

        # Добавляем римские цифры в аббревиатуры
        self.ORG_ABBR.update(self.ROMAN_NUMERALS)

    def get_doc(self, text: str) -> Optional[Doc]:
        """Получение или создание документа с кэшированием"""
        if not text:
            return None

        if text in self.doc_cache:
            return self.doc_cache[text]

        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        doc.parse_syntax(self.syntax_parser)
        doc.tag_ner(self.ner_tagger)

        # Лемматизация
        for token in doc.tokens:
            token.lemmatize(self.morph_vocab)

        for span in doc.spans:
            span.normalize(self.morph_vocab)

        self.doc_cache[text] = doc
        return doc

    def is_roman_numeral(self, text: str) -> bool:
        """Проверка на римскую цифру"""
        if not text:
            return False
        clean_text = text.strip('.,;:!?()').upper()
        return clean_text in self.ROMAN_NUMERALS

    def is_abbr(self, text: str) -> bool:
        """Проверка на аббревиатуру организации"""
        if not text:
            return False
        clean_text = text.strip('.,;:!?()').upper()
        return clean_text in self.ORG_ABBR

    def is_person(self, text: str) -> bool:
        """Определение, является ли текст ФИО человека"""
        if not text or len(text) < 6:
            return False

        # Если есть явные признаки организации
        if any(ind in text for ind in self.ORG_ABBR if len(ind) > 2):
            return False

        org_indicators = ['Общество', 'Компания', 'Корпорация', 'Завод',
                         'Институт', 'Университет', 'Академия', 'Лаборатория',
                         'Фирма', 'Центр']

        if any(ind.lower() in text.lower() for ind in org_indicators):
            return False

        # Проверка через NER
        doc = self.get_doc(text)
        if doc and doc.spans:
            for span in doc.spans:
                if span.type == 'PER':
                    return True

        # Паттерны ФИО
        words = text.split()
        if 2 <= len(words) <= 4:
            name_like = 0
            for word in words:
                clean = word.rstrip('.,')
                if clean and clean[0].isupper() and len(clean) > 1:
                    name_like += 1
            return name_like >= len(words) - 1

        return False

    def extract_person_parts(self, text: str) -> Dict[str, str]:
        """Извлечение частей ФИО с помощью natasha"""
        matches = list(self.names_extractor(text))
        if matches:
            fact = matches[0].fact
            parts = []
            if fact.last:
                parts.append(fact.last)
            if fact.first:
                parts.append(fact.first)
            if fact.middle:
                parts.append(fact.middle)

            return {
                'last': fact.last or '',
                'first': fact.first or '',
                'middle': fact.middle or '',
                'full': ' '.join(parts)
            }

        # Fallback: ручной парсинг
        return self._parse_name_manually(text)

    def _parse_name_manually(self, text: str) -> Dict[str, str]:
        """Ручной парсинг имени"""
        words = text.split()

        if len(words) == 3:
            return {
                'last': words[0],
                'first': words[1],
                'middle': words[2],
                'full': text
            }
        elif len(words) == 2:
            return {
                'last': words[0],
                'first': words[1],
                'middle': '',
                'full': text
            }
        else:
            return {
                'last': text,
                'first': '',
                'middle': '',
                'full': text
            }

    def format_person_name(self, name: str) -> str:
        """Форматирование ФИО человека"""
        if not name:
            return name

        parts = self.extract_person_parts(name)
        if parts.get('full'):
            return parts['full']

        return name


class OrganizationNormalizer:
    """Нормализация названий организаций (только для поиска, не для сохранения)"""

    def __init__(self):
        self.rules_cache = None
        self.processor = RussianTextProcessor()
        self.load_rules()

    def load_rules(self):
        """Загрузка правил из БД"""
        try:
            rules = OrganizationNormalizationRule.objects.all().order_by('priority')
            self.rules_cache = [
                {
                    'original': rule.original_text.lower(),
                    'replacement': rule.replacement_text.lower(),
                    'type': rule.rule_type,
                    'priority': rule.priority
                }
                for rule in rules
            ]
        except Exception as e:
            self.rules_cache = []
            logger.warning(f"Не удалось загрузить правила нормализации: {e}")

    def normalize_for_search(self, name: str) -> Dict[str, Any]:
        """
        Нормализация названия ТОЛЬКО для поиска дубликатов
        Само название остается как в CSV
        """
        if pd.isna(name) or not name:
            return {'normalized': '', 'keywords': [], 'original': name}

        original = str(name).strip()
        name_lower = original.lower()

        # Применяем правила из БД для нормализации
        normalized = name_lower
        if self.rules_cache:
            for rule in self.rules_cache:
                try:
                    if rule['type'] == 'ignore':
                        pattern = r'\b' + re.escape(rule['original']) + r'\b'
                        normalized = re.sub(pattern, '', normalized)
                    else:
                        pattern = r'\b' + re.escape(rule['original']) + r'\b'
                        normalized = re.sub(pattern, rule['replacement'], normalized)
                except Exception:
                    continue

        # Убираем кавычки и знаки препинания для поиска
        normalized = re.sub(r'["\'«»„“”]', '', normalized)
        normalized = re.sub(r'[^\w\s-]', ' ', normalized)
        normalized = ' '.join(normalized.split())

        # Извлекаем ключевые слова для поиска
        keywords = []

        # Слова в кавычках
        quoted = re.findall(r'"([^"]+)"', original)
        for q in quoted:
            words = q.lower().split()
            keywords.extend([w for w in words if len(w) > 3])

        # Аббревиатуры
        abbrs = re.findall(r'\b[А-ЯЁA-Z]{2,}\b', original)
        keywords.extend([a.lower() for a in abbrs if len(a) >= 2])

        # Коды (ИНН, ОГРН и т.д.)
        codes = re.findall(r'\b\d{10,}\b', original)
        keywords.extend(codes)

        return {
            'normalized': normalized,
            'keywords': list(set(keywords)),
            'original': original,
        }

    def format_organization_name(self, name: str) -> str:
        """Возвращает оригинальное название без изменений"""
        return name


class PersonNameFormatter:
    """Форматирование имен людей"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def format(self, name: str) -> str:
        """Форматирование ФИО"""
        return self.processor.format_person_name(name)


class RIDNameFormatter:
    """Форматирование названий РИД"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def format(self, text: str) -> str:
        """Форматирование названия РИД"""
        if not text or not isinstance(text, str):
            return text

        if len(text.strip()) <= 1:
            return text

        # Приводим к нижнему регистру и делаем первую букву заглавной
        words = text.lower().split()
        if words:
            words[0] = words[0][0].upper() + words[0][1:]
        return ' '.join(words)


class EntityTypeDetector:
    """Детектор типов сущностей"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def detect_type(self, text: str) -> str:
        """Определение типа сущности"""
        if self.processor.is_person(text):
            return 'person'
        return 'organization'


class BaseFIPSParser:
    """Базовый класс для всех парсеров каталогов ФИПС"""

    def __init__(self, command):
        self.command = command
        self.stdout = command.stdout
        self.style = command.style

        # Инициализация процессоров
        self.processor = RussianTextProcessor()
        self.org_normalizer = OrganizationNormalizer()
        self.type_detector = EntityTypeDetector()
        self.person_formatter = PersonNameFormatter()
        self.rid_formatter = RIDNameFormatter()

        # Кэши для оптимизации
        self.country_cache = {}
        self.person_cache = {}
        self.organization_cache = {}
        self.foiv_cache = {}
        self.rf_rep_cache = {}
        self.city_cache = {}
        self.activity_type_cache = {}
        self.ceo_position_cache = {}

    def get_ip_type(self):
        """Должен быть переопределен в дочерних классах"""
        raise NotImplementedError

    def get_required_columns(self):
        """Возвращает список обязательных колонок"""
        raise NotImplementedError

    def parse_dataframe(self, df, catalogue):
        """Основной метод парсинга DataFrame"""
        raise NotImplementedError

    def clean_string(self, value):
        """Очистка строкового значения"""
        if pd.isna(value) or value is None:
            return ''
        value = str(value).strip()
        if value in ['', 'None', 'null', 'NULL', 'nan']:
            return ''
        return value

    def parse_date(self, value):
        """Парсинг даты из строки"""
        if pd.isna(value) or not value:
            return None

        date_str = str(value).strip()
        if not date_str:
            return None

        for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except (ValueError, TypeError):
                continue

        try:
            return pd.to_datetime(date_str).date()
        except (ValueError, TypeError):
            return None

    def parse_bool(self, value):
        """Парсинг булевого значения"""
        if pd.isna(value) or not value:
            return False
        value = str(value).lower().strip()
        return value in ['1', 'true', 'yes', 'да', 'действует', 't', '1.0', 'активен']

    def get_or_create_country(self, code):
        """Получение страны по коду"""
        if not code or pd.isna(code):
            return None

        code = str(code).upper().strip()
        if len(code) != 2:
            return None

        if code in self.country_cache:
            return self.country_cache[code]

        try:
            country = Country.objects.filter(code=code).first()
            if country:
                self.country_cache[code] = country
                return country

            country = Country.objects.filter(code_alpha3=code).first()
            if country:
                self.country_cache[code] = country
                return country

            return None

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка поиска страны {code}: {e}"))
            return None

    def parse_authors(self, authors_str):
        """Парсинг строки с авторами"""
        if pd.isna(authors_str) or not authors_str:
            return []

        authors_str = str(authors_str)
        authors_list = re.split(r'[\n,]\s*', authors_str)

        result = []
        for author in authors_list:
            author = author.strip()
            if not author or author == '""' or author == 'null':
                continue

            author = author.strip('"')
            author = re.sub(r'\s*\([A-Z]{2}\)', '', author)
            author = self.person_formatter.format(author)

            parts = author.split()

            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1] if len(parts) > 1 else ''
                middle_name = parts[2] if len(parts) > 2 else ''

                first_name_clean = first_name.replace('.', '')
                middle_name_clean = middle_name.replace('.', '')

                result.append({
                    'last_name': last_name,
                    'first_name': first_name_clean,
                    'middle_name': middle_name_clean,
                    'full_name': author,
                })
            else:
                result.append({
                    'last_name': author,
                    'first_name': '',
                    'middle_name': '',
                    'full_name': author,
                })

        return result

    def parse_patent_holders(self, holders_str):
        """Парсинг строки с патентообладателями"""
        if pd.isna(holders_str) or not holders_str:
            return []

        holders_str = str(holders_str)
        holders_list = re.split(r'[\n]\s*', holders_str)

        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None':
                continue

            holder = re.sub(r'\s*\([A-Z]{2}\)', '', holder)
            result.append(holder)

        return result

    def find_or_create_person(self, person_data):
        """Поиск или создание физического лица"""
        cache_key = f"{person_data['last_name']}|{person_data['first_name']}|{person_data['middle_name']}"

        if cache_key in self.person_cache:
            return self.person_cache[cache_key]

        persons = Person.objects.filter(
            last_name=person_data['last_name'],
            first_name=person_data['first_name']
        )

        if person_data['middle_name']:
            persons = persons.filter(middle_name=person_data['middle_name'])

        if persons.exists():
            person = persons.first()
            self.person_cache[cache_key] = person
            return person

        try:
            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
            new_id = max_id + 1

            if 'full_name' in person_data:
                full_name = person_data['full_name']
            else:
                full_name_parts = [person_data['last_name'], person_data['first_name']]
                if person_data['middle_name']:
                    full_name_parts.append(person_data['middle_name'])
                full_name = ' '.join(full_name_parts)
                full_name = self.person_formatter.format(full_name)

            # Генерируем уникальный slug
            base_slug = slugify(f"{person_data['last_name']} {person_data['first_name']} {person_data['middle_name']}".strip())
            if not base_slug:
                base_slug = 'person'

            unique_slug = base_slug
            counter = 1
            while Person.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            person = Person.objects.create(
                ceo_id=new_id,
                ceo=full_name,
                last_name=person_data['last_name'],
                first_name=person_data['first_name'],
                middle_name=person_data['middle_name'],
                slug=unique_slug
            )
            self.person_cache[cache_key] = person
            return person
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Person: {e}"))
            return None

    def find_or_create_person_from_name(self, full_name):
        """Поиск или создание физического лица по полному имени"""
        if pd.isna(full_name) or not full_name:
            return None

        full_name = str(full_name).strip().strip('"')
        full_name = self.person_formatter.format(full_name)

        if full_name in self.person_cache:
            return self.person_cache[full_name]

        parts = full_name.split()

        if len(parts) >= 2:
            last_name = parts[0]
            first_name = parts[1] if len(parts) > 1 else ''
            middle_name = parts[2] if len(parts) > 2 else ''

            first_name_clean = first_name.replace('.', '')
            middle_name_clean = middle_name.replace('.', '')

            person_data = {
                'last_name': last_name,
                'first_name': first_name_clean,
                'middle_name': middle_name_clean,
                'full_name': full_name,
            }
        else:
            person_data = {
                'last_name': full_name,
                'first_name': '',
                'middle_name': '',
                'full_name': full_name,
            }

        return self.find_or_create_person(person_data)

    def find_similar_organization(self, org_name):
        """Усиленный поиск похожей организации"""
        if pd.isna(org_name) or not org_name:
            return None

        org_name = str(org_name).strip().strip('"')

        # Стратегия 1: Прямое совпадение
        direct_match = Organization.objects.filter(
            models.Q(name=org_name) |
            models.Q(full_name=org_name) |
            models.Q(short_name=org_name)
        ).first()
        if direct_match:
            return direct_match

        # Нормализуем название для поиска
        norm_data = self.org_normalizer.normalize_for_search(org_name)
        normalized = norm_data['normalized']
        keywords = norm_data['keywords']

        # Стратегия 2: Поиск по ключевым словам
        for keyword in keywords:
            if len(keyword) >= 3:
                similar = Organization.objects.filter(
                    models.Q(name__icontains=keyword) |
                    models.Q(full_name__icontains=keyword) |
                    models.Q(short_name__icontains=keyword)
                ).first()
                if similar:
                    return similar

        # Стратегия 3: Поиск по первым 30 символам
        if len(normalized) > 30:
            prefix = normalized[:30]
            similar = Organization.objects.filter(
                models.Q(name__icontains=prefix) |
                models.Q(full_name__icontains=prefix) |
                models.Q(short_name__icontains=prefix)
            ).first()
            if similar:
                return similar

        # Стратегия 4: Поиск по отдельным словам
        words = org_name.split()
        for word in words:
            if len(word) > 4:
                similar = Organization.objects.filter(
                    models.Q(name__icontains=word) |
                    models.Q(full_name__icontains=word)
                ).first()
                if similar:
                    return similar

        return None

    def find_or_create_organization(self, org_name):
        """Поиск или создание организации с сохранением оригинального названия"""
        if pd.isna(org_name) or not org_name:
            return None

        org_name = str(org_name).strip().strip('"')

        if not org_name or org_name == 'null' or org_name == 'None':
            return None

        # Проверяем кэш
        if org_name in self.organization_cache:
            return self.organization_cache[org_name]

        # Ищем похожие
        similar = self.find_similar_organization(org_name)
        if similar:
            self.organization_cache[org_name] = similar
            return similar

        # Не нашли - создаем новую с оригинальным названием
        try:
            max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
            new_id = max_id + 1

            # Генерируем slug из оригинального названия
            base_slug = slugify(org_name[:50])
            if not base_slug:
                base_slug = 'organization'

            unique_slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            # Сохраняем оригинальное название без изменений
            org = Organization.objects.create(
                organization_id=new_id,
                name=org_name,
                full_name=org_name,
                short_name=org_name[:500] if len(org_name) > 500 else org_name,
                slug=unique_slug,
                register_opk=False,
                strategic=False,
            )

            self.organization_cache[org_name] = org
            return org
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Organization: {e}"))
            return None


class InventionParser(BaseFIPSParser):
    """Парсер для изобретений с пакетной обработкой"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='invention').first()

    def get_required_columns(self):
        return ['registration number', 'invention name']

    def _has_data_changed(self, obj, new_data):
        """Проверяет, изменились ли данные"""
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('patent_starting_date', obj.patent_starting_date, new_data['patent_starting_date']),
            ('expiration_date', obj.expiration_date, new_data['expiration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('abstract', obj.abstract, new_data['abstract']),
            ('claims', obj.claims, new_data['claims']),
            ('creation_year', obj.creation_year, new_data['creation_year']),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  🔄 Начинаем парсинг изобретений..."))

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'invention' не найден в БД"))
            stats['errors'] += 1
            return stats

        # Получаем дату загрузки каталога
        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # ШАГ 1: Собираем все регистрационные номера
        self.stdout.write("  📥 Чтение CSV...")
        all_reg_numbers = []
        reg_num_to_row = {}

        with tqdm(total=len(df), desc="     Прогресс", unit=" зап", leave=False) as pbar:
            for idx, row in df.iterrows():
                reg_num = self.clean_string(row.get('registration number'))
                if reg_num:
                    all_reg_numbers.append(reg_num)
                    reg_num_to_row[reg_num] = row
                pbar.update(1)

        self.stdout.write(f"  📊 Всего записей в CSV: {len(all_reg_numbers)}")

        # ШАГ 2: Загружаем существующие записи ПАЧКАМИ
        self.stdout.write("  🔍 Загрузка существующих записей из БД...")
        existing_objects = {}
        batch_size = 500

        with tqdm(total=len(all_reg_numbers), desc="     Загрузка пачками", unit=" зап") as pbar:
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_numbers = all_reg_numbers[i:i+batch_size]

                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj

                pbar.update(len(batch_numbers))

                if (i // batch_size) % 10 == 0:
                    pbar.set_postfix({"найдено": len(existing_objects)})

        self.stdout.write(f"  📊 Найдено в БД: {len(existing_objects)}")

        # ШАГ 3: Подготавливаем данные для пакетной обработки
        self.stdout.write("  🔄 Подготовка данных...")
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        authors_cache = defaultdict(list)
        holders_cache = defaultdict(list)

        with tqdm(total=len(reg_num_to_row), desc="     Обработка записей", unit=" зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    # Проверка по дате
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('invention name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Изобретение №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    patent_starting_date = self.parse_date(row.get('patent starting date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    abstract = self.clean_string(row.get('abstract'))
                    claims = self.clean_string(row.get('claims'))

                    creation_year = None
                    if application_date:
                        creation_year = application_date.year
                    elif registration_date:
                        creation_year = registration_date.year

                    # Подготовка данных
                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type': ip_type,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'patent_starting_date': patent_starting_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'abstract': abstract,
                        'claims': claims,
                        'creation_year': creation_year,
                    }

                    if reg_num in existing_objects:
                        # Проверяем, изменились ли данные
                        existing = existing_objects[reg_num]
                        if self._has_data_changed(existing, obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Сохраняем авторов и правообладателей
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors_cache[reg_num] = self.parse_authors(authors_str)

                    holders_str = row.get('patent holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders_cache[reg_num] = self.parse_patent_holders(holders_str)

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    self.stdout.write(self.style.ERROR(f"\n  ❌ Ошибка подготовки записи {reg_num}: {e}"))
                    logger.error(f"Error preparing invention {reg_num}: {e}", exc_info=True)

                pbar.update(1)
                if pbar.n % 1000 == 0:
                    pbar.set_postfix({
                        "новые": len(to_create),
                        "обнов": len(to_update),
                        "без изм": unchanged_count,
                        "пропущ": len(skipped_by_date)
                    })

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        self.stdout.write(f"     Итого: новых={len(to_create)}, обновление={len(to_update)}, без изменений={unchanged_count}")

        # ШАГ 4: Пакетное создание новых записей
        if to_create and not self.command.dry_run:
            self.stdout.write(f"  📦 Создание {len(to_create)} записей...")
            create_objects = [IPObject(**data) for data in to_create]

            batch_size = 1000
            created_count = 0

            with tqdm(total=len(create_objects), desc="     Создание", unit=" зап") as pbar:
                for i in range(0, len(create_objects), batch_size):
                    batch = create_objects[i:i+batch_size]
                    IPObject.objects.bulk_create(batch, batch_size=batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))
                    pbar.set_postfix({"создано": created_count})

            stats['created'] = created_count

            # Обновляем кэш новыми объектами
            self.stdout.write("     Обновление кэша...")

            with tqdm(total=len(to_create), desc="     Обновление кэша", unit=" зап") as pbar:
                for i in range(0, len(to_create), batch_size):
                    batch_data = to_create[i:i+batch_size]
                    batch_nums = [d['registration_number'] for d in batch_data]

                    for obj in IPObject.objects.filter(
                        registration_number__in=batch_nums,
                        ip_type=ip_type
                    ):
                        existing_objects[obj.registration_number] = obj

                    pbar.update(len(batch_data))

        # ШАГ 5: Пакетное обновление существующих записей
        if to_update and not self.command.dry_run:
            self.stdout.write(f"  📦 Обновление {len(to_update)} записей...")
            updated_count = 0

            with tqdm(total=len(to_update), desc="     Обновление", unit=" зап") as pbar:
                for data in to_update:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []

                    if obj.name != data['name']:
                        obj.name = data['name']
                        update_fields.append('name')

                    if obj.application_date != data['application_date']:
                        obj.application_date = data['application_date']
                        update_fields.append('application_date')

                    if obj.registration_date != data['registration_date']:
                        obj.registration_date = data['registration_date']
                        update_fields.append('registration_date')

                    if obj.patent_starting_date != data['patent_starting_date']:
                        obj.patent_starting_date = data['patent_starting_date']
                        update_fields.append('patent_starting_date')

                    if obj.expiration_date != data['expiration_date']:
                        obj.expiration_date = data['expiration_date']
                        update_fields.append('expiration_date')

                    if obj.actual != data['actual']:
                        obj.actual = data['actual']
                        update_fields.append('actual')

                    if obj.publication_url != data['publication_url']:
                        obj.publication_url = data['publication_url']
                        update_fields.append('publication_url')

                    if obj.abstract != data['abstract']:
                        obj.abstract = data['abstract']
                        update_fields.append('abstract')

                    if obj.claims != data['claims']:
                        obj.claims = data['claims']
                        update_fields.append('claims')

                    if obj.creation_year != data['creation_year']:
                        obj.creation_year = data['creation_year']
                        update_fields.append('creation_year')

                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1

                    pbar.update(1)
                    if pbar.n % 100 == 0:
                        pbar.set_postfix({"обновлено": updated_count})

            stats['updated'] = updated_count
            self.stdout.write(f"     Реально обновлено: {updated_count} из {len(to_update)}")

        # ШАГ 6: Пакетная обработка авторов
        if authors_cache and not self.command.dry_run:
            self.stdout.write(f"  📦 Обработка авторов ({len(authors_cache)} записей)...")
            self._process_authors_batch_with_progress(existing_objects, authors_cache)

        # ШАГ 7: Пакетная обработка патентообладателей
        if holders_cache and not self.command.dry_run:
            self.stdout.write(f"  📦 Обработка патентообладателей ({len(holders_cache)} записей)...")
            self._process_holders_batch_with_progress(existing_objects, holders_cache)

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        self.stdout.write(self.style.SUCCESS(f"  ✅ Парсинг изобретений завершен"))
        self.stdout.write(f"     Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}, "
                         f"Пропущено всего: {stats['skipped']} (из них по дате: {stats['skipped_by_date']}), "
                         f"Ошибок: {stats['errors']}")

        return stats

    def _process_authors_batch_with_progress(self, existing_objects, authors_cache):
        """Обработка авторов с прогресс-баром и разбивкой на пачки"""
        self.stdout.write(f"     ⚡ Обработка авторов...")

        # ШАГ 1: Сбор уникальных авторов
        self.stdout.write("        Шаг 1/6: Сбор уникальных авторов...")
        author_to_key = {}
        total_relations = 0

        for reg_num, authors_data in authors_cache.items():
            ip_object = existing_objects.get(reg_num)
            if not ip_object:
                continue

            for author_data in authors_data:
                key = f"{author_data['last_name']}|{author_data['first_name']}|{author_data['middle_name']}"
                if key not in author_to_key:
                    author_to_key[key] = {
                        'data': author_data,
                        'ip_objects': []
                    }
                author_to_key[key]['ip_objects'].append(ip_object)
                total_relations += 1

        all_keys = list(author_to_key.keys())
        self.stdout.write(f"        Уникальных авторов: {len(all_keys)}, всего связей: {total_relations}")

        # ШАГ 2: Поиск в БД
        self.stdout.write("        Шаг 2/6: Поиск в БД...")
        existing_people = {}
        batch_size = 50

        with tqdm(total=len(all_keys), desc="           Поиск", unit=" ключ") as pbar:
            for i in range(0, len(all_keys), batch_size):
                batch_keys = all_keys[i:i+batch_size]

                name_conditions = models.Q()
                for key in batch_keys:
                    last, first, middle = key.split('|')
                    if middle:
                        name_conditions |= models.Q(
                            last_name=last,
                            first_name=first,
                            middle_name=middle
                        )
                    else:
                        name_conditions |= models.Q(
                            last_name=last,
                            first_name=first,
                            middle_name__isnull=True
                        ) | models.Q(
                            last_name=last,
                            first_name=first,
                            middle_name=''
                        )

                for person in Person.objects.filter(name_conditions):
                    key = f"{person.last_name}|{person.first_name}|{person.middle_name or ''}"
                    existing_people[key] = person
                    self.person_cache[key] = person

                pbar.update(len(batch_keys))
                if (i // batch_size) % 10 == 0:
                    pbar.set_postfix({"найдено": len(existing_people)})

        self.stdout.write(f"        Найдено существующих: {len(existing_people)}")

        # ШАГ 3: Подготовка новых авторов
        self.stdout.write("        Шаг 3/6: Подготовка новых авторов...")
        people_to_create = []
        key_to_new_person = {}

        max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
        next_id = max_id + 1
        existing_slugs = set(Person.objects.values_list('slug', flat=True))

        with tqdm(total=len(all_keys), desc="           Подготовка", unit=" ключ") as pbar:
            for key, info in author_to_key.items():
                if key not in existing_people:
                    author_data = info['data']

                    name_parts = [author_data['last_name'], author_data['first_name']]
                    if author_data['middle_name']:
                        name_parts.append(author_data['middle_name'])

                    base_slug = slugify(' '.join(name_parts).strip())
                    if not base_slug:
                        base_slug = 'person'

                    unique_slug = base_slug
                    counter = 1
                    while unique_slug in existing_slugs or any(p.slug == unique_slug for p in people_to_create):
                        unique_slug = f"{base_slug}-{counter}"
                        counter += 1

                    person = Person(
                        ceo_id=next_id,
                        ceo=author_data['full_name'],
                        last_name=author_data['last_name'],
                        first_name=author_data['first_name'],
                        middle_name=author_data['middle_name'] or '',
                        slug=unique_slug
                    )
                    people_to_create.append(person)
                    key_to_new_person[key] = person
                    next_id += 1
                    existing_slugs.add(unique_slug)

                pbar.update(1)
                if pbar.n % 10000 == 0:
                    pbar.set_postfix({"к созданию": len(people_to_create)})

        self.stdout.write(f"        Новых авторов для создания: {len(people_to_create)}")

        # ШАГ 4: Создание новых авторов
        if people_to_create:
            self.stdout.write(f"        Шаг 4/6: Создание новых авторов...")
            batch_size = 500
            created_count = 0

            with tqdm(total=len(people_to_create), desc="           Создание", unit=" чел") as pbar:
                for i in range(0, len(people_to_create), batch_size):
                    batch = people_to_create[i:i+batch_size]
                    Person.objects.bulk_create(batch, batch_size=batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))
                    pbar.set_postfix({"создано": created_count})

            for person in people_to_create:
                key = f"{person.last_name}|{person.first_name}|{person.middle_name}"
                self.person_cache[key] = person

        # ШАГ 5: Подготовка связей
        self.stdout.write("        Шаг 5/6: Подготовка связей...")
        unique_pairs = set()
        through_objs = []

        for key, info in author_to_key.items():
            person = existing_people.get(key) or key_to_new_person.get(key)
            if not person:
                continue

            unique_ip_objects = {ip.pk: ip for ip in info['ip_objects']}

            for ip_object in unique_ip_objects.values():
                pair = (ip_object.pk, person.pk)
                if pair not in unique_pairs:
                    unique_pairs.add(pair)
                    through_objs.append(
                        IPObject.authors.through(
                            ipobject_id=ip_object.pk,
                            person_id=person.pk
                        )
                    )

        self.stdout.write(f"        Уникальных связей для создания: {len(through_objs)}")

        # ШАГ 6: Создание связей
        if through_objs:
            self.stdout.write(f"        Шаг 6/6: Создание связей...")

            # Получаем все уникальные ID IP-объектов
            ip_ids = list(set(obj.ipobject_id for obj in through_objs))
            self.stdout.write(f"           Удаление старых связей для {len(ip_ids)} IP-объектов...")

            # Удаляем старые связи ПАЧКАМИ по 500 ID
            delete_batch_size = 500
            deleted_total = 0

            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.authors.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted

                if (i // delete_batch_size) % 10 == 0:
                    self.stdout.write(f"              Удалено {deleted_total} связей...")

            self.stdout.write(f"           Удалено старых связей: {deleted_total}")

            # Создаем новые связи пачками
            create_batch_size = 1000
            created_count = 0

            with tqdm(total=len(through_objs), desc="           Добавление", unit=" связь") as pbar:
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.authors.through.objects.bulk_create(batch, batch_size=create_batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))
                    pbar.set_postfix({"создано": created_count})

        self.stdout.write(f"        ✅ Обработка авторов завершена")

    def _process_holders_batch_with_progress(self, existing_objects, holders_cache):
        """Обработка правообладателей с прогресс-баром и разбивкой на пачки"""
        self.stdout.write(f"     ⚡ Обработка правообладателей...")

        # ШАГ 1: Сбор уникальных правообладателей
        self.stdout.write("        Шаг 1/7: Сбор уникальных правообладателей...")
        all_holders = set()
        for holders_list in holders_cache.values():
            all_holders.update(holders_list)

        self.stdout.write(f"        Уникальных правообладателей: {len(all_holders)}")

        # ШАГ 2: Определение типов
        self.stdout.write("        Шаг 2/7: Определение типов...")
        person_holders = []
        org_holders = []

        with tqdm(total=len(all_holders), desc="           Анализ", unit=" об") as pbar:
            for holder in all_holders:
                if self.type_detector.detect_type(holder) == 'person':
                    person_holders.append(holder)
                else:
                    org_holders.append(holder)
                pbar.update(1)

        self.stdout.write(f"        Люди: {len(person_holders)}, Организации: {len(org_holders)}")

        # ШАГ 3: Обработка организаций (ЧАСТЯМИ)
        self.stdout.write("        Шаг 3/7: Обработка организаций...")
        org_map = {}

        if org_holders:
            CHUNK_SIZE = 1000
            total_orgs = len(org_holders)

            self.stdout.write(f"        Обработка {total_orgs} организаций частями по {CHUNK_SIZE}...")

            for chunk_start in range(0, total_orgs, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, total_orgs)
                chunk_holders = org_holders[chunk_start:chunk_end]

                # Поиск существующих в этой части
                existing_orgs = {}
                for org in Organization.objects.filter(name__in=chunk_holders):
                    existing_orgs[org.name] = org
                    self.organization_cache[org.name] = org

                # Создание новых в этой части
                orgs_to_create = []
                for holder in chunk_holders:
                    if holder not in existing_orgs and holder not in self.organization_cache:
                        max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
                        new_id = max_id + len(orgs_to_create) + 1

                        base_slug = slugify(holder[:50])
                        if not base_slug:
                            base_slug = 'organization'

                        unique_slug = base_slug
                        counter = 1
                        while Organization.objects.filter(slug=unique_slug).exists() or any(o.slug == unique_slug for o in orgs_to_create):
                            unique_slug = f"{base_slug}-{counter}"
                            counter += 1

                        org = Organization(
                            organization_id=new_id,
                            name=holder,
                            full_name=holder,
                            short_name=holder[:500] if len(holder) > 500 else holder,
                            slug=unique_slug,
                            register_opk=False,
                            strategic=False,
                        )
                        orgs_to_create.append(org)
                        self.organization_cache[holder] = org

                # Мгновенно создаем в БД
                if orgs_to_create:
                    batch_size = 500
                    for i in range(0, len(orgs_to_create), batch_size):
                        batch = orgs_to_create[i:i+batch_size]
                        Organization.objects.bulk_create(batch, batch_size=batch_size)

                # Освобождаем память
                del existing_orgs
                del orgs_to_create

                progress = (chunk_end / total_orgs) * 100
                self.stdout.write(f"           Прогресс: {progress:.1f}%")

            # Финальный маппинг
            for holder in org_holders:
                org_map[holder] = self.organization_cache.get(holder)

        # ШАГ 4: Обработка людей (ЧАСТЯМИ)
        self.stdout.write("        Шаг 4/7: Обработка людей...")
        person_map = {}

        if person_holders:
            CHUNK_SIZE = 500
            total_people = len(person_holders)

            self.stdout.write(f"        Обработка {total_people} людей частями по {CHUNK_SIZE}...")

            for chunk_start in range(0, total_people, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, total_people)
                chunk_holders = person_holders[chunk_start:chunk_end]

                # Поиск существующих
                existing_people = {}
                for holder in chunk_holders:
                    parts = holder.split()
                    if len(parts) >= 2:
                        last_name = parts[0]
                        first_name = parts[1]
                        middle_name = parts[2] if len(parts) > 2 else ''

                        persons = Person.objects.filter(
                            last_name=last_name,
                            first_name=first_name
                        )
                        if middle_name:
                            persons = persons.filter(middle_name=middle_name)

                        person = persons.first()
                        if person:
                            existing_people[holder] = person
                            self.person_cache[holder] = person

                # Создание новых
                people_to_create = []
                for holder in chunk_holders:
                    if holder not in existing_people and holder not in self.person_cache:
                        parts = holder.split()
                        if len(parts) >= 2:
                            last_name = parts[0]
                            first_name = parts[1]
                            middle_name = parts[2] if len(parts) > 2 else ''

                            name_parts = [last_name, first_name]
                            if middle_name:
                                name_parts.append(middle_name)

                            base_slug = slugify(' '.join(name_parts))
                            if not base_slug:
                                base_slug = 'person'

                            unique_slug = base_slug
                            counter = 1
                            while Person.objects.filter(slug=unique_slug).exists() or any(p.slug == unique_slug for p in people_to_create):
                                unique_slug = f"{base_slug}-{counter}"
                                counter += 1

                            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
                            new_id = max_id + len(people_to_create) + 1

                            person = Person(
                                ceo_id=new_id,
                                ceo=holder,
                                last_name=last_name,
                                first_name=first_name,
                                middle_name=middle_name or '',
                                slug=unique_slug
                            )
                            people_to_create.append(person)
                            self.person_cache[holder] = person

                # Мгновенно создаем в БД
                if people_to_create:
                    batch_size = 500
                    for i in range(0, len(people_to_create), batch_size):
                        batch = people_to_create[i:i+batch_size]
                        Person.objects.bulk_create(batch, batch_size=batch_size)

                # Освобождаем память
                del existing_people
                del people_to_create

                progress = (chunk_end / total_people) * 100
                self.stdout.write(f"           Прогресс: {progress:.1f}%")

            # Финальный маппинг
            for holder in person_holders:
                person_map[holder] = self.person_cache.get(holder)

        # ШАГ 5: Подготовка связей
        self.stdout.write("        Шаг 5/7: Подготовка связей...")

        org_relations = set()
        person_relations = set()

        with tqdm(total=sum(len(h) for h in holders_cache.values()), desc="           Сбор связей", unit=" св") as pbar:
            for reg_num, holders_list in holders_cache.items():
                ip_object = existing_objects.get(reg_num)
                if not ip_object:
                    continue

                for holder in holders_list:
                    if holder in org_map and org_map[holder]:
                        org_relations.add((ip_object.pk, org_map[holder].pk))
                    elif holder in person_map and person_map[holder]:
                        person_relations.add((ip_object.pk, person_map[holder].pk))
                    pbar.update(1)

        self.stdout.write(f"        Уникальных связей с организациями: {len(org_relations)}")
        self.stdout.write(f"        Уникальных связей с людьми: {len(person_relations)}")

        # ШАГ 6: Создание связей с организациями
        if org_relations:
            self.stdout.write("        Шаг 6/7: Создание связей с организациями...")

            ip_ids = list(set(ip_id for ip_id, _ in org_relations))

            # Удаляем старые связи ПАЧКАМИ
            delete_batch_size = 500
            deleted_total = 0
            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.owner_organizations.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted
                if (i // delete_batch_size) % 10 == 0:
                    self.stdout.write(f"              Удалено {deleted_total} связей с организациями...")

            self.stdout.write(f"           Удалено старых связей: {deleted_total}")

            # Создаем новые связи пачками
            through_objs = [
                IPObject.owner_organizations.through(
                    ipobject_id=ip_id,
                    organization_id=org_id
                )
                for ip_id, org_id in org_relations
            ]

            create_batch_size = 1000
            created_count = 0
            with tqdm(total=len(through_objs), desc="           Добавление", unit=" св") as pbar:
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.owner_organizations.through.objects.bulk_create(batch, batch_size=create_batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))

        # ШАГ 7: Создание связей с людьми
        if person_relations:
            self.stdout.write("        Шаг 7/7: Создание связей с людьми...")

            ip_ids = list(set(ip_id for ip_id, _ in person_relations))

            # Удаляем старые связи ПАЧКАМИ
            delete_batch_size = 500
            deleted_total = 0
            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.owner_persons.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted
                if (i // delete_batch_size) % 10 == 0:
                    self.stdout.write(f"              Удалено {deleted_total} связей с людьми...")

            self.stdout.write(f"           Удалено старых связей: {deleted_total}")

            # Создаем новые связи пачками
            through_objs = [
                IPObject.owner_persons.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in person_relations
            ]

            create_batch_size = 1000
            created_count = 0
            with tqdm(total=len(through_objs), desc="           Добавление", unit=" св") as pbar:
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.owner_persons.through.objects.bulk_create(batch, batch_size=create_batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))

        self.stdout.write(f"        ✅ Обработка правообладателей завершена")


class UtilityModelParser(BaseFIPSParser):
    """Парсер для полезных моделей"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='utility-model').first()

    def get_required_columns(self):
        return ['registration number', 'utility model name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер полезных моделей готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class IndustrialDesignParser(BaseFIPSParser):
    """Парсер для промышленных образцов"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='industrial-design').first()

    def get_required_columns(self):
        return ['registration number', 'industrial design name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер промышленных образцов готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class IntegratedCircuitTopologyParser(BaseFIPSParser):
    """Парсер для топологий интегральных микросхем"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='integrated-circuit-topology').first()

    def get_required_columns(self):
        return ['registration number', 'microchip name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер топологий микросхем готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class ComputerProgramParser(BaseFIPSParser):
    """Парсер для программ для ЭВМ"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='computer-program').first()

    def get_required_columns(self):
        return ['registration number', 'program name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер программ для ЭВМ готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class DatabaseParser(BaseFIPSParser):
    """Парсер для баз данных"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='database').first()

    def get_required_columns(self):
        return ['registration number', 'db name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер баз данных готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class Command(BaseCommand):
    help = 'Парсинг каталогов открытых данных ФИПС Роспатента'

    def add_arguments(self, parser):
        parser.add_argument('--catalogue-id', type=int, help='ID конкретного каталога для парсинга')
        parser.add_argument('--ip-type', type=str,
                        choices=['invention', 'utility-model', 'industrial-design',
                                'integrated-circuit-topology', 'computer-program', 'database'],
                        help='Тип РИД для парсинга (если не указан, парсятся все)')
        parser.add_argument('--dry-run', action='store_true', help='Режим проверки без сохранения в БД')
        parser.add_argument('--encoding', type=str, default='utf-8', help='Кодировка CSV файла')
        parser.add_argument('--delimiter', type=str, default=',', help='Разделитель в CSV файле')
        parser.add_argument('--batch-size', type=int, default=100, help='Размер пакета для bulk-операций')
        parser.add_argument('--min-year', type=int, default=2000, help='Минимальный год регистрации для фильтрации')
        parser.add_argument('--skip-filters', action='store_true', help='Пропустить фильтрацию (обработать все записи)')
        parser.add_argument('--only-active', action='store_true', help='Парсить только активные патенты (actual = True)')
        parser.add_argument('--max-rows', type=int, help='Максимальное количество строк для обработки (для тестирования)')
        parser.add_argument('--force', action='store_true', help='Принудительный парсинг даже если каталог уже обработан')
        parser.add_argument('--mark-processed', action='store_true',
                        help='Пометить каталог как обработанный (даже если были ошибки)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parsers = {
            'invention': InventionParser(self),
            'utility-model': UtilityModelParser(self),
            'industrial-design': IndustrialDesignParser(self),
            'integrated-circuit-topology': IntegratedCircuitTopologyParser(self),
            'computer-program': ComputerProgramParser(self),
            'database': DatabaseParser(self),
        }

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.encoding = options['encoding']
        self.delimiter = options['delimiter']
        self.batch_size = options['batch_size']
        self.min_year = options['min_year']
        self.skip_filters = options['skip_filters']
        self.only_active = options['only_active']
        self.max_rows = options.get('max_rows')
        self.force = options.get('force', False)
        self.mark_processed = options.get('mark_processed', False)

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД\n"))

        if self.only_active:
            self.stdout.write(self.style.WARNING("📌 Режим: парсинг только активных записей (actual = True)"))

        if self.force:
            self.stdout.write(self.style.WARNING("⚠️  Режим: принудительный парсинг (игнорирование даты обработки)"))

        catalogues = self.get_catalogues(options.get('catalogue_id'), options.get('ip_type'))

        if not catalogues:
            raise CommandError('Не найдены каталоги для парсинга')

        total_stats = {
            'catalogues': len(catalogues),
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        for catalogue in catalogues:
            self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
            self.stdout.write(self.style.SUCCESS(f"📁 Обработка каталога: {catalogue.name}"))
            self.stdout.write(self.style.SUCCESS(f"   ID: {catalogue.id}, Тип: {catalogue.ip_type.name if catalogue.ip_type else 'Неизвестно'}"))
            self.stdout.write(self.style.SUCCESS(f"{'='*60}"))

            stats = self.process_catalogue(catalogue)

            for key in ['processed', 'created', 'updated', 'skipped', 'errors']:
                total_stats[key] += stats.get(key, 0)
            total_stats['skipped_by_date'] += stats.get('skipped_by_date', 0)

        self.print_final_stats(total_stats)

    def get_catalogues(self, catalogue_id=None, ip_type_slug=None):
        queryset = FipsOpenDataCatalogue.objects.all()

        if catalogue_id:
            queryset = queryset.filter(id=catalogue_id)
        elif ip_type_slug:
            queryset = queryset.filter(ip_type__slug=ip_type_slug)
        else:
            queryset = queryset.exclude(catalogue_file='')

        return queryset.order_by('ip_type__id', '-publication_date')

    def process_catalogue(self, catalogue):
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        if not catalogue.catalogue_file:
            self.stdout.write(self.style.ERROR(f"  ❌ У каталога ID={catalogue.id} не загружен файл"))
            stats['errors'] += 1
            return stats

        if not self.force and hasattr(catalogue, 'parsed_date') and catalogue.parsed_date:
            self.stdout.write(self.style.WARNING(
                f"  ⚠️ Каталог уже был обработан {catalogue.parsed_date.strftime('%d.%m.%Y %H:%M')}"
            ))
            self.stdout.write(self.style.WARNING(f"     Используйте --force для повторного парсинга"))
            stats['skipped'] += 1
            return stats

        ip_type_slug = catalogue.ip_type.slug if catalogue.ip_type else None

        if ip_type_slug not in self.parsers:
            self.stdout.write(self.style.ERROR(f"  ❌ Нет парсера для типа РИД: {ip_type_slug}"))
            stats['errors'] += 1
            return stats

        parser = self.parsers[ip_type_slug]
        df = self.load_csv(catalogue)

        if df is None or df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Файл пуст или не удалось загрузить"))
            stats['skipped'] += 1
            return stats

        self.stdout.write(f"  📊 Загружено записей: {len(df)}")

        missing_columns = self.check_required_columns(df, parser.get_required_columns())
        if missing_columns:
            self.stdout.write(self.style.ERROR(f"  ❌ Отсутствуют обязательные колонки: {missing_columns}"))
            stats['errors'] += 1
            return stats

        if not self.skip_filters:
            df = self.apply_filters(df)

        if df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Нет данных после фильтрации"))
            stats['skipped'] += 1
            return stats

        self.stdout.write(f"  📊 После фильтрации: {len(df)} записей")

        if self.max_rows and len(df) > self.max_rows:
            df = df.head(self.max_rows)
            self.stdout.write(self.style.WARNING(f"  ⚠️ Ограничено до {self.max_rows} записей"))

        try:
            parser_stats = parser.parse_dataframe(df, catalogue)
            stats.update(parser_stats)

            if not self.dry_run and hasattr(catalogue, 'parsed_date'):
                if stats['errors'] == 0 or self.mark_processed:
                    catalogue.parsed_date = timezone.now()
                    catalogue.save(update_fields=['parsed_date'])
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Каталог помечен как обработанный"))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠️ Каталог не помечен как обработанный из-за ошибок"
                    ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка при парсинге: {e}"))
            logger.error(f"Error parsing catalogue {catalogue.id}: {e}", exc_info=True)
            stats['errors'] += 1

        return stats

    def load_csv(self, catalogue):
        file_path = catalogue.catalogue_file.path

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"  ❌ Файл не найден: {file_path}"))
            return None

        try:
            strategies = [
                {'encoding': self.encoding, 'delimiter': self.delimiter, 'skipinitialspace': True},
                {'encoding': 'cp1251', 'delimiter': self.delimiter, 'skipinitialspace': True},
                {'encoding': 'utf-8', 'delimiter': ';', 'skipinitialspace': True},
                {'encoding': 'cp1251', 'delimiter': ';', 'skipinitialspace': True},
                {'encoding': 'utf-8', 'delimiter': '\t', 'skipinitialspace': True},
            ]

            for strategy in strategies:
                try:
                    df = pd.read_csv(file_path, **strategy, dtype=str, keep_default_na=False)
                    self.stdout.write(f"  ✅ Успешно загружено с параметрами: {strategy}")

                    df.columns = [col.strip().strip('\ufeff').strip('"') for col in df.columns]

                    return df
                except Exception as e:
                    continue

            raise Exception("Не удалось загрузить CSV ни одной стратегией")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка загрузки CSV: {e}"))
            return None

    def check_required_columns(self, df, required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        return missing

    def apply_filters(self, df):
        original_count = len(df)

        if 'registration date' in df.columns:
            df = self.filter_by_registration_year(df)

        if self.only_active and 'actual' in df.columns:
            df = self.filter_by_actual(df)

        filtered_count = len(df)
        if filtered_count < original_count:
            self.stdout.write(f"  🔍 Фильтрация: {original_count} → {filtered_count} записей")

        return df

    def filter_by_registration_year(self, df):
        def extract_year(date_str):
            try:
                if pd.isna(date_str) or not date_str:
                    return None

                date_str = str(date_str).strip()
                if not date_str:
                    return None

                for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                    try:
                        return datetime.strptime(date_str, fmt).year
                    except (ValueError, TypeError):
                        continue

                try:
                    return pd.to_datetime(date_str).year
                except (ValueError, TypeError):
                    return None
            except:
                return None

        self.stdout.write("  🔍 Фильтрация по году регистрации...")
        df['_year'] = df['registration date'].apply(extract_year)

        years_dist = df['_year'].value_counts().sort_index()
        years_list = list(years_dist.items())
        if len(years_list) > 0:
            self.stdout.write(f"     Диапазон годов: {years_list[0][0]:.0f} - {years_list[-1][0]:.0f}")
            self.stdout.write(f"     Первые 5: {years_list[:5]}")
            self.stdout.write(f"     Последние 5: {years_list[-5:]}")

        filtered_df = df[df['_year'] >= self.min_year].copy()
        filtered_df.drop('_year', axis=1, inplace=True)

        return filtered_df

    def filter_by_actual(self, df):
        def parse_actual(value):
            if pd.isna(value) or not value:
                return False
            value = str(value).lower().strip()
            return value in ['1', 'true', 'yes', 'да', 'действует', 't', '1.0', 'активен']

        df['_actual'] = df['actual'].apply(parse_actual)
        filtered_df = df[df['_actual'] == True].copy()
        filtered_df.drop('_actual', axis=1, inplace=True)

        return filtered_df

    def print_final_stats(self, stats):
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("📊 ИТОГОВАЯ СТАТИСТИКА"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
        self.stdout.write(f"📁 Обработано каталогов: {stats['catalogues']}")
        self.stdout.write(f"📝 Всего записей обработано: {stats['processed']}")
        self.stdout.write(f"✅ Создано: {stats['created']}")
        self.stdout.write(f"🔄 Обновлено: {stats['updated']}")
        self.stdout.write(f"⏭️  Пропущено всего: {stats['skipped']}")
        self.stdout.write(f"   └─ по дате обновления: {stats.get('skipped_by_date', 0)}")

        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Ошибок: {stats['errors']}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Ошибок: {stats['errors']}"))

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены в БД"))

        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))

```


-----

# Файл: management\commands\__init__.py

```

```


-----

# Файл: management\parsers\base.py

```
"""
Базовый класс для всех парсеров каталогов ФИПС
"""

import logging
import re
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Set
from collections import defaultdict

from django.db import models
from django.utils.text import slugify
import pandas as pd

from intellectual_property.models import IPObject, IPType
from core.models import Person, Organization, Country

# Исправляем импорты процессоров
from .processors import (
    RussianTextProcessor,
    OrganizationNormalizer,
    PersonNameFormatter,
    RIDNameFormatter,
    EntityTypeDetector
)

logger = logging.getLogger(__name__)


class BaseFIPSParser:
    """Базовый класс для всех парсеров каталогов ФИПС"""

    def __init__(self, command):
        self.command = command
        self.stdout = command.stdout
        self.style = command.style

        # Инициализация процессоров
        self.processor = RussianTextProcessor()
        self.org_normalizer = OrganizationNormalizer()
        self.type_detector = EntityTypeDetector()
        self.person_formatter = PersonNameFormatter()
        self.rid_formatter = RIDNameFormatter()

        # Кэши для оптимизации
        self.country_cache = {}
        self.person_cache = {}
        self.organization_cache = {}
        self.foiv_cache = {}
        self.rf_rep_cache = {}
        self.city_cache = {}
        self.activity_type_cache = {}
        self.ceo_position_cache = {}

    def get_ip_type(self):
        """Должен быть переопределен в дочерних классах"""
        raise NotImplementedError

    def get_required_columns(self):
        """Возвращает список обязательных колонок"""
        raise NotImplementedError

    def parse_dataframe(self, df, catalogue):
        """Основной метод парсинга DataFrame"""
        raise NotImplementedError

    def clean_string(self, value):
        """Очистка строкового значения"""
        if pd.isna(value) or value is None:
            return ''
        value = str(value).strip()
        if value in ['', 'None', 'null', 'NULL', 'nan']:
            return ''
        return value

    def parse_date(self, value):
        """Парсинг даты из строки"""
        if pd.isna(value) or not value:
            return None

        date_str = str(value).strip()
        if not date_str:
            return None

        for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except (ValueError, TypeError):
                continue

        try:
            return pd.to_datetime(date_str).date()
        except (ValueError, TypeError):
            return None

    def parse_bool(self, value):
        """Парсинг булевого значения"""
        if pd.isna(value) or not value:
            return False
        value = str(value).lower().strip()
        return value in ['1', 'true', 'yes', 'да', 'действует', 't', '1.0', 'активен']

    def get_or_create_country(self, code):
        """Получение страны по коду"""
        if not code or pd.isna(code):
            return None

        code = str(code).upper().strip()
        if len(code) != 2:
            return None

        if code in self.country_cache:
            return self.country_cache[code]

        try:
            country = Country.objects.filter(code=code).first()
            if country:
                self.country_cache[code] = country
                return country

            country = Country.objects.filter(code_alpha3=code).first()
            if country:
                self.country_cache[code] = country
                return country

            return None

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка поиска страны {code}: {e}"))
            return None

    def parse_authors(self, authors_str):
        """Парсинг строки с авторами"""
        if pd.isna(authors_str) or not authors_str:
            return []

        authors_str = str(authors_str)
        authors_list = re.split(r'[\n,]\s*', authors_str)

        result = []
        for author in authors_list:
            author = author.strip()
            if not author or author == '""' or author == 'null':
                continue

            author = author.strip('"')
            author = re.sub(r'\s*\([A-Z]{2}\)', '', author)
            author = self.person_formatter.format(author)

            parts = author.split()

            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1] if len(parts) > 1 else ''
                middle_name = parts[2] if len(parts) > 2 else ''

                first_name_clean = first_name.replace('.', '')
                middle_name_clean = middle_name.replace('.', '')

                result.append({
                    'last_name': last_name,
                    'first_name': first_name_clean,
                    'middle_name': middle_name_clean,
                    'full_name': author,
                })
            else:
                result.append({
                    'last_name': author,
                    'first_name': '',
                    'middle_name': '',
                    'full_name': author,
                })

        return result

    def parse_patent_holders(self, holders_str):
        """Парсинг строки с патентообладателями"""
        if pd.isna(holders_str) or not holders_str:
            return []

        holders_str = str(holders_str)
        holders_list = re.split(r'[\n]\s*', holders_str)

        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None':
                continue

            holder = re.sub(r'\s*\([A-Z]{2}\)', '', holder)
            result.append(holder)

        return result

    def find_or_create_person(self, person_data):
        """Поиск или создание физического лица"""
        cache_key = f"{person_data['last_name']}|{person_data['first_name']}|{person_data['middle_name']}"

        if cache_key in self.person_cache:
            return self.person_cache[cache_key]

        persons = Person.objects.filter(
            last_name=person_data['last_name'],
            first_name=person_data['first_name']
        )

        if person_data['middle_name']:
            persons = persons.filter(middle_name=person_data['middle_name'])

        if persons.exists():
            person = persons.first()
            self.person_cache[cache_key] = person
            return person

        try:
            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
            new_id = max_id + 1

            if 'full_name' in person_data:
                full_name = person_data['full_name']
            else:
                full_name_parts = [person_data['last_name'], person_data['first_name']]
                if person_data['middle_name']:
                    full_name_parts.append(person_data['middle_name'])
                full_name = ' '.join(full_name_parts)
                full_name = self.person_formatter.format(full_name)

            # Генерируем уникальный slug
            base_slug = slugify(f"{person_data['last_name']} {person_data['first_name']} {person_data['middle_name']}".strip())
            if not base_slug:
                base_slug = 'person'

            unique_slug = base_slug
            counter = 1
            while Person.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            person = Person.objects.create(
                ceo_id=new_id,
                ceo=full_name,
                last_name=person_data['last_name'],
                first_name=person_data['first_name'],
                middle_name=person_data['middle_name'],
                slug=unique_slug
            )
            self.person_cache[cache_key] = person
            return person
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Person: {e}"))
            return None

    def find_or_create_person_from_name(self, full_name):
        """Поиск или создание физического лица по полному имени"""
        if pd.isna(full_name) or not full_name:
            return None

        full_name = str(full_name).strip().strip('"')
        full_name = self.person_formatter.format(full_name)

        if full_name in self.person_cache:
            return self.person_cache[full_name]

        parts = full_name.split()

        if len(parts) >= 2:
            last_name = parts[0]
            first_name = parts[1] if len(parts) > 1 else ''
            middle_name = parts[2] if len(parts) > 2 else ''

            first_name_clean = first_name.replace('.', '')
            middle_name_clean = middle_name.replace('.', '')

            person_data = {
                'last_name': last_name,
                'first_name': first_name_clean,
                'middle_name': middle_name_clean,
                'full_name': full_name,
            }
        else:
            person_data = {
                'last_name': full_name,
                'first_name': '',
                'middle_name': '',
                'full_name': full_name,
            }

        return self.find_or_create_person(person_data)

    def find_similar_organization(self, org_name):
        """Усиленный поиск похожей организации"""
        if pd.isna(org_name) or not org_name:
            return None

        org_name = str(org_name).strip().strip('"')

        # Стратегия 1: Прямое совпадение
        direct_match = Organization.objects.filter(
            models.Q(name=org_name) |
            models.Q(full_name=org_name) |
            models.Q(short_name=org_name)
        ).first()
        if direct_match:
            return direct_match

        # Нормализуем название для поиска
        norm_data = self.org_normalizer.normalize_for_search(org_name)
        normalized = norm_data['normalized']
        keywords = norm_data['keywords']

        # Стратегия 2: Поиск по ключевым словам
        for keyword in keywords:
            if len(keyword) >= 3:
                similar = Organization.objects.filter(
                    models.Q(name__icontains=keyword) |
                    models.Q(full_name__icontains=keyword) |
                    models.Q(short_name__icontains=keyword)
                ).first()
                if similar:
                    return similar

        # Стратегия 3: Поиск по первым 30 символам
        if len(normalized) > 30:
            prefix = normalized[:30]
            similar = Organization.objects.filter(
                models.Q(name__icontains=prefix) |
                models.Q(full_name__icontains=prefix) |
                models.Q(short_name__icontains=prefix)
            ).first()
            if similar:
                return similar

        # Стратегия 4: Поиск по отдельным словам
        words = org_name.split()
        for word in words:
            if len(word) > 4:
                similar = Organization.objects.filter(
                    models.Q(name__icontains=word) |
                    models.Q(full_name__icontains=word)
                ).first()
                if similar:
                    return similar

        return None

    def find_or_create_organization(self, org_name):
        """Поиск или создание организации с сохранением оригинального названия"""
        if pd.isna(org_name) or not org_name:
            return None

        org_name = str(org_name).strip().strip('"')

        if not org_name or org_name == 'null' or org_name == 'None':
            return None

        # Проверяем кэш
        if org_name in self.organization_cache:
            return self.organization_cache[org_name]

        # Ищем похожие
        similar = self.find_similar_organization(org_name)
        if similar:
            self.organization_cache[org_name] = similar
            return similar

        # Не нашли - создаем новую с оригинальным названием
        try:
            max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
            new_id = max_id + 1

            # Генерируем slug из оригинального названия
            base_slug = slugify(org_name[:50])
            if not base_slug:
                base_slug = 'organization'

            unique_slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            # Сохраняем оригинальное название без изменений
            org = Organization.objects.create(
                organization_id=new_id,
                name=org_name,
                full_name=org_name,
                short_name=org_name[:500] if len(org_name) > 500 else org_name,
                slug=unique_slug,
                register_opk=False,
                strategic=False,
            )

            self.organization_cache[org_name] = org
            return org
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания Organization: {e}"))
            return None

```


-----

# Файл: management\parsers\computer_program.py

```
"""
Парсер для программ для ЭВМ
"""

from intellectual_property.models import IPType
from .base import BaseFIPSParser


class ComputerProgramParser(BaseFIPSParser):
    """Парсер для программ для ЭВМ"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='computer-program').first()

    def get_required_columns(self):
        return ['registration number', 'program name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер программ для ЭВМ готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

```


-----

# Файл: management\parsers\database.py

```
"""
Парсер для баз данных
"""

from intellectual_property.models import IPType
from .base import BaseFIPSParser


class DatabaseParser(BaseFIPSParser):
    """Парсер для баз данных"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='database').first()

    def get_required_columns(self):
        return ['registration number', 'db name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер баз данных готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

```


-----

# Файл: management\parsers\industrial_design.py

```
"""
Парсер для промышленных образцов
"""

from intellectual_property.models import IPType
from .base import BaseFIPSParser


class IndustrialDesignParser(BaseFIPSParser):
    """Парсер для промышленных образцов"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='industrial-design').first()

    def get_required_columns(self):
        return ['registration number', 'industrial design name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер промышленных образцов готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

```


-----

# Файл: management\parsers\integrated_circuit.py

```
"""
Парсер для топологий интегральных микросхем
"""

from intellectual_property.models import IPType
from .base import BaseFIPSParser


class IntegratedCircuitTopologyParser(BaseFIPSParser):
    """Парсер для топологий интегральных микросхем"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='integrated-circuit-topology').first()

    def get_required_columns(self):
        return ['registration number', 'microchip name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер топологий микросхем готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

```


-----

# Файл: management\parsers\invention.py

```
"""
Парсер для изобретений с пакетной обработкой
"""

import logging
from collections import defaultdict

from django.db import models
from django.utils.text import slugify
from tqdm import tqdm
import pandas as pd

# Добавляем недостающие импорты
from intellectual_property.models import IPObject, IPType, Person
from core.models import Organization  # <-- Добавлен этот импорт
from .base import BaseFIPSParser

logger = logging.getLogger(__name__)


class InventionParser(BaseFIPSParser):
    """Парсер для изобретений с пакетной обработкой"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='invention').first()

    def get_required_columns(self):
        return ['registration number', 'invention name']

    def _has_data_changed(self, obj, new_data):
        """Проверяет, изменились ли данные"""
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('patent_starting_date', obj.patent_starting_date, new_data['patent_starting_date']),
            ('expiration_date', obj.expiration_date, new_data['expiration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('abstract', obj.abstract, new_data['abstract']),
            ('claims', obj.claims, new_data['claims']),
            ('creation_year', obj.creation_year, new_data['creation_year']),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  🔄 Начинаем парсинг изобретений..."))

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'invention' не найден в БД"))
            stats['errors'] += 1
            return stats

        # Получаем дату загрузки каталога
        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # ШАГ 1: Собираем все регистрационные номера
        self.stdout.write("  📥 Чтение CSV...")
        all_reg_numbers = []
        reg_num_to_row = {}

        with tqdm(total=len(df), desc="     Прогресс", unit=" зап", leave=False) as pbar:
            for idx, row in df.iterrows():
                reg_num = self.clean_string(row.get('registration number'))
                if reg_num:
                    all_reg_numbers.append(reg_num)
                    reg_num_to_row[reg_num] = row
                pbar.update(1)

        self.stdout.write(f"  📊 Всего записей в CSV: {len(all_reg_numbers)}")

        # ШАГ 2: Загружаем существующие записи ПАЧКАМИ
        self.stdout.write("  🔍 Загрузка существующих записей из БД...")
        existing_objects = {}
        batch_size = 500

        with tqdm(total=len(all_reg_numbers), desc="     Загрузка пачками", unit=" зап") as pbar:
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_numbers = all_reg_numbers[i:i+batch_size]

                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj

                pbar.update(len(batch_numbers))

                if (i // batch_size) % 10 == 0:
                    pbar.set_postfix({"найдено": len(existing_objects)})

        self.stdout.write(f"  📊 Найдено в БД: {len(existing_objects)}")

        # ШАГ 3: Подготавливаем данные для пакетной обработки
        self.stdout.write("  🔄 Подготовка данных...")
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        authors_cache = defaultdict(list)
        holders_cache = defaultdict(list)

        with tqdm(total=len(reg_num_to_row), desc="     Обработка записей", unit=" зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    # Проверка по дате
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('invention name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Изобретение №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    patent_starting_date = self.parse_date(row.get('patent starting date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    abstract = self.clean_string(row.get('abstract'))
                    claims = self.clean_string(row.get('claims'))

                    creation_year = None
                    if application_date:
                        creation_year = application_date.year
                    elif registration_date:
                        creation_year = registration_date.year

                    # Подготовка данных
                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type': ip_type,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'patent_starting_date': patent_starting_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'abstract': abstract,
                        'claims': claims,
                        'creation_year': creation_year,
                    }

                    if reg_num in existing_objects:
                        # Проверяем, изменились ли данные
                        existing = existing_objects[reg_num]
                        if self._has_data_changed(existing, obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Сохраняем авторов и правообладателей
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors_cache[reg_num] = self.parse_authors(authors_str)

                    holders_str = row.get('patent holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders_cache[reg_num] = self.parse_patent_holders(holders_str)

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    self.stdout.write(self.style.ERROR(f"\n  ❌ Ошибка подготовки записи {reg_num}: {e}"))
                    logger.error(f"Error preparing invention {reg_num}: {e}", exc_info=True)

                pbar.update(1)
                if pbar.n % 1000 == 0:
                    pbar.set_postfix({
                        "новые": len(to_create),
                        "обнов": len(to_update),
                        "без изм": unchanged_count,
                        "пропущ": len(skipped_by_date)
                    })

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        self.stdout.write(f"     Итого: новых={len(to_create)}, обновление={len(to_update)}, без изменений={unchanged_count}")

        # ШАГ 4: Пакетное создание новых записей
        if to_create and not self.command.dry_run:
            self.stdout.write(f"  📦 Создание {len(to_create)} записей...")
            create_objects = [IPObject(**data) for data in to_create]

            batch_size = 1000
            created_count = 0

            with tqdm(total=len(create_objects), desc="     Создание", unit=" зап") as pbar:
                for i in range(0, len(create_objects), batch_size):
                    batch = create_objects[i:i+batch_size]
                    IPObject.objects.bulk_create(batch, batch_size=batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))
                    pbar.set_postfix({"создано": created_count})

            stats['created'] = created_count

            # Обновляем кэш новыми объектами
            self.stdout.write("     Обновление кэша...")

            with tqdm(total=len(to_create), desc="     Обновление кэша", unit=" зап") as pbar:
                for i in range(0, len(to_create), batch_size):
                    batch_data = to_create[i:i+batch_size]
                    batch_nums = [d['registration_number'] for d in batch_data]

                    for obj in IPObject.objects.filter(
                        registration_number__in=batch_nums,
                        ip_type=ip_type
                    ):
                        existing_objects[obj.registration_number] = obj

                    pbar.update(len(batch_data))

        # ШАГ 5: Пакетное обновление существующих записей
        if to_update and not self.command.dry_run:
            self.stdout.write(f"  📦 Обновление {len(to_update)} записей...")
            updated_count = 0

            with tqdm(total=len(to_update), desc="     Обновление", unit=" зап") as pbar:
                for data in to_update:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []

                    if obj.name != data['name']:
                        obj.name = data['name']
                        update_fields.append('name')

                    if obj.application_date != data['application_date']:
                        obj.application_date = data['application_date']
                        update_fields.append('application_date')

                    if obj.registration_date != data['registration_date']:
                        obj.registration_date = data['registration_date']
                        update_fields.append('registration_date')

                    if obj.patent_starting_date != data['patent_starting_date']:
                        obj.patent_starting_date = data['patent_starting_date']
                        update_fields.append('patent_starting_date')

                    if obj.expiration_date != data['expiration_date']:
                        obj.expiration_date = data['expiration_date']
                        update_fields.append('expiration_date')

                    if obj.actual != data['actual']:
                        obj.actual = data['actual']
                        update_fields.append('actual')

                    if obj.publication_url != data['publication_url']:
                        obj.publication_url = data['publication_url']
                        update_fields.append('publication_url')

                    if obj.abstract != data['abstract']:
                        obj.abstract = data['abstract']
                        update_fields.append('abstract')

                    if obj.claims != data['claims']:
                        obj.claims = data['claims']
                        update_fields.append('claims')

                    if obj.creation_year != data['creation_year']:
                        obj.creation_year = data['creation_year']
                        update_fields.append('creation_year')

                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1

                    pbar.update(1)
                    if pbar.n % 100 == 0:
                        pbar.set_postfix({"обновлено": updated_count})

            stats['updated'] = updated_count
            self.stdout.write(f"     Реально обновлено: {updated_count} из {len(to_update)}")

        # ШАГ 6: Пакетная обработка авторов
        if authors_cache and not self.command.dry_run:
            self.stdout.write(f"  📦 Обработка авторов ({len(authors_cache)} записей)...")
            self._process_authors_batch_with_progress(existing_objects, authors_cache)

        # ШАГ 7: Пакетная обработка патентообладателей
        if holders_cache and not self.command.dry_run:
            self.stdout.write(f"  📦 Обработка патентообладателей ({len(holders_cache)} записей)...")
            self._process_holders_batch_with_progress(existing_objects, holders_cache)

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        self.stdout.write(self.style.SUCCESS(f"  ✅ Парсинг изобретений завершен"))
        self.stdout.write(f"     Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}, "
                         f"Пропущено всего: {stats['skipped']} (из них по дате: {stats['skipped_by_date']}), "
                         f"Ошибок: {stats['errors']}")

        return stats

    def _process_authors_batch_with_progress(self, existing_objects, authors_cache):
        """Обработка авторов с прогресс-баром и разбивкой на пачки"""
        self.stdout.write(f"     ⚡ Обработка авторов...")

        # ШАГ 1: Сбор уникальных авторов
        self.stdout.write("        Шаг 1/6: Сбор уникальных авторов...")
        author_to_key = {}
        total_relations = 0

        for reg_num, authors_data in authors_cache.items():
            ip_object = existing_objects.get(reg_num)
            if not ip_object:
                continue

            for author_data in authors_data:
                key = f"{author_data['last_name']}|{author_data['first_name']}|{author_data['middle_name']}"
                if key not in author_to_key:
                    author_to_key[key] = {
                        'data': author_data,
                        'ip_objects': []
                    }
                author_to_key[key]['ip_objects'].append(ip_object)
                total_relations += 1

        all_keys = list(author_to_key.keys())
        self.stdout.write(f"        Уникальных авторов: {len(all_keys)}, всего связей: {total_relations}")

        # ШАГ 2: Поиск в БД
        self.stdout.write("        Шаг 2/6: Поиск в БД...")
        existing_people = {}
        batch_size = 50

        with tqdm(total=len(all_keys), desc="           Поиск", unit=" ключ") as pbar:
            for i in range(0, len(all_keys), batch_size):
                batch_keys = all_keys[i:i+batch_size]

                name_conditions = models.Q()
                for key in batch_keys:
                    last, first, middle = key.split('|')
                    if middle:
                        name_conditions |= models.Q(
                            last_name=last,
                            first_name=first,
                            middle_name=middle
                        )
                    else:
                        name_conditions |= models.Q(
                            last_name=last,
                            first_name=first,
                            middle_name__isnull=True
                        ) | models.Q(
                            last_name=last,
                            first_name=first,
                            middle_name=''
                        )

                for person in Person.objects.filter(name_conditions):
                    key = f"{person.last_name}|{person.first_name}|{person.middle_name or ''}"
                    existing_people[key] = person
                    self.person_cache[key] = person

                pbar.update(len(batch_keys))
                if (i // batch_size) % 10 == 0:
                    pbar.set_postfix({"найдено": len(existing_people)})

        self.stdout.write(f"        Найдено существующих: {len(existing_people)}")

        # ШАГ 3: Подготовка новых авторов
        self.stdout.write("        Шаг 3/6: Подготовка новых авторов...")
        people_to_create = []
        key_to_new_person = {}

        max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
        next_id = max_id + 1
        existing_slugs = set(Person.objects.values_list('slug', flat=True))

        with tqdm(total=len(all_keys), desc="           Подготовка", unit=" ключ") as pbar:
            for key, info in author_to_key.items():
                if key not in existing_people:
                    author_data = info['data']

                    name_parts = [author_data['last_name'], author_data['first_name']]
                    if author_data['middle_name']:
                        name_parts.append(author_data['middle_name'])

                    base_slug = slugify(' '.join(name_parts).strip())
                    if not base_slug:
                        base_slug = 'person'

                    unique_slug = base_slug
                    counter = 1
                    while unique_slug in existing_slugs or any(p.slug == unique_slug for p in people_to_create):
                        unique_slug = f"{base_slug}-{counter}"
                        counter += 1

                    person = Person(
                        ceo_id=next_id,
                        ceo=author_data['full_name'],
                        last_name=author_data['last_name'],
                        first_name=author_data['first_name'],
                        middle_name=author_data['middle_name'] or '',
                        slug=unique_slug
                    )
                    people_to_create.append(person)
                    key_to_new_person[key] = person
                    next_id += 1
                    existing_slugs.add(unique_slug)

                pbar.update(1)
                if pbar.n % 10000 == 0:
                    pbar.set_postfix({"к созданию": len(people_to_create)})

        self.stdout.write(f"        Новых авторов для создания: {len(people_to_create)}")

        # ШАГ 4: Создание новых авторов
        if people_to_create:
            self.stdout.write(f"        Шаг 4/6: Создание новых авторов...")
            batch_size = 500
            created_count = 0

            with tqdm(total=len(people_to_create), desc="           Создание", unit=" чел") as pbar:
                for i in range(0, len(people_to_create), batch_size):
                    batch = people_to_create[i:i+batch_size]
                    Person.objects.bulk_create(batch, batch_size=batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))
                    pbar.set_postfix({"создано": created_count})

            for person in people_to_create:
                key = f"{person.last_name}|{person.first_name}|{person.middle_name}"
                self.person_cache[key] = person

        # ШАГ 5: Подготовка связей
        self.stdout.write("        Шаг 5/6: Подготовка связей...")
        unique_pairs = set()
        through_objs = []

        for key, info in author_to_key.items():
            person = existing_people.get(key) or key_to_new_person.get(key)
            if not person:
                continue

            unique_ip_objects = {ip.pk: ip for ip in info['ip_objects']}

            for ip_object in unique_ip_objects.values():
                pair = (ip_object.pk, person.pk)
                if pair not in unique_pairs:
                    unique_pairs.add(pair)
                    through_objs.append(
                        IPObject.authors.through(
                            ipobject_id=ip_object.pk,
                            person_id=person.pk
                        )
                    )

        self.stdout.write(f"        Уникальных связей для создания: {len(through_objs)}")

        # ШАГ 6: Создание связей
        if through_objs:
            self.stdout.write(f"        Шаг 6/6: Создание связей...")

            # Получаем все уникальные ID IP-объектов
            ip_ids = list(set(obj.ipobject_id for obj in through_objs))
            self.stdout.write(f"           Удаление старых связей для {len(ip_ids)} IP-объектов...")

            # Удаляем старые связи ПАЧКАМИ по 500 ID
            delete_batch_size = 500
            deleted_total = 0

            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.authors.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted

                if (i // delete_batch_size) % 10 == 0:
                    self.stdout.write(f"              Удалено {deleted_total} связей...")

            self.stdout.write(f"           Удалено старых связей: {deleted_total}")

            # Создаем новые связи пачками
            create_batch_size = 1000
            created_count = 0

            with tqdm(total=len(through_objs), desc="           Добавление", unit=" связь") as pbar:
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.authors.through.objects.bulk_create(batch, batch_size=create_batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))
                    pbar.set_postfix({"создано": created_count})

        self.stdout.write(f"        ✅ Обработка авторов завершена")

    def _process_holders_batch_with_progress(self, existing_objects, holders_cache):
        """Обработка правообладателей с прогресс-баром и разбивкой на пачки"""
        self.stdout.write(f"     ⚡ Обработка правообладателей...")

        # ШАГ 1: Сбор уникальных правообладателей
        self.stdout.write("        Шаг 1/7: Сбор уникальных правообладателей...")
        all_holders = set()
        for holders_list in holders_cache.values():
            all_holders.update(holders_list)

        self.stdout.write(f"        Уникальных правообладателей: {len(all_holders)}")

        # ШАГ 2: Определение типов
        self.stdout.write("        Шаг 2/7: Определение типов...")
        person_holders = []
        org_holders = []

        with tqdm(total=len(all_holders), desc="           Анализ", unit=" об") as pbar:
            for holder in all_holders:
                if self.type_detector.detect_type(holder) == 'person':
                    person_holders.append(holder)
                else:
                    org_holders.append(holder)
                pbar.update(1)

        self.stdout.write(f"        Люди: {len(person_holders)}, Организации: {len(org_holders)}")

        # ШАГ 3: Обработка организаций (ЧАСТЯМИ)
        self.stdout.write("        Шаг 3/7: Обработка организаций...")
        org_map = {}

        if org_holders:
            CHUNK_SIZE = 1000
            total_orgs = len(org_holders)

            self.stdout.write(f"        Обработка {total_orgs} организаций частями по {CHUNK_SIZE}...")

            for chunk_start in range(0, total_orgs, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, total_orgs)
                chunk_holders = org_holders[chunk_start:chunk_end]

                # Поиск существующих в этой части
                existing_orgs = {}
                for org in Organization.objects.filter(name__in=chunk_holders):
                    existing_orgs[org.name] = org
                    self.organization_cache[org.name] = org

                # Создание новых в этой части
                orgs_to_create = []
                for holder in chunk_holders:
                    if holder not in existing_orgs and holder not in self.organization_cache:
                        max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
                        new_id = max_id + len(orgs_to_create) + 1

                        base_slug = slugify(holder[:50])
                        if not base_slug:
                            base_slug = 'organization'

                        unique_slug = base_slug
                        counter = 1
                        while Organization.objects.filter(slug=unique_slug).exists() or any(o.slug == unique_slug for o in orgs_to_create):
                            unique_slug = f"{base_slug}-{counter}"
                            counter += 1

                        org = Organization(
                            organization_id=new_id,
                            name=holder,
                            full_name=holder,
                            short_name=holder[:500] if len(holder) > 500 else holder,
                            slug=unique_slug,
                            register_opk=False,
                            strategic=False,
                        )
                        orgs_to_create.append(org)
                        self.organization_cache[holder] = org

                # Мгновенно создаем в БД
                if orgs_to_create:
                    batch_size = 500
                    for i in range(0, len(orgs_to_create), batch_size):
                        batch = orgs_to_create[i:i+batch_size]
                        Organization.objects.bulk_create(batch, batch_size=batch_size)

                # Освобождаем память
                del existing_orgs
                del orgs_to_create

                progress = (chunk_end / total_orgs) * 100
                self.stdout.write(f"           Прогресс: {progress:.1f}%")

            # Финальный маппинг
            for holder in org_holders:
                org_map[holder] = self.organization_cache.get(holder)

        # ШАГ 4: Обработка людей (ЧАСТЯМИ)
        self.stdout.write("        Шаг 4/7: Обработка людей...")
        person_map = {}

        if person_holders:
            CHUNK_SIZE = 500
            total_people = len(person_holders)

            self.stdout.write(f"        Обработка {total_people} людей частями по {CHUNK_SIZE}...")

            for chunk_start in range(0, total_people, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, total_people)
                chunk_holders = person_holders[chunk_start:chunk_end]

                # Поиск существующих
                existing_people = {}
                for holder in chunk_holders:
                    parts = holder.split()
                    if len(parts) >= 2:
                        last_name = parts[0]
                        first_name = parts[1]
                        middle_name = parts[2] if len(parts) > 2 else ''

                        persons = Person.objects.filter(
                            last_name=last_name,
                            first_name=first_name
                        )
                        if middle_name:
                            persons = persons.filter(middle_name=middle_name)

                        person = persons.first()
                        if person:
                            existing_people[holder] = person
                            self.person_cache[holder] = person

                # Создание новых
                people_to_create = []
                for holder in chunk_holders:
                    if holder not in existing_people and holder not in self.person_cache:
                        parts = holder.split()
                        if len(parts) >= 2:
                            last_name = parts[0]
                            first_name = parts[1]
                            middle_name = parts[2] if len(parts) > 2 else ''

                            name_parts = [last_name, first_name]
                            if middle_name:
                                name_parts.append(middle_name)

                            base_slug = slugify(' '.join(name_parts))
                            if not base_slug:
                                base_slug = 'person'

                            unique_slug = base_slug
                            counter = 1
                            while Person.objects.filter(slug=unique_slug).exists() or any(p.slug == unique_slug for p in people_to_create):
                                unique_slug = f"{base_slug}-{counter}"
                                counter += 1

                            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
                            new_id = max_id + len(people_to_create) + 1

                            person = Person(
                                ceo_id=new_id,
                                ceo=holder,
                                last_name=last_name,
                                first_name=first_name,
                                middle_name=middle_name or '',
                                slug=unique_slug
                            )
                            people_to_create.append(person)
                            self.person_cache[holder] = person

                # Мгновенно создаем в БД
                if people_to_create:
                    batch_size = 500
                    for i in range(0, len(people_to_create), batch_size):
                        batch = people_to_create[i:i+batch_size]
                        Person.objects.bulk_create(batch, batch_size=batch_size)

                # Освобождаем память
                del existing_people
                del people_to_create

                progress = (chunk_end / total_people) * 100
                self.stdout.write(f"           Прогресс: {progress:.1f}%")

            # Финальный маппинг
            for holder in person_holders:
                person_map[holder] = self.person_cache.get(holder)

        # ШАГ 5: Подготовка связей
        self.stdout.write("        Шаг 5/7: Подготовка связей...")

        org_relations = set()
        person_relations = set()

        with tqdm(total=sum(len(h) for h in holders_cache.values()), desc="           Сбор связей", unit=" св") as pbar:
            for reg_num, holders_list in holders_cache.items():
                ip_object = existing_objects.get(reg_num)
                if not ip_object:
                    continue

                for holder in holders_list:
                    if holder in org_map and org_map[holder]:
                        org_relations.add((ip_object.pk, org_map[holder].pk))
                    elif holder in person_map and person_map[holder]:
                        person_relations.add((ip_object.pk, person_map[holder].pk))
                    pbar.update(1)

        self.stdout.write(f"        Уникальных связей с организациями: {len(org_relations)}")
        self.stdout.write(f"        Уникальных связей с людьми: {len(person_relations)}")

        # ШАГ 6: Создание связей с организациями
        if org_relations:
            self.stdout.write("        Шаг 6/7: Создание связей с организациями...")

            ip_ids = list(set(ip_id for ip_id, _ in org_relations))

            # Удаляем старые связи ПАЧКАМИ
            delete_batch_size = 500
            deleted_total = 0
            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.owner_organizations.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted
                if (i // delete_batch_size) % 10 == 0:
                    self.stdout.write(f"              Удалено {deleted_total} связей с организациями...")

            self.stdout.write(f"           Удалено старых связей: {deleted_total}")

            # Создаем новые связи пачками
            through_objs = [
                IPObject.owner_organizations.through(
                    ipobject_id=ip_id,
                    organization_id=org_id
                )
                for ip_id, org_id in org_relations
            ]

            create_batch_size = 1000
            created_count = 0
            with tqdm(total=len(through_objs), desc="           Добавление", unit=" св") as pbar:
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.owner_organizations.through.objects.bulk_create(batch, batch_size=create_batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))

        # ШАГ 7: Создание связей с людьми
        if person_relations:
            self.stdout.write("        Шаг 7/7: Создание связей с людьми...")

            ip_ids = list(set(ip_id for ip_id, _ in person_relations))

            # Удаляем старые связи ПАЧКАМИ
            delete_batch_size = 500
            deleted_total = 0
            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.owner_persons.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted
                if (i // delete_batch_size) % 10 == 0:
                    self.stdout.write(f"              Удалено {deleted_total} связей с людьми...")

            self.stdout.write(f"           Удалено старых связей: {deleted_total}")

            # Создаем новые связи пачками
            through_objs = [
                IPObject.owner_persons.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in person_relations
            ]

            create_batch_size = 1000
            created_count = 0
            with tqdm(total=len(through_objs), desc="           Добавление", unit=" св") as pbar:
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.owner_persons.through.objects.bulk_create(batch, batch_size=create_batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))

        self.stdout.write(f"        ✅ Обработка правообладателей завершена")

```


-----

# Файл: management\parsers\utility_model.py

```
"""
Парсер для полезных моделей
"""

from intellectual_property.models import IPType
from .base import BaseFIPSParser


class UtilityModelParser(BaseFIPSParser):
    """Парсер для полезных моделей"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='utility-model').first()

    def get_required_columns(self):
        return ['registration number', 'utility model name']

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  Парсер полезных моделей готов к работе"))
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

```


-----

# Файл: management\parsers\__init__.py

```
from .invention import InventionParser
from .utility_model import UtilityModelParser
from .industrial_design import IndustrialDesignParser
from .integrated_circuit import IntegratedCircuitTopologyParser
from .computer_program import ComputerProgramParser
from .database import DatabaseParser

# Импортируем процессоры из правильного места
from .processors import (
    RussianTextProcessor,
    OrganizationNormalizer,
    PersonNameFormatter,
    RIDNameFormatter,
    EntityTypeDetector
)

__all__ = [
    'InventionParser',
    'UtilityModelParser',
    'IndustrialDesignParser',
    'IntegratedCircuitTopologyParser',
    'ComputerProgramParser',
    'DatabaseParser',
    'RussianTextProcessor',
    'OrganizationNormalizer',
    'PersonNameFormatter',
    'RIDNameFormatter',
    'EntityTypeDetector',
]

```


-----

# Файл: management\parsers\processors\entity_detector.py

```
"""
Детектор типов сущностей
"""

from .text_processor import RussianTextProcessor


class EntityTypeDetector:
    """Детектор типов сущностей"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def detect_type(self, text: str) -> str:
        """Определение типа сущности"""
        if self.processor.is_person(text):
            return 'person'
        return 'organization'

```


-----

# Файл: management\parsers\processors\organization.py

```
"""
Нормализация названий организаций (только для поиска, не для сохранения)
"""

import re
from typing import Dict, Any

import pandas as pd

from core.models import OrganizationNormalizationRule
from .text_processor import RussianTextProcessor


class OrganizationNormalizer:
    """Нормализация названий организаций (только для поиска, не для сохранения)"""

    def __init__(self):
        self.rules_cache = None
        self.processor = RussianTextProcessor()
        self.load_rules()

    def load_rules(self):
        """Загрузка правил из БД"""
        try:
            rules = OrganizationNormalizationRule.objects.all().order_by('priority')
            self.rules_cache = [
                {
                    'original': rule.original_text.lower(),
                    'replacement': rule.replacement_text.lower(),
                    'type': rule.rule_type,
                    'priority': rule.priority
                }
                for rule in rules
            ]
        except Exception as e:
            self.rules_cache = []
            # Логирование ошибки, но не падаем

    def normalize_for_search(self, name: str) -> Dict[str, Any]:
        """
        Нормализация названия ТОЛЬКО для поиска дубликатов
        Само название остается как в CSV
        """
        if pd.isna(name) or not name:
            return {'normalized': '', 'keywords': [], 'original': name}

        original = str(name).strip()
        name_lower = original.lower()

        # Применяем правила из БД для нормализации
        normalized = name_lower
        if self.rules_cache:
            for rule in self.rules_cache:
                try:
                    if rule['type'] == 'ignore':
                        pattern = r'\b' + re.escape(rule['original']) + r'\b'
                        normalized = re.sub(pattern, '', normalized)
                    else:
                        pattern = r'\b' + re.escape(rule['original']) + r'\b'
                        normalized = re.sub(pattern, rule['replacement'], normalized)
                except Exception:
                    continue

        # Убираем кавычки и знаки препинания для поиска
        normalized = re.sub(r'["\'«»„“”]', '', normalized)
        normalized = re.sub(r'[^\w\s-]', ' ', normalized)
        normalized = ' '.join(normalized.split())

        # Извлекаем ключевые слова для поиска
        keywords = []

        # Слова в кавычках
        quoted = re.findall(r'"([^"]+)"', original)
        for q in quoted:
            words = q.lower().split()
            keywords.extend([w for w in words if len(w) > 3])

        # Аббревиатуры
        abbrs = re.findall(r'\b[А-ЯЁA-Z]{2,}\b', original)
        keywords.extend([a.lower() for a in abbrs if len(a) >= 2])

        # Коды (ИНН, ОГРН и т.д.)
        codes = re.findall(r'\b\d{10,}\b', original)
        keywords.extend(codes)

        return {
            'normalized': normalized,
            'keywords': list(set(keywords)),
            'original': original,
        }

    def format_organization_name(self, name: str) -> str:
        """Возвращает оригинальное название без изменений"""
        return name

```


-----

# Файл: management\parsers\processors\person.py

```
"""
Форматирование имен людей
"""

from .text_processor import RussianTextProcessor


class PersonNameFormatter:
    """Форматирование имен людей"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def format(self, name: str) -> str:
        """Форматирование ФИО"""
        return self.processor.format_person_name(name)

```


-----

# Файл: management\parsers\processors\rid.py

```
"""
Форматирование названий РИД
"""

from .text_processor import RussianTextProcessor


class RIDNameFormatter:
    """Форматирование названий РИД"""

    def __init__(self):
        self.processor = RussianTextProcessor()

    def format(self, text: str) -> str:
        """Форматирование названия РИД"""
        if not text or not isinstance(text, str):
            return text

        if len(text.strip()) <= 1:
            return text

        # Приводим к нижнему регистру и делаем первую букву заглавной
        words = text.lower().split()
        if words:
            words[0] = words[0][0].upper() + words[0][1:]
        return ' '.join(words)

```


-----

# Файл: management\parsers\processors\text_processor.py

```
"""
Процессор для русских текстов с использованием natasha
"""

from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,
    Doc,
    NamesExtractor
)


class RussianTextProcessor:
    """
    Процессор для русских текстов с использованием natasha
    """

    # Список римских цифр
    ROMAN_NUMERALS = {
        'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
        'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
        'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXX', 'XL', 'L', 'LX', 'XC',
        'C', 'CD', 'D', 'DC', 'CM', 'M'
    }

    # Аббревиатуры для поиска организаций
    ORG_ABBR = {
        'ООО', 'ЗАО', 'ОАО', 'АО', 'ПАО', 'НАО',
        'ФГУП', 'ФГБУ', 'ФГАОУ', 'ФГАУ', 'ФГКУ',
        'НИИ', 'КБ', 'ОКБ', 'СКБ', 'ЦКБ', 'ПКБ',
        'НПО', 'НПП', 'НПФ', 'НПЦ', 'НИЦ',
        'МУП', 'ГУП', 'ИЧП', 'ТОО', 'АОЗТ', 'АООТ',
        'РФ', 'РАН', 'СО РАН', 'УрО РАН', 'ДВО РАН',
        'МГУ', 'СПбГУ', 'МФТИ', 'МИФИ', 'МГТУ', 'МАИ',
        'ЛТД', 'ИНК', 'КО', 'ГМБХ', 'АГ', 'СА', 'НВ', 'БВ', 'СЕ',
        'Ко', 'Ltd', 'Inc', 'GmbH', 'AG', 'SA', 'NV', 'BV', 'SE',
    }

    def __init__(self):
        # Инициализация компонентов natasha
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.emb = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(self.emb)
        self.syntax_parser = NewsSyntaxParser(self.emb)
        self.ner_tagger = NewsNERTagger(self.emb)
        self.names_extractor = NamesExtractor(self.morph_vocab)

        # Кэши для производительности
        self.doc_cache = {}
        self.morph_cache = {}

        # Добавляем римские цифры в аббревиатуры
        self.ORG_ABBR.update(self.ROMAN_NUMERALS)

    def get_doc(self, text: str) -> Doc:
        """Получение или создание документа с кэшированием"""
        if not text:
            return None

        if text in self.doc_cache:
            return self.doc_cache[text]

        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        doc.parse_syntax(self.syntax_parser)
        doc.tag_ner(self.ner_tagger)

        # Лемматизация
        for token in doc.tokens:
            token.lemmatize(self.morph_vocab)

        for span in doc.spans:
            span.normalize(self.morph_vocab)

        self.doc_cache[text] = doc
        return doc

    def is_roman_numeral(self, text: str) -> bool:
        """Проверка на римскую цифру"""
        if not text:
            return False
        clean_text = text.strip('.,;:!?()').upper()
        return clean_text in self.ROMAN_NUMERALS

    def is_abbr(self, text: str) -> bool:
        """Проверка на аббревиатуру организации"""
        if not text:
            return False
        clean_text = text.strip('.,;:!?()').upper()
        return clean_text in self.ORG_ABBR

    def is_person(self, text: str) -> bool:
        """Определение, является ли текст ФИО человека"""
        if not text or len(text) < 6:
            return False

        # Если есть явные признаки организации
        if any(ind in text for ind in self.ORG_ABBR if len(ind) > 2):
            return False

        org_indicators = ['Общество', 'Компания', 'Корпорация', 'Завод',
                         'Институт', 'Университет', 'Академия', 'Лаборатория',
                         'Фирма', 'Центр']

        if any(ind.lower() in text.lower() for ind in org_indicators):
            return False

        # Проверка через NER
        doc = self.get_doc(text)
        if doc and doc.spans:
            for span in doc.spans:
                if span.type == 'PER':
                    return True

        # Паттерны ФИО
        words = text.split()
        if 2 <= len(words) <= 4:
            name_like = 0
            for word in words:
                clean = word.rstrip('.,')
                if clean and clean[0].isupper() and len(clean) > 1:
                    name_like += 1
            return name_like >= len(words) - 1

        return False

    def extract_person_parts(self, text: str) -> dict:
        """Извлечение частей ФИО с помощью natasha"""
        matches = list(self.names_extractor(text))
        if matches:
            fact = matches[0].fact
            parts = []
            if fact.last:
                parts.append(fact.last)
            if fact.first:
                parts.append(fact.first)
            if fact.middle:
                parts.append(fact.middle)

            return {
                'last': fact.last or '',
                'first': fact.first or '',
                'middle': fact.middle or '',
                'full': ' '.join(parts)
            }

        # Fallback: ручной парсинг
        return self._parse_name_manually(text)

    def _parse_name_manually(self, text: str) -> dict:
        """Ручной парсинг имени"""
        words = text.split()

        if len(words) == 3:
            return {
                'last': words[0],
                'first': words[1],
                'middle': words[2],
                'full': text
            }
        elif len(words) == 2:
            return {
                'last': words[0],
                'first': words[1],
                'middle': '',
                'full': text
            }
        else:
            return {
                'last': text,
                'first': '',
                'middle': '',
                'full': text
            }

    def format_person_name(self, name: str) -> str:
        """Форматирование ФИО человека"""
        if not name:
            return name

        parts = self.extract_person_parts(name)
        if parts.get('full'):
            return parts['full']

        return name

```


-----

# Файл: management\parsers\processors\__init__.py

```
from .text_processor import RussianTextProcessor
from .organization import OrganizationNormalizer
from .person import PersonNameFormatter
from .rid import RIDNameFormatter
from .entity_detector import EntityTypeDetector

__all__ = [
    'RussianTextProcessor',
    'OrganizationNormalizer',
    'PersonNameFormatter',
    'RIDNameFormatter',
    'EntityTypeDetector',
]

```


-----

# Файл: management\utils\csv_loader.py

```
"""
Утилиты для загрузки CSV файлов
"""

import pandas as pd


def load_csv_with_strategies(file_path, encoding, delimiter, stdout=None):
    """
    Загрузка CSV с несколькими стратегиями
    """
    strategies = [
        {'encoding': encoding, 'delimiter': delimiter, 'skipinitialspace': True},
        {'encoding': 'cp1251', 'delimiter': delimiter, 'skipinitialspace': True},
        {'encoding': 'utf-8', 'delimiter': ';', 'skipinitialspace': True},
        {'encoding': 'cp1251', 'delimiter': ';', 'skipinitialspace': True},
        {'encoding': 'utf-8', 'delimiter': '\t', 'skipinitialspace': True},
    ]

    for strategy in strategies:
        try:
            df = pd.read_csv(file_path, **strategy, dtype=str, keep_default_na=False)
            if stdout:
                stdout.write(f"  ✅ Успешно загружено с параметрами: {strategy}")

            df.columns = [col.strip().strip('\ufeff').strip('"') for col in df.columns]
            return df
        except Exception:
            continue

    raise Exception("Не удалось загрузить CSV ни одной стратегией")

```


-----

# Файл: management\utils\filters.py

```
"""
Утилиты для фильтрации DataFrame
"""

from datetime import datetime
import pandas as pd


def filter_by_registration_year(df, min_year, stdout=None):
    """
    Фильтрация DataFrame по году регистрации
    """
    def extract_year(date_str):
        try:
            if pd.isna(date_str) or not date_str:
                return None

            date_str = str(date_str).strip()
            if not date_str:
                return None

            for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str, fmt).year
                except (ValueError, TypeError):
                    continue

            try:
                return pd.to_datetime(date_str).year
            except (ValueError, TypeError):
                return None
        except:
            return None

    if stdout:
        stdout.write("  🔍 Фильтрация по году регистрации...")

    if 'registration date' not in df.columns:
        if stdout:
            stdout.write("  ⚠️ Колонка 'registration date' не найдена, пропускаем фильтрацию по году")
        return df

    df['_year'] = df['registration date'].apply(extract_year)

    if stdout:
        # Фильтруем None значения для статистики
        valid_years = df['_year'].dropna()
        if not valid_years.empty:
            years_dist = valid_years.value_counts().sort_index()
            years_list = list(years_dist.items())
            if len(years_list) > 0:
                stdout.write(f"     Диапазон годов: {years_list[0][0]:.0f} - {years_list[-1][0]:.0f}")
                stdout.write(f"     Первые 5: {years_list[:5]}")
                stdout.write(f"     Последние 5: {years_list[-5:]}")

    filtered_df = df[df['_year'] >= min_year].copy() if '_year' in df.columns else df.copy()
    if '_year' in filtered_df.columns:
        filtered_df.drop('_year', axis=1, inplace=True)

    return filtered_df


def filter_by_actual(df, stdout=None):
    """
    Фильтрация DataFrame по активности (actual = True)
    """
    def parse_actual(value):
        if pd.isna(value) or not value:
            return False
        value = str(value).lower().strip()
        return value in ['1', 'true', 'yes', 'да', 'действует', 't', '1.0', 'активен']

    if 'actual' not in df.columns:
        if stdout:
            stdout.write("  ⚠️ Колонка 'actual' не найдена, пропускаем фильтрацию по активности")
        return df

    df['_actual'] = df['actual'].apply(parse_actual)
    filtered_df = df[df['_actual'] == True].copy()
    filtered_df.drop('_actual', axis=1, inplace=True)

    return filtered_df


def apply_filters(df, min_year, only_active, stdout=None):
    """
    Применение всех фильтров к DataFrame
    """
    original_count = len(df)

    if min_year is not None:
        df = filter_by_registration_year(df, min_year, stdout)

    if only_active:
        df = filter_by_actual(df, stdout)

    filtered_count = len(df)
    if stdout and filtered_count < original_count:
        stdout.write(f"  🔍 Фильтрация: {original_count} → {filtered_count} записей")

    return df

```


-----

# Файл: management\utils\__init__.py

```

```
