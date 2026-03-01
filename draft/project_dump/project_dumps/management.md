# Файл: management\help.txt

```
python manage.py pars_fips_catalogue \
  --catalogue-id 42 \
  --ip-type invention \
  --dry-run \
  --encoding utf-8 \
  --delimiter , \
  --batch-size 1000 \
  --min-year 2020 \
  --max-year 2023 \
  --skip-filters \
  --only-active \
  --max-rows 10000 \
  --force \
  --mark-processed \
  --process-by-year \
  --year-step 1 \
  --start-year 2021

  # Только активные изобретения с 2020 года, по годам
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --only-active --process-by-year

# Тест для 2023 года (10 записей)
python manage.py pars_fips_catalogue --ip-type computer-program --min-year 2023 --max-year 2023 --max-rows 10 --process-by-year

# Принудительный перепарсинг конкретного каталога
python manage.py pars_fips_catalogue --catalogue-id 42 --force

# Все программы для ЭВМ без фильтров
python manage.py pars_fips_catalogue --ip-type computer-program --skip-filters

# ============================================================================
# ПАРСЕР КАТАЛОГОВ ОТКРЫТЫХ ДАННЫХ ФИПС РОСПАТЕНТА
# ============================================================================

# ----------------------------------------------------------------------------
# ОСНОВНЫЕ РЕЖИМЫ РАБОТЫ
# ----------------------------------------------------------------------------

# Режим ONLY-ACTIVE: парсинг только активных записей (actual = True)
# Режим MIN-YEAR 2020: парсинг только записей 2020 года и позже
# Режим MAX-YEAR 2023: парсинг только записей до 2023 года включительно
# Режим PROCESS-BY-YEAR: обработка по годам (уменьшает нагрузку на БД)
# Режим DRY-RUN: изменения НЕ будут сохранены в БД
# Режим FORCE: принудительный парсинг, игнорируя дату последней обработки

# ----------------------------------------------------------------------------
# ТИПЫ РИД ДЛЯ ПАРСИНГА
# ----------------------------------------------------------------------------

# --ip-type invention                      # Изобретения
# --ip-type utility-model                  # Полезные модели
# --ip-type industrial-design              # Промышленные образцы
# --ip-type integrated-circuit-topology    # Топологии интегральных микросхем
# --ip-type computer-program               # Программы для ЭВМ
# --ip-type database                       # Базы данных

# ----------------------------------------------------------------------------
# ПРИМЕРЫ ЗАПУСКА
# ----------------------------------------------------------------------------

# 1. ТЕСТОВЫЙ ЗАПУСК (мало записей)
# ----------------------------------------------------------------------------

# Тест для изобретений (10 записей)
python manage.py pars_fips_catalogue --ip-type invention --max-rows 10

# Тест для изобретений 2026 года (10 записей)
python manage.py pars_fips_catalogue --ip-type invention --min-year 2026 --max-rows 10

# Тест для программ для ЭВМ (активные, 2023 год, 100 записей)
python manage.py pars_fips_catalogue --ip-type computer-program --min-year 2023 --max-year 2023 --only-active --max-rows 100

# Тест в режиме DRY-RUN (проверка без сохранения)
python manage.py pars_fips_catalogue --ip-type database --min-year 2024 --dry-run --max-rows 50

# ----------------------------------------------------------------------------
# 2. ОБРАБОТКА ПО ГОДАМ (РЕКОМЕНДУЕТСЯ ДЛЯ БОЛЬШИХ ОБЪЕМОВ)
# ----------------------------------------------------------------------------

# Все изобретения с 2020 года, разбивая по годам
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --process-by-year

# Все полезные модели с 2018 по 2022 год с шагом 2 года
python manage.py pars_fips_catalogue --ip-type utility-model --min-year 2018 --max-year 2022 --process-by-year --year-step 2

# Начать обработку программ для ЭВМ с 2021 года (пропустить ранние)
python manage.py pars_fips_catalogue --ip-type computer-program --min-year 2020 --process-by-year --start-year 2021

# Только активные промышленные образцы 2023 года
python manage.py pars_fips_catalogue --ip-type industrial-design --min-year 2023 --max-year 2023 --only-active --process-by-year

# ----------------------------------------------------------------------------
# 3. ПОЛНЫЙ ПАРСИНГ (ВСЕ ЗАПИСИ)
# ----------------------------------------------------------------------------

# Все изобретения (без фильтров)
python manage.py pars_fips_catalogue --ip-type invention --skip-filters

# Все полезные модели (без фильтров)
python manage.py pars_fips_catalogue --ip-type utility-model --skip-filters

# Все программы для ЭВМ (без фильтров)
python manage.py pars_fips_catalogue --ip-type computer-program --skip-filters

# ----------------------------------------------------------------------------
# 4. ПАРСИНГ ПО КАТАЛОГАМ
# ----------------------------------------------------------------------------

# Конкретный каталог по ID
python manage.py pars_fips_catalogue --catalogue-id 42

# Конкретный каталог с принудительным перепарсингом
python manage.py pars_fips_catalogue --catalogue-id 42 --force

# Конкретный каталог с пометкой как обработанный (даже с ошибками)
python manage.py pars_fips_catalogue --catalogue-id 42 --mark-processed

# ----------------------------------------------------------------------------
# 5. ПАРСИНГ С ФИЛЬТРАЦИЕЙ ПО ГОДАМ
# ----------------------------------------------------------------------------

# Все изобретения с 2020 года
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020

# Все изобретения с 2015 по 2020 год
python manage.py pars_fips_catalogue --ip-type invention --min-year 2015 --max-year 2020

# Все изобретения с 2020 года (только активные)
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --only-active

# Все изобретения с 2020 года (только активные, по годам)
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --only-active --process-by-year

# ----------------------------------------------------------------------------
# 6. ПРОДВИНУТЫЕ СЦЕНАРИИ
# ----------------------------------------------------------------------------

# Полный перепарсинг всех изобретений с 2020 года (игнорируя даты обработки)
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --force --process-by-year

# Парсинг баз данных с кастомной кодировкой и разделителем
python manage.py pars_fips_catalogue --ip-type database --encoding cp1251 --delimiter ';' --min-year 2020

# Парсинг с большими пачками для ускорения
python manage.py pars_fips_catalogue --ip-type invention --batch-size 5000 --min-year 2020 --process-by-year

# Парсинг всех типов РИД с 2020 года (последовательно)
python manage.py pars_fips_catalogue --ip-type invention --min-year 2020 --process-by-year
python manage.py pars_fips_catalogue --ip-type utility-model --min-year 2020 --process-by-year
python manage.py pars_fips_catalogue --ip-type industrial-design --min-year 2020 --process-by-year
python manage.py pars_fips_catalogue --ip-type integrated-circuit-topology --min-year 2020 --process-by-year
python manage.py pars_fips_catalogue --ip-type computer-program --min-year 2020 --process-by-year
python manage.py pars_fips_catalogue --ip-type database --min-year 2020 --process-by-year

# ----------------------------------------------------------------------------
# ПОЛНОЕ ОПИСАНИЕ ПАРАМЕТРОВ
# ----------------------------------------------------------------------------

usage: manage.py pars_fips_catalogue [-h] [--catalogue-id CATALOGUE_ID] 
                                     [--ip-type {invention,utility-model,industrial-design,integrated-circuit-topology,computer-program,database}] 
                                     [--dry-run] [--encoding ENCODING] [--delimiter DELIMITER] 
                                     [--batch-size BATCH_SIZE] [--min-year MIN_YEAR] [--max-year MAX_YEAR] 
                                     [--skip-filters] [--only-active] [--max-rows MAX_ROWS] [--force] 
                                     [--mark-processed] [--process-by-year] [--year-step YEAR_STEP] 
                                     [--start-year START_YEAR] [--version] [-v {0,1,2,3}] 
                                     [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] 
                                     [--no-color] [--force-color] [--skip-checks]

Парсинг каталогов открытых данных ФИПС Роспатента с поддержкой обработки по годам

options:
  -h, --help            show this help message and exit
  
  --catalogue-id CATALOGUE_ID
                        ID конкретного каталога для парсинга
                        
  --ip-type {invention,utility-model,industrial-design,integrated-circuit-topology,computer-program,database}
                        Тип РИД для парсинга (если не указан, парсятся все)
                        
  --dry-run             Режим проверки без сохранения в БД
  
  --encoding ENCODING   Кодировка CSV файла (по умолчанию: utf-8)
  
  --delimiter DELIMITER
                        Разделитель в CSV файле (по умолчанию: ,)
                        
  --batch-size BATCH_SIZE
                        Размер пакета для bulk-операций (по умолчанию: 100)
                        
  --min-year MIN_YEAR   Минимальный год регистрации для фильтрации (по умолчанию: 2000)
  
  --max-year MAX_YEAR   Максимальный год регистрации для фильтрации (опционально)
  
  --skip-filters        Пропустить фильтрацию (обработать все записи)
  
  --only-active         Парсить только активные патенты (actual = True)
  
  --max-rows MAX_ROWS   Максимальное количество строк для обработки (для тестирования)
  
  --force               Принудительный парсинг даже если каталог уже обработан
  
  --mark-processed      Пометить каталог как обработанный (даже если были ошибки)
  
  --process-by-year     Обрабатывать данные по годам (уменьшает нагрузку на БД)
  
  --year-step YEAR_STEP
                        Шаг по годам при обработке (по умолчанию: 1)
                        
  --start-year START_YEAR
                        Начальный год для обработки (если нужно начать не с минимального)
  
  --version             Show program's version number and exit.
  
  -v, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 
                        3=very verbose output
                        
  --settings SETTINGS   The Python path to a settings module, e.g. "myproject.settings.main". 
                        If this isn't provided, the DJANGO_SETTINGS_MODULE environment variable 
                        will be used.
                        
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g. 
                        "/home/djangoprojects/myproject".
                        
  --traceback           Display a full stack trace on CommandError exceptions.
  
  --no-color            Don't colorize the command output.
  
  --force-color         Force colorization of the command output.
  
  --skip-checks         Skip system checks.

# ----------------------------------------------------------------------------
# ПРИМЕРЫ ВЫВОДА СТАТИСТИКИ
# ----------------------------------------------------------------------------

# При обработке по годам вы увидите:
# ============================================================
# 📁 Обработка каталога: Изобретения 2024
#    ID: 42, Тип: Изобретение
# ============================================================
#   
#   📅 Найдены годы в каталоге: 2020 - 2024 (всего 5 лет)
#   
#   📅 Год 2024 (1/5)
#   🔹 Начинаем парсинг изобретений для 2024 года
#   🔹 Чтение CSV и сбор регистрационных номеров
#   🔹 Всего записей в CSV: 1250
#   ...
#   ✅ Парсинг изобретений для 2024 года завершен
#      Создано: 120, Обновлено: 30, Без изменений: 1100
#   
#   📅 Год 2023 (2/5)
#   ...

# Итоговая статистика:
# ============================================================
# 📊 ИТОГОВАЯ СТАТИСТИКА
# ============================================================
# 📁 Обработано каталогов: 1
# 📝 Всего записей обработано: 6250
# ✅ Создано: 600
# 🔄 Обновлено: 150
# ⏸️  Без изменений: 5500
# ⏭️  Пропущено всего: 0
#    └─ по дате обновления: 0
# ✅ Ошибок: 0
# ============================================================

# ----------------------------------------------------------------------------
# РЕКОМЕНДАЦИИ ПО ИСПОЛЬЗОВАНИЮ
# ----------------------------------------------------------------------------

# Для больших объемов данных (более 100 000 записей):
#   - Используйте --process-by-year для разбивки по годам
#   - Увеличьте --batch-size до 1000-5000 для ускорения
#   - Используйте --only-active если нужны только действующие патенты
#   - При проблемах с памятью уменьшите --batch-size

# Для тестирования:
#   - Всегда используйте --dry-run для проверки
#   - Ограничивайте количество записей через --max-rows
#   - Проверяйте один год через --min-year и --max-year

# Для повторного парсинга:
#   - Используйте --force для игнорирования даты обработки
#   - Используйте --mark-processed если хотите пометить как обработанный даже с ошибками

# Для отладки:
#   - Используйте -v 2 или -v 3 для подробного вывода
#   - Используйте --traceback для полной трассировки ошибок
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
Поддерживает обработку по годам для уменьшения нагрузки на БД.
"""

import logging
import os
import gc
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import pandas as pd

from intellectual_property.models import FipsOpenDataCatalogue

# Импортируем парсеры из пакета parsers
from ..parsers import (
    InventionParser, UtilityModelParser, IndustrialDesignParser,
    IntegratedCircuitTopologyParser, ComputerProgramParser, DatabaseParser
)
from ..utils.csv_loader import load_csv_with_strategies
from ..utils.filters import apply_filters, filter_by_actual

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
        parser.add_argument('--max-year', type=int, help='Максимальный год регистрации для фильтрации')
        parser.add_argument('--skip-filters', action='store_true', help='Пропустить фильтрацию (обработать все записи)')
        parser.add_argument('--only-active', action='store_true', help='Парсить только активные патенты (actual = True)')
        parser.add_argument('--max-rows', type=int, help='Максимальное количество строк для обработки (для тестирования)')
        parser.add_argument('--force', action='store_true', help='Принудительный парсинг даже если каталог уже обработан')
        parser.add_argument('--mark-processed', action='store_true',
                        help='Пометить каталог как обработанный (даже если были ошибки)')
        parser.add_argument('--process-by-year', action='store_true',
                        help='Обрабатывать данные по годам (уменьшает нагрузку на БД)')
        parser.add_argument('--year-step', type=int, default=1,
                        help='Шаг по годам при обработке (по умолчанию 1)')
        parser.add_argument('--start-year', type=int,
                        help='Начальный год для обработки (если нужно начать не с минимального)')

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
        self.max_year = options.get('max_year')
        self.skip_filters = options['skip_filters']
        self.only_active = options['only_active']
        self.max_rows = options.get('max_rows')
        self.force = options.get('force', False)
        self.mark_processed = options.get('mark_processed', False)
        self.process_by_year = options.get('process_by_year', False)
        self.year_step = options.get('year_step', 1)
        self.start_year = options.get('start_year')

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД\n"))

        if self.only_active:
            self.stdout.write(self.style.WARNING("📌 Режим: парсинг только активных записей (actual = True)"))

        if self.force:
            self.stdout.write(self.style.WARNING("⚠️  Режим: принудительный парсинг (игнорирование даты обработки)"))

        if self.process_by_year:
            self.stdout.write(self.style.WARNING(
                f"📅 Режим: обработка по годам с {self.min_year} по {self.max_year or 'все'} (шаг {self.year_step})"
            ))

        catalogues = self.get_catalogues(options.get('catalogue_id'), options.get('ip_type'))

        if not catalogues:
            raise CommandError('Не найдены каталоги для парсинга')

        total_stats = {
            'catalogues': len(catalogues),
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
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

            for key in ['processed', 'created', 'updated', 'unchanged', 'skipped', 'errors']:
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

    def extract_year_from_date(self, date_str):
        """Извлечение года из строки с датой"""
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

    def get_years_from_catalogue(self, catalogue):
        """
        Определяет список годов, присутствующих в CSV файле каталога
        """
        df = self.load_csv(catalogue)
        if df is None or df.empty:
            return []
        
        if 'registration date' not in df.columns:
            self.stdout.write(self.style.WARNING(
                f"  ⚠️ Колонка 'registration date' не найдена, не могу определить годы"
            ))
            return []
        
        df['_year'] = df['registration date'].apply(self.extract_year_from_date)
        all_years = sorted(df['_year'].dropna().unique().astype(int).tolist())
        
        if not all_years:
            self.stdout.write(self.style.WARNING("  ⚠️ Не удалось извлечь годы из дат"))
            return []
        
        # Подробный отладочный вывод
        self.stdout.write(f"  📊 Все годы в каталоге: {all_years[0]} - {all_years[-1]} (всего {len(all_years)} лет)")
        
        if len(all_years) > 20:
            self.stdout.write(f"     Первые 10 лет: {all_years[:10]}")
            self.stdout.write(f"     Последние 10 лет: {all_years[-10:]}")
        else:
            self.stdout.write(f"     Все годы: {all_years}")
        
        # ЕСЛИ УКАЗАН --skip-filters - ВОЗВРАЩАЕМ ВСЕ ГОДЫ БЕЗ ФИЛЬТРАЦИИ!
        if self.skip_filters:
            self.stdout.write(f"  🔍 Фильтрация отключена (--skip-filters), обрабатываются все годы")
            return all_years
        
        # Применяем фильтр по минимальному году (ТОЛЬКО если не skip_filters)
        years = all_years
        if self.min_year is not None:
            years = [y for y in all_years if y >= self.min_year]
            self.stdout.write(f"  🔍 После фильтрации по min_year={self.min_year}: {years[0] if years else 'нет'} - {years[-1] if years else 'нет'} (всего {len(years)} лет)")
        
        # Применяем фильтр по максимальному году
        if self.max_year is not None:
            years = [y for y in years if y <= self.max_year]
            self.stdout.write(f"  🔍 После фильтрации по max_year={self.max_year}: {years[0] if years else 'нет'} - {years[-1] if years else 'нет'} (всего {len(years)} лет)")
        
        # Применяем начальный год, если указан
        if self.start_year and self.start_year in years:
            start_idx = years.index(self.start_year)
            years = years[start_idx:]
            self.stdout.write(f"  🔍 Начинаем с {self.start_year}: {years[0]} - {years[-1]} (всего {len(years)} лет)")
        
        return years

    def process_catalogue(self, catalogue):
        """
        Обработка каталога с поддержкой разбивки по годам
        """
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
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
        
        # Определяем режим обработки
        if not self.process_by_year or self.skip_filters or self.min_year is None:
            # Обычный режим - обрабатываем все сразу
            stats = self._process_catalogue_normal(catalogue, parser, stats)
        else:
            # Режим обработки по годам
            stats = self._process_catalogue_by_year(catalogue, parser, stats)
        
        # Помечаем каталог как обработанный
        if not self.dry_run and hasattr(catalogue, 'parsed_date'):
            if stats['errors'] == 0 or self.mark_processed:
                catalogue.parsed_date = timezone.now()
                catalogue.save(update_fields=['parsed_date'])
                self.stdout.write(self.style.SUCCESS(f"  ✅ Каталог помечен как обработанный"))
            else:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠️ Каталог не помечен как обработанный из-за ошибок"
                ))

        return stats

    def _process_catalogue_normal(self, catalogue, parser, stats):
        """Обычная обработка каталога без разбивки по годам"""
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
            df = apply_filters(df, self.min_year, self.only_active, self.stdout, self.max_year)
        
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
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка при парсинге: {e}"))
            logger.error(f"Error parsing catalogue {catalogue.id}: {e}", exc_info=True)
            stats['errors'] += 1
        
        return stats

    def _process_catalogue_by_year(self, catalogue, parser, stats):
        """Обработка каталога с разбивкой по годам"""
        # Получаем список годов - теперь с учетом skip_filters!
        years = self.get_years_from_catalogue(catalogue)
        
        if not years:
            self.stdout.write(self.style.WARNING(
                f"  ⚠️ Не удалось определить годы в каталоге, обрабатываем целиком"
            ))
            return self._process_catalogue_normal(catalogue, parser, stats)
        
        self.stdout.write(self.style.SUCCESS(
            f"\n  📅 Будет обработано {len(years)} лет: {years[0]} - {years[-1]}"
        ))
        
        # Загружаем полный DataFrame один раз
        full_df = self.load_csv(catalogue)
        if full_df is None or full_df.empty:
            stats['skipped'] += 1
            return stats
        
        missing_columns = self.check_required_columns(full_df, parser.get_required_columns())
        if missing_columns:
            self.stdout.write(self.style.ERROR(f"  ❌ Отсутствуют обязательные колонки: {missing_columns}"))
            stats['errors'] += 1
            return stats
        
        # Добавляем колонку с годом
        full_df['_year'] = full_df['registration date'].apply(self.extract_year_from_date)
        
        # Обрабатываем годы с заданным шагом
        years_to_process = years[::self.year_step]
        
        for year_idx, year in enumerate(years_to_process, 1):
            self.stdout.write(self.style.SUCCESS(
                f"\n  📅 Год {year} ({year_idx}/{len(years_to_process)})"
            ))
            
            # Фильтруем DataFrame для текущего года
            year_df = full_df[full_df['_year'] == year].copy()
            
            # Применяем фильтр по активности (actual) если нужно
            if self.only_active and not self.skip_filters:
                year_df = filter_by_actual(year_df, self.stdout)
            
            if year_df.empty:
                self.stdout.write(self.style.WARNING(f"     ⚠️ Нет данных для года {year} после фильтрации"))
                continue
            
            if self.max_rows:
                year_df = year_df.head(min(self.max_rows, len(year_df)))
            
            try:
                year_stats = parser.parse_dataframe(year_df, catalogue, year=year)
                
                # Обновляем общую статистику
                stats['processed'] += year_stats.get('processed', 0)
                stats['created'] += year_stats.get('created', 0)
                stats['updated'] += year_stats.get('updated', 0)
                stats['unchanged'] += year_stats.get('unchanged', 0)
                stats['errors'] += year_stats.get('errors', 0)
                
                self.stdout.write(f"     Результаты года {year}: "
                                f"создано={year_stats.get('created', 0)}, "
                                f"обновлено={year_stats.get('updated', 0)}, "
                                f"без изменений={year_stats.get('unchanged', 0)}")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Ошибка при парсинге года {year}: {e}"))
                logger.error(f"Error parsing year {year} for catalogue {catalogue.id}: {e}", exc_info=True)
                stats['errors'] += 1
            
            # Принудительная сборка мусора после каждого года
            gc.collect()
        
        # Удаляем временную колонку
        if '_year' in full_df.columns:
            del full_df['_year']
        
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
        self.stdout.write(f"⏸️  Без изменений: {stats.get('unchanged', 0)}")
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
Поддерживает параметр year для обработки по годам
"""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import gc

from django.db import models
from django.utils.text import slugify
import pandas as pd

from intellectual_property.models import IPObject, IPType
from core.models import Person, Organization, Country

from .processors import (
    RussianTextProcessor,
    OrganizationNormalizer,
    PersonNameFormatter,
    RIDNameFormatter,
    EntityTypeDetector
)

from ..utils.progress import batch_iterator

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

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
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
        """
        Парсинг строки с авторами
        Возвращает список словарей с данными авторов
        """
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
        """
        Парсинг строки с патентообладателями
        Возвращает список названий
        """
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

    # =========================================================================
    # МЕТОДЫ ДЛЯ МАССОВОГО СОЗДАНИЯ ЛЮДЕЙ
    # =========================================================================

    def _create_persons_bulk(self, persons_df: pd.DataFrame) -> Dict[str, Person]:
        """
        Пакетное создание людей из DataFrame с индикацией прогресса
        
        Args:
            persons_df: DataFrame с колонкой 'entity_name'
            
        Returns:
            Словарь {имя: объект Person}
        """
        person_map = {}
        
        if persons_df.empty:
            self.stdout.write("      Нет людей для обработки")
            return person_map
        
        all_names = persons_df['entity_name'].tolist()
        total_names = len(all_names)
        
        self.stdout.write(f"      Всего уникальных людей для обработки: {total_names}")
        
        # ШАГ 1: Поиск существующих людей
        self.stdout.write(f"      Поиск существующих людей в БД...")
        
        name_to_parts = self._extract_name_parts(all_names)
        existing_persons = self._find_existing_persons(name_to_parts)
        
        # ШАГ 2: Определяем новых людей
        valid_names = list(name_to_parts.keys())
        new_names = [name for name in valid_names if name not in existing_persons]
        new_count = len(new_names)
        
        self.stdout.write(f"      Новых людей для создания: {new_count}")
        
        # ШАГ 3: Создаем новых людей
        if new_names:
            new_persons_map = self._create_new_persons(new_names)
            person_map.update(new_persons_map)
        
        # ШАГ 4: Добавляем существующих людей в маппинг
        person_map.update(existing_persons)
        
        self.stdout.write(f"      ✅ Обработано людей: {len(person_map)}")
        
        return person_map

    def _extract_name_parts(self, names: List[str]) -> Dict[str, Tuple[str, str, str]]:
        """
        Извлечение частей ФИО из списка имен
        
        Returns:
            Словарь {полное_имя: (фамилия, имя, отчество)}
        """
        name_to_parts = {}
        for name in names:
            if pd.isna(name) or not name:
                continue
            name = str(name).strip()
            if not name:
                continue
            
            parts = name.split()
            if len(parts) >= 2:
                last = parts[0]
                first = parts[1]
                middle = parts[2] if len(parts) > 2 else ''
                name_to_parts[name] = (last, first, middle)
        
        return name_to_parts

    def _find_existing_persons(self, name_to_parts: Dict[str, Tuple[str, str, str]]) -> Dict[str, Person]:
        """
        Поиск существующих людей в БД
        
        Returns:
            Словарь {имя: объект Person}
        """
        existing_persons = {}
        found_count = 0
        batch_size = 100
        all_names_list = list(name_to_parts.keys())
        
        for i in range(0, len(all_names_list), batch_size):
            batch_names = all_names_list[i:i+batch_size]
            
            # Строим условия поиска
            name_conditions = models.Q()
            batch_name_to_parts = {}
            
            for name in batch_names:
                last, first, middle = name_to_parts[name]
                batch_name_to_parts[name] = (last, first, middle)
                
                if middle:
                    name_conditions |= models.Q(
                        last_name=last, 
                        first_name=first, 
                        middle_name=middle
                    )
                else:
                    name_conditions |= models.Q(
                        last_name=last, 
                        first_name=first
                    ) & (models.Q(middle_name='') | models.Q(middle_name__isnull=True))
            
            # Ищем людей
            for person in Person.objects.filter(name_conditions).only(
                'ceo_id', 'last_name', 'first_name', 'middle_name', 'ceo', 'slug'
            ):
                for name, (last, first, middle) in batch_name_to_parts.items():
                    if (person.last_name == last and 
                        person.first_name == first and 
                        (not middle or person.middle_name == middle)):
                        existing_persons[name] = person
                        self.person_cache[name] = person
                        found_count += 1
                        break
            
            if (i + len(batch_names)) % 500 == 0 or (i + len(batch_names)) >= len(all_names_list):
                self.stdout.write(f"         Обработано {i + len(batch_names)}/{len(all_names_list)} имен")
        
        self.stdout.write(f"      Найдено существующих: {found_count}")
        return existing_persons

    def _create_new_persons(self, new_names: List[str]) -> Dict[str, Person]:
        """
        Создание новых людей
        
        Returns:
            Словарь {имя: объект Person}
        """
        self.stdout.write(f"      Подготовка данных для создания...")
        
        # Получаем все существующие slugs
        existing_slugs = set(Person.objects.values_list('slug', flat=True))
        self.stdout.write(f"         Существующих slug-ов в БД: {len(existing_slugs)}")
        
        people_to_create = []
        
        for name in new_names:
            if pd.isna(name) or not name:
                continue
            
            name = str(name).strip()
            parts = name.split()
            
            if len(parts) >= 2:
                last_name = parts[0]
                first_name = parts[1]
                middle_name = parts[2] if len(parts) > 2 else ''
                
                # Формируем базовый slug
                name_parts_list = [last_name, first_name]
                if middle_name:
                    name_parts_list.append(middle_name)
                
                base_slug = slugify(' '.join(name_parts_list))
                if not base_slug:
                    base_slug = 'person'
                
                # Генерируем уникальный slug
                unique_slug, existing_slugs = self._generate_unique_slug(base_slug, existing_slugs)
                
                # Создаем объект без ID (ID будет назначен при bulk_create)
                person = Person(
                    ceo=name,
                    last_name=last_name,
                    first_name=first_name,
                    middle_name=middle_name or '',
                    slug=unique_slug
                )
                people_to_create.append(person)
        
        # Создаем людей
        return self._bulk_create_persons(people_to_create, len(new_names))

    def _generate_unique_slug(self, base_slug: str, existing_slugs: set) -> Tuple[str, set]:
        """
        Генерация уникального slug
        
        Returns:
            Tuple[уникальный_slug, обновленное_множество_slugs]
        """
        unique_slug = base_slug
        counter = 1
        while unique_slug in existing_slugs:
            unique_slug = f"{base_slug}-{counter}"
            counter += 1
        
        existing_slugs.add(unique_slug)
        return unique_slug, existing_slugs

    def _bulk_create_persons(self, people_to_create: List[Person], total_count: int) -> Dict[str, Person]:
        """
        Массовое создание людей с обработкой ошибок
        
        Returns:
            Словарь {имя: объект Person}
        """
        if not people_to_create:
            return {}
        
        self.stdout.write(f"      Создание людей пачками по 500...")
        
        BATCH_SIZE = 500
        created_count = 0
        created_map = {}
        
        for i in range(0, len(people_to_create), BATCH_SIZE):
            batch = people_to_create[i:i+BATCH_SIZE]
            
            # Получаем актуальный max_id перед каждой пачкой
            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
            next_id = max_id + 1
            
            # Назначаем ID для текущей пачки
            for j, person in enumerate(batch):
                person.ceo_id = next_id + j
            
            # Фильтруем дубликаты в пачке
            batch = self._filter_duplicate_persons(batch)
            if not batch:
                continue
            
            # Пробуем создать пачкой
            try:
                Person.objects.bulk_create(batch, batch_size=BATCH_SIZE, ignore_conflicts=True)
                created_count += len(batch)
                self.stdout.write(self.style.SUCCESS(f"         ✅ Создана пачка из {len(batch)} человек"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"         Ошибка при создании пачки: {e}"))
                created_count += self._create_persons_one_by_one(batch)
            
            if created_count % 5000 == 0 or created_count >= total_count:
                percent = (created_count / total_count) * 100 if total_count > 0 else 0
                self.stdout.write(f"         Прогресс: {created_count}/{total_count} ({percent:.1f}%)")
        
        # Получаем созданных людей для маппинга
        if created_count > 0:
            created_names = [p.ceo for p in people_to_create[:created_count]]
            created_map = self._fetch_created_persons(created_names)
        
        return created_map

    def _filter_duplicate_persons(self, batch: List[Person]) -> List[Person]:
        """
        Фильтрация дубликатов в пачке по ceo_id и slug
        """
        batch_ceo_ids = [p.ceo_id for p in batch]
        batch_slugs = [p.slug for p in batch]
        
        existing_by_ceo = set(Person.objects.filter(ceo_id__in=batch_ceo_ids).values_list('ceo_id', flat=True))
        existing_by_slug = set(Person.objects.filter(slug__in=batch_slugs).values_list('slug', flat=True))
        
        if existing_by_ceo or existing_by_slug:
            self.stdout.write(self.style.WARNING(f"         Найдены дубликаты в пачке:"))
            if existing_by_ceo:
                self.stdout.write(self.style.WARNING(f"            по ceo_id: {list(existing_by_ceo)[:5]}..."))
            if existing_by_slug:
                self.stdout.write(self.style.WARNING(f"            по slug: {list(existing_by_slug)[:5]}..."))
            
            batch = [p for p in batch 
                    if p.ceo_id not in existing_by_ceo 
                    and p.slug not in existing_by_slug]
        
        return batch

    def _create_persons_one_by_one(self, batch: List[Person]) -> int:
        """
        Создание людей по одному в случае ошибки пачки
        """
        created = 0
        for person in batch:
            for attempt in range(10):
                try:
                    # Получаем свежий max_id перед каждой попыткой
                    current_max = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
                    person.ceo_id = current_max + 1
                    
                    # Проверяем и обновляем slug при необходимости
                    if Person.objects.filter(slug=person.slug).exists():
                        base_slug = person.slug.split('-')[0]
                        counter = 1
                        new_slug = f"{base_slug}-{counter}"
                        while Person.objects.filter(slug=new_slug).exists():
                            counter += 1
                            new_slug = f"{base_slug}-{counter}"
                        person.slug = new_slug
                    
                    person.save()
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"            ✅ Создан: {person.ceo}"))
                    break
                except Exception as e:
                    if attempt == 9:
                        self.stdout.write(self.style.ERROR(f"            ❌ Не удалось создать {person.ceo}: {e}"))
                    continue
        return created

    def _fetch_created_persons(self, names: List[str]) -> Dict[str, Person]:
        """
        Получение созданных людей из БД для маппинга
        """
        person_map = {}
        for batch in batch_iterator(names, 1000):
            for person in Person.objects.filter(ceo__in=batch).only('ceo_id', 'ceo', 'slug'):
                person_map[person.ceo] = person
                self.person_cache[person.ceo] = person
        return person_map

    # =========================================================================
    # МЕТОДЫ ДЛЯ МАССОВОГО СОЗДАНИЯ ОРГАНИЗАЦИЙ
    # =========================================================================

    def _create_organizations_bulk(self, orgs_df: pd.DataFrame) -> Dict[str, Organization]:
        """
        Пакетное создание организаций из DataFrame с индикацией прогресса
        
        Args:
            orgs_df: DataFrame с колонкой 'entity_name'
            
        Returns:
            Словарь {название: объект Organization}
        """
        org_map = {}
        
        if orgs_df.empty:
            self.stdout.write("      Нет организаций для обработки")
            return org_map
        
        all_names = orgs_df['entity_name'].tolist()
        total_names = len(all_names)
        
        self.stdout.write(f"      Всего уникальных организаций для обработки: {total_names}")
        
        # ШАГ 1: Поиск существующих организаций
        self.stdout.write(f"      Поиск существующих организаций в БД...")
        
        existing_orgs = self._find_existing_organizations(all_names)
        
        # ШАГ 2: Определяем новые организации
        new_names = [name for name in all_names if name not in existing_orgs]
        new_count = len(new_names)
        
        self.stdout.write(f"      Новых организаций для создания: {new_count}")
        
        # ШАГ 3: Создаем новые организации
        if new_names:
            new_orgs_map = self._create_new_organizations(new_names)
            org_map.update(new_orgs_map)
        
        # ШАГ 4: Добавляем существующие организации
        org_map.update(existing_orgs)
        
        self.stdout.write(f"      ✅ Обработано организаций: {len(org_map)}")
        
        return org_map

    def _find_existing_organizations(self, names: List[str]) -> Dict[str, Organization]:
        """
        Поиск существующих организаций в БД
        """
        existing_orgs = {}
        batch_size = 100
        
        for i in range(0, len(names), batch_size):
            batch_names = names[i:i+batch_size]
            
            for org in Organization.objects.filter(name__in=batch_names).only('organization_id', 'name', 'slug'):
                existing_orgs[org.name] = org
                self.organization_cache[org.name] = org
            
            if (i + len(batch_names)) % 500 == 0 or (i + len(batch_names)) >= len(names):
                self.stdout.write(f"         Обработано {i + len(batch_names)}/{len(names)} названий")
        
        self.stdout.write(f"      Найдено существующих: {len(existing_orgs)}")
        return existing_orgs

    def _create_new_organizations(self, new_names: List[str]) -> Dict[str, Organization]:
        """
        Создание новых организаций
        """
        self.stdout.write(f"      Подготовка данных для создания...")
        
        max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
        
        # Получаем все существующие slugs
        existing_slugs = set(Organization.objects.values_list('slug', flat=True))
        self.stdout.write(f"      Всего существующих slug: {len(existing_slugs)}")
        
        orgs_to_create = []
        used_slugs_in_batch = set()
        
        for name in new_names:
            base_slug = slugify(name[:50]) or 'organization'
            unique_slug = base_slug
            counter = 1
            
            # Проверяем И существующие slugs, И уже использованные в этом батче
            while unique_slug in existing_slugs or unique_slug in used_slugs_in_batch:
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            used_slugs_in_batch.add(unique_slug)
            existing_slugs.add(unique_slug)
            
            org = Organization(
                organization_id=max_id + len(orgs_to_create) + 1,
                name=name,
                full_name=name,
                short_name=name[:500] if len(name) > 500 else name,
                slug=unique_slug,
                register_opk=False,
                strategic=False,
            )
            orgs_to_create.append(org)
        
        # Создаем организации
        return self._bulk_create_organizations(orgs_to_create, len(new_names))

    def _bulk_create_organizations(self, orgs_to_create: List[Organization], total_count: int) -> Dict[str, Organization]:
        """
        Массовое создание организаций с обработкой ошибок
        """
        org_map = {}
        batch_size = 500
        created_count = 0
        
        for batch in batch_iterator(orgs_to_create, batch_size):
            try:
                # Пробуем создать пачкой с ignore_conflicts
                Organization.objects.bulk_create(batch, batch_size=batch_size, ignore_conflicts=True)
                created_count += len(batch)
            except Exception as e:
                self.stdout.write(f"         Ошибка при создании батча: {e}")
                # В случае ошибки создаем по одному
                for org in batch:
                    try:
                        org.save()
                        created_count += 1
                    except Exception as e2:
                        self.stdout.write(f"         Не удалось создать организацию {org.name}: {e2}")
            
            if created_count % 5000 == 0 or created_count == total_count:
                percent = (created_count / total_count) * 100 if total_count > 0 else 0
                self.stdout.write(f"         Создано {created_count}/{total_count} ({percent:.1f}%)")
        
        # Получаем созданные организации для маппинга
        if created_count > 0:
            created_names = [o.name for o in orgs_to_create[:created_count]]
            org_map = self._fetch_created_organizations(created_names)
        
        return org_map

    def _fetch_created_organizations(self, names: List[str]) -> Dict[str, Organization]:
        """
        Получение созданных организаций из БД для маппинга
        """
        org_map = {}
        for batch in batch_iterator(names, 1000):
            for org in Organization.objects.filter(name__in=batch).only('organization_id', 'name', 'slug'):
                org_map[org.name] = org
                self.organization_cache[org.name] = org
        return org_map

    # =========================================================================
    # МЕТОДЫ ДЛЯ РАБОТЫ СО СВЯЗЯМИ (ОБЩИЕ ДЛЯ ВСЕХ ПАРСЕРОВ)
    # =========================================================================

    def _process_relations_dataframe(self, relations_data: List[Dict], reg_to_ip: Dict):
        """
        Обработка всех связей через единый DataFrame
        Этот метод может быть переопределен в дочерних классах при необходимости
        """
        if not relations_data:
            self.stdout.write("   Нет данных для обработки связей")
            return

        self.stdout.write("   Создание DataFrame связей")
        df_relations = pd.DataFrame(relations_data)
        
        self.stdout.write(f"   Всего записей связей: {len(df_relations)}")
        self.stdout.write(f"   Уникальных регистрационных номеров: {df_relations['reg_number'].nunique()}")

        self.stdout.write("   Добавление ID объектов")
        df_relations['ip_id'] = df_relations['reg_number'].map(reg_to_ip)

        missing_ip = df_relations['ip_id'].isna().sum()
        if missing_ip > 0:
            self.stdout.write(self.style.WARNING(f"   ⚠️ Пропущено {missing_ip} связей с отсутствующими ID объектов"))
            df_relations = df_relations.dropna(subset=['ip_id']).copy()
        
        df_relations['ip_id'] = df_relations['ip_id'].astype(int)

        # Определение типов для правообладателей
        self.stdout.write("   Определение типов сущностей через Natasha")
        
        unique_entities = df_relations[['entity_name', 'entity_type']].drop_duplicates()
        holders_to_check = unique_entities[unique_entities['entity_type'].isna()]['entity_name'].tolist()

        if holders_to_check:
            self.stdout.write(f"   Определение типов для {len(holders_to_check)} правообладателей")
            entity_type_map = self.type_detector.detect_type_batch(holders_to_check)

            mask = df_relations['entity_type'].isna()
            df_relations.loc[mask, 'entity_type'] = \
                df_relations.loc[mask, 'entity_name'].map(entity_type_map)

        type_stats = df_relations['entity_type'].value_counts().to_dict()
        self.stdout.write(f"   Распределение типов: люди={type_stats.get('person', 0)}, "
                         f"организации={type_stats.get('organization', 0)}")

        # Группировка по сущностям
        unique_entities = df_relations[['entity_name', 'entity_type']].drop_duplicates()
        
        persons_df = unique_entities[unique_entities['entity_type'] == 'person']
        orgs_df = unique_entities[unique_entities['entity_type'] == 'organization']

        person_map = {}
        if not persons_df.empty:
            self.stdout.write(f"   Обработка {len(persons_df)} уникальных людей")
            person_map = self._create_persons_bulk(persons_df)

        org_map = {}
        if not orgs_df.empty:
            self.stdout.write(f"   Обработка {len(orgs_df)} уникальных организаций")
            org_map = self._create_organizations_bulk(orgs_df)

        # Подготовка связей
        self.stdout.write("   Подготовка связей для вставки в БД")

        authors_df = df_relations[df_relations['relation_type'] == 'author'].copy()
        holders_df = df_relations[df_relations['relation_type'] == 'holder'].copy()

        # Авторы
        author_relations = self._prepare_author_relations(authors_df, person_map)
        
        # Правообладатели (люди и организации)
        holder_person_relations, holder_org_relations = self._prepare_holder_relations(
            holders_df, person_map, org_map
        )

        # Создание связей
        self._create_all_relations(author_relations, holder_person_relations, holder_org_relations)

        self.stdout.write(self.style.SUCCESS("   ✅ Обработка всех связей завершена"))

    def _prepare_author_relations(self, authors_df: pd.DataFrame, person_map: Dict) -> List[Tuple[int, int]]:
        """Подготовка связей авторов"""
        if authors_df.empty:
            return []
        
        person_id_map = {name: p.ceo_id for name, p in person_map.items()}
        authors_df['person_id'] = authors_df['entity_name'].map(person_id_map)
        authors_df = authors_df.dropna(subset=['person_id'])
        authors_df['person_id'] = authors_df['person_id'].astype(int)
        
        authors_unique = authors_df[['ip_id', 'person_id']].drop_duplicates()
        relations = [(row['ip_id'], row['person_id']) for _, row in authors_unique.iterrows()]
        
        self.stdout.write(f"   Подготовлено {len(relations)} уникальных связей авторов")
        return relations

    def _prepare_holder_relations(self, holders_df: pd.DataFrame, person_map: Dict, org_map: Dict) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Подготовка связей правообладателей"""
        person_relations = []
        org_relations = []

        if holders_df.empty:
            return person_relations, org_relations

        # Правообладатели-люди
        holders_persons = holders_df[holders_df['entity_type'] == 'person'].copy()
        if not holders_persons.empty:
            person_id_map = {name: p.ceo_id for name, p in person_map.items()}
            holders_persons['person_id'] = holders_persons['entity_name'].map(person_id_map)
            holders_persons = holders_persons.dropna(subset=['person_id'])
            holders_persons['person_id'] = holders_persons['person_id'].astype(int)
            
            holders_persons_unique = holders_persons[['ip_id', 'person_id']].drop_duplicates()
            person_relations = [(row['ip_id'], row['person_id']) for _, row in holders_persons_unique.iterrows()]
            self.stdout.write(f"   Подготовлено {len(person_relations)} связей правообладателей-людей")

        # Правообладатели-организации
        holders_orgs = holders_df[holders_df['entity_type'] == 'organization'].copy()
        if not holders_orgs.empty:
            org_id_map = {name: o.organization_id for name, o in org_map.items()}
            holders_orgs['org_id'] = holders_orgs['entity_name'].map(org_id_map)
            holders_orgs = holders_orgs.dropna(subset=['org_id'])
            holders_orgs['org_id'] = holders_orgs['org_id'].astype(int)
            
            holders_orgs_unique = holders_orgs[['ip_id', 'org_id']].drop_duplicates()
            org_relations = [(row['ip_id'], row['org_id']) for _, row in holders_orgs_unique.iterrows()]
            self.stdout.write(f"   Подготовлено {len(org_relations)} связей правообладателей-организаций")

        return person_relations, org_relations

    def _create_all_relations(self, author_relations: List[Tuple[int, int]], 
                             holder_person_relations: List[Tuple[int, int]], 
                             holder_org_relations: List[Tuple[int, int]]):
        """Создание всех типов связей"""
        if author_relations:
            self.stdout.write("   Создание связей авторов")
            ip_ids = list(set(ip_id for ip_id, _ in author_relations))
            with tqdm(total=len(ip_ids), desc="   Удаление старых связей авторов", unit="ip") as pbar:
                self._delete_author_relations(ip_ids, pbar)
            
            with tqdm(total=len(author_relations), desc="   Создание новых связей авторов", unit="св") as pbar:
                self._create_author_relations(author_relations, pbar)

        if holder_person_relations:
            self.stdout.write("   Создание связей правообладателей (люди)")
            ip_ids = list(set(ip_id for ip_id, _ in holder_person_relations))
            with tqdm(total=len(ip_ids), desc="   Удаление старых связей", unit="ip") as pbar:
                self._delete_holder_person_relations(ip_ids, pbar)
            
            with tqdm(total=len(holder_person_relations), desc="   Создание новых связей", unit="св") as pbar:
                self._create_holder_person_relations(holder_person_relations, pbar)

        if holder_org_relations:
            self.stdout.write("   Создание связей правообладателей (организации)")
            ip_ids = list(set(ip_id for ip_id, _ in holder_org_relations))
            with tqdm(total=len(ip_ids), desc="   Удаление старых связей", unit="ip") as pbar:
                self._delete_holder_org_relations(ip_ids, pbar)
            
            with tqdm(total=len(holder_org_relations), desc="   Создание новых связей", unit="св") as pbar:
                self._create_holder_org_relations(holder_org_relations, pbar)

    # Методы для удаления связей
    def _delete_author_relations(self, ip_ids: List[int], pbar):
        """Удаление связей авторов"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.authors.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    def _delete_holder_person_relations(self, ip_ids: List[int], pbar):
        """Удаление связей правообладателей-людей"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.owner_persons.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    def _delete_holder_org_relations(self, ip_ids: List[int], pbar):
        """Удаление связей правообладателей-организаций"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.owner_organizations.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    # Методы для создания связей
    def _create_author_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей авторов"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.authors.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in batch
            ]
            IPObject.authors.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))

    def _create_holder_person_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей правообладателей-людей"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.owner_persons.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in batch
            ]
            IPObject.owner_persons.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))

    def _create_holder_org_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей правообладателей-организаций"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.owner_organizations.through(
                    ipobject_id=ip_id,
                    organization_id=org_id
                )
                for ip_id, org_id in batch
            ]
            IPObject.owner_organizations.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))
```


-----

# Файл: management\parsers\computer_program.py

```
"""
Парсер для программ для ЭВМ с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import re

import pandas as pd
from django.db import models, transaction
from django.utils.text import slugify
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from core.models import Organization

from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class ComputerProgramParser(BaseFIPSParser):
    """
    Парсер для программ для ЭВМ с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'computer-program'"""
        return IPType.objects.filter(slug='computer-program').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'program name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('creation_year', obj.creation_year, new_data.get('creation_year')),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг программ для ЭВМ{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'computer-program' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('program name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Программа для ЭВМ №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    
                    creation_year = None
                    creation_year_str = row.get('creation year')
                    if not pd.isna(creation_year_str) and creation_year_str:
                        try:
                            creation_year = int(float(creation_year_str))
                        except (ValueError, TypeError):
                            pass
                    
                    if not creation_year and application_date:
                        creation_year = application_date.year
                    elif not creation_year and registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'creation_year': creation_year,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self._parse_program_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Правообладатели
                    holders_str = row.get('right holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self._parse_right_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing computer program {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг программ для ЭВМ{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _parse_program_authors(self, authors_str: str) -> List[Dict]:
        """
        Парсинг строки с авторами для программ для ЭВМ
        """
        if pd.isna(authors_str) or not authors_str:
            return []

        authors_str = str(authors_str)
        authors_list = re.split(r'[\n]\s*', authors_str)

        result = []
        for author in authors_list:
            author = author.strip()
            if not author or author == '""' or author == 'null':
                continue

            author = author.strip('"')
            author = re.sub(r'\s*\([A-Z]{2}\)$', '', author)
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

    def _parse_right_holders(self, holders_str: str) -> List[str]:
        """
        Парсинг строки с правообладателями для программ для ЭВМ
        """
        if pd.isna(holders_str) or not holders_str:
            return []
        
        holders_str = str(holders_str)
        holders_list = re.split(r'[\n]\s*', holders_str)
        
        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None' or holder.lower() == 'нет':
                continue
            holder = re.sub(r'\s*\([A-Z]{2}\)$', '', holder)
            result.append(holder)
        
        return result

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\database.py

```
"""
Парсер для баз данных с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import re

import pandas as pd
from django.db import models, transaction
from django.utils.text import slugify
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from core.models import Organization

from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class DatabaseParser(BaseFIPSParser):
    """
    Парсер для баз данных с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'database'"""
        return IPType.objects.filter(slug='database').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'db name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('expiration_date', obj.expiration_date, new_data.get('expiration_date')),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('creation_year', obj.creation_year, new_data.get('creation_year')),
            ('publication_year', obj.publication_year, new_data.get('publication_year')),
            ('update_year', obj.update_year, new_data.get('update_year')),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг баз данных{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'database' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('db name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"База данных №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    
                    creation_year = None
                    creation_year_str = row.get('creation year')
                    if not pd.isna(creation_year_str) and creation_year_str:
                        try:
                            creation_year = int(float(creation_year_str))
                        except (ValueError, TypeError):
                            pass
                    
                    publication_year = None
                    publication_year_str = row.get('publication year')
                    if not pd.isna(publication_year_str) and publication_year_str:
                        try:
                            publication_year = int(float(publication_year_str))
                        except (ValueError, TypeError):
                            pass
                    
                    update_year = None
                    update_year_str = row.get('update year')
                    if not pd.isna(update_year_str) and update_year_str:
                        try:
                            update_year = int(float(update_year_str))
                        except (ValueError, TypeError):
                            pass
                    
                    if not creation_year and application_date:
                        creation_year = application_date.year
                    elif not creation_year and registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'creation_year': creation_year,
                        'publication_year': publication_year,
                        'update_year': update_year,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self._parse_database_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Правообладатели
                    holders_str = row.get('right holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self._parse_right_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing database {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг баз данных{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _parse_database_authors(self, authors_str: str) -> List[Dict]:
        """
        Парсинг строки с авторами для баз данных
        """
        if pd.isna(authors_str) or not authors_str:
            return []

        authors_str = str(authors_str)
        authors_list = re.split(r'[\n]\s*', authors_str)

        result = []
        for author in authors_list:
            author = author.strip()
            if not author or author == '""' or author == 'null':
                continue

            author = author.strip('"')
            author = re.sub(r'\s*\([A-Z]{2}\)$', '', author)
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

    def _parse_right_holders(self, holders_str: str) -> List[str]:
        """
        Парсинг строки с правообладателями для баз данных
        """
        if pd.isna(holders_str) or not holders_str:
            return []
        
        holders_str = str(holders_str)
        holders_list = re.split(r'[\n]\s*', holders_str)
        
        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None' or holder.lower() == 'нет':
                continue
            holder = re.sub(r'\s*\([A-Z]{2}\)$', '', holder)
            result.append(holder)
        
        return result

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\industrial_design.py

```
"""
Парсер для промышленных образцов с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

import pandas as pd
from django.db import models, transaction
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class IndustrialDesignParser(BaseFIPSParser):
    """
    Парсер для промышленных образцов с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'industrial-design'"""
        return IPType.objects.filter(slug='industrial-design').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'industrial design name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('patent_starting_date', obj.patent_starting_date, new_data['patent_starting_date']),
            ('expiration_date', obj.expiration_date, new_data['expiration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('abstract', obj.abstract, new_data['abstract']),
            ('creation_year', obj.creation_year, new_data['creation_year']),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг промышленных образцов{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'industrial-design' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('industrial design name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Промышленный образец №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    patent_starting_date = self.parse_date(row.get('patent starting date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    
                    abstract = ''

                    creation_year = None
                    if application_date:
                        creation_year = application_date.year
                    elif registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'patent_starting_date': patent_starting_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'abstract': abstract,
                        'creation_year': creation_year,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self.parse_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Патентообладатели
                    holders_str = row.get('patent holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self.parse_patent_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing industrial design {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            # Используем метод базового класса
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг промышленных образцов{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\integrated_circuit.py

```
"""
Парсер для топологий интегральных микросхем с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import re

import pandas as pd
from django.db import models, transaction
from django.utils.text import slugify
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType, Person
from core.models import Organization, Country

from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class IntegratedCircuitTopologyParser(BaseFIPSParser):
    """
    Парсер для топологий интегральных микросхем с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'integrated-circuit-topology'"""
        return IPType.objects.filter(slug='integrated-circuit-topology').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'microchip name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('expiration_date', obj.expiration_date, new_data['expiration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('creation_year', obj.creation_year, new_data['creation_year']),
            ('first_usage_date', obj.first_usage_date, new_data.get('first_usage_date')),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг топологий интегральных микросхем{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'integrated-circuit-topology' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        first_usage_countries_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('microchip name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Топология ИМС №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    
                    first_usage_date = self.parse_date(row.get('first usage date'))
                    
                    creation_year = None
                    if application_date:
                        creation_year = application_date.year
                    elif registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'creation_year': creation_year,
                        'first_usage_date': first_usage_date,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self.parse_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Правообладатели
                    holders_str = row.get('right holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self._parse_right_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                    # Страны первого использования
                    countries_str = row.get('first usage countries')
                    if not pd.isna(countries_str) and countries_str and countries_str.lower() != 'нет':
                        countries = self._parse_first_usage_countries(countries_str)
                        for country_code in countries:
                            first_usage_countries_data.append({
                                'reg_number': reg_num,
                                'country_code': country_code
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing integrated circuit topology {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        # =====================================================================
        # ШАГ 7: Обработка стран первого использования
        # =====================================================================
        if first_usage_countries_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка стран первого использования")
            self._process_first_usage_countries(first_usage_countries_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг топологий интегральных микросхем{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _parse_right_holders(self, holders_str: str) -> List[str]:
        """
        Парсинг строки с правообладателями для топологий ИМС
        """
        if pd.isna(holders_str) or not holders_str:
            return []
        
        holders_str = str(holders_str)
        holders_list = re.split(r'[\n]\s*', holders_str)
        
        result = []
        for holder in holders_list:
            holder = holder.strip().strip('"')
            if not holder or holder == 'null' or holder == 'None' or holder.lower() == 'нет':
                continue
            holder = re.sub(r'\s*\([A-Z]{2}\)$', '', holder)
            result.append(holder)
        
        return result

    def _parse_first_usage_countries(self, countries_str: str) -> List[str]:
        """
        Парсинг строки со странами первого использования
        """
        if pd.isna(countries_str) or not countries_str:
            return []
        
        countries_str = str(countries_str)
        if countries_str.lower() == 'нет':
            return []
        
        countries = re.split(r'[,\s]+', countries_str)
        
        result = []
        country_map = {
            'РФ': 'RU',
            'Россия': 'RU',
            'Российская Федерация': 'RU',
            'RU': 'RU',
            'RUS': 'RU',
        }
        
        for country in countries:
            country = country.strip()
            if not country:
                continue
            
            if country in country_map:
                result.append(country_map[country])
            elif len(country) == 2 and country.isupper():
                result.append(country)
            else:
                country_obj = Country.objects.filter(name__icontains=country).first()
                if country_obj:
                    result.append(country_obj.code)
                else:
                    self.stdout.write(self.style.WARNING(f"      ⚠️ Не удалось определить код страны: {country}"))
        
        return list(set(result))

    def _process_first_usage_countries(self, countries_data: List[Dict], reg_to_ip: Dict):
        """
        Обработка связей со странами первого использования
        """
        if not countries_data:
            return
        
        self.stdout.write("   Подготовка связей со странами первого использования")
        
        reg_to_countries = defaultdict(set)
        for item in countries_data:
            ip_id = reg_to_ip.get(item['reg_number'])
            if ip_id:
                reg_to_countries[ip_id].add(item['country_code'])
        
        if not reg_to_countries:
            return
        
        country_codes = set()
        for countries in reg_to_countries.values():
            country_codes.update(countries)
        
        country_map = {}
        for code in country_codes:
            country = self.get_or_create_country(code)
            if country:
                country_map[code] = country
        
        ip_ids = list(reg_to_countries.keys())
        
        # Удаляем старые связи
        with tqdm(total=len(ip_ids), desc="   Удаление старых связей со странами", unit="ip") as pbar:
            delete_batch_size = 500
            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ids = ip_ids[i:i+delete_batch_size]
                IPObject.first_usage_countries.through.objects.filter(
                    ipobject_id__in=batch_ids
                ).delete()
                pbar.update(len(batch_ids))
        
        # Создаем новые связи
        through_objs = []
        for ip_id, country_codes in reg_to_countries.items():
            for code in country_codes:
                country = country_map.get(code)
                if country:
                    through_objs.append(
                        IPObject.first_usage_countries.through(
                            ipobject_id=ip_id,
                            country_id=country.id
                        )
                    )
        
        if through_objs:
            with tqdm(total=len(through_objs), desc="   Создание связей со странами", unit="св") as pbar:
                create_batch_size = 2000
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.first_usage_countries.through.objects.bulk_create(
                        batch, batch_size=create_batch_size, ignore_conflicts=True
                    )
                    pbar.update(len(batch))
        
        self.stdout.write("   ✅ Обработка стран первого использования завершена")

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\invention.py

```
"""
Парсер для изобретений с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

import pandas as pd
from django.db import models, transaction
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class InventionParser(BaseFIPSParser):
    """
    Парсер для изобретений с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'invention'"""
        return IPType.objects.filter(slug='invention').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'invention name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
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

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг изобретений{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'invention' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    name = self.clean_string(row.get('invention name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Изобретение №{reg_num}"

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

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
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
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self.parse_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Патентообладатели
                    holders_str = row.get('patent holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self.parse_patent_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing invention {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг изобретений{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\utility_model.py

```
"""
Парсер для полезных моделей с использованием единого DataFrame для связей
Поддерживает параметр year для обработки по годам
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

import pandas as pd
from django.db import models, transaction
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType
from .base import BaseFIPSParser
from ..utils.progress import batch_iterator

logger = logging.getLogger(__name__)


class UtilityModelParser(BaseFIPSParser):
    """
    Парсер для полезных моделей с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'utility-model'"""
        return IPType.objects.filter(slug='utility-model').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'utility model name']

    def _has_data_changed(self, obj, new_data):
        """
        Проверяет, изменились ли данные объекта
        """
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

    def parse_dataframe(self, df, catalogue, year=None):
        """
        Основной метод парсинга DataFrame
        
        Args:
            df: DataFrame с данными
            catalogue: объект каталога
            year: год для текущей обработки (опционально)
        """
        year_msg = f" для {year} года" if year else ""
        self.stdout.write(f"\n🔹 Начинаем парсинг полезных моделей{year_msg}")

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        # Получаем тип РИД
        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'utility-model' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.stdout.write("🔹 Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.stdout.write(f"🔹 Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.stdout.write("🔹 Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        with tqdm(total=len(reg_numbers), desc="Загрузка пачками", unit="зап") as pbar:
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.stdout.write(f"🔹 Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.stdout.write("🔹 Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        with tqdm(total=len(reg_num_to_row), desc="Подготовка данных IPObject", unit="зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('utility model name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Полезная модель №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    patent_starting_date = self.parse_date(row.get('patent starting date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    
                    abstract = self.clean_string(row.get('abstract', ''))
                    claims = self.clean_string(row.get('claims', ''))

                    creation_year = None
                    if application_date:
                        creation_year = application_date.year
                    elif registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type_id': ip_type.id,
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
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Авторы
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self.parse_authors(authors_str)
                        for author in authors:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': author['full_name'],
                                'entity_type': 'person',
                                'relation_type': 'author',
                                'entity_data': author
                            })

                    # Патентообладатели
                    holders_str = row.get('patent holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self.parse_patent_holders(holders_str)
                        for holder in holders:
                            relations_data.append({
                                'reg_number': reg_num,
                                'entity_name': holder,
                                'entity_type': None,
                                'relation_type': 'holder',
                                'entity_data': {'full_name': holder}
                            })

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    if len(error_reg_numbers) < 10:
                        self.stdout.write(self.style.ERROR(f"\n❌ Ошибка подготовки записи {reg_num}: {e}"))
                    elif len(error_reg_numbers) == 10:
                        self.stdout.write(self.style.WARNING("\n⚠️ ... и далее ошибки подавляются"))
                    
                    logger.error(f"Error preparing utility model {reg_num}: {e}", exc_info=True)

                pbar.update(1)

        self.stdout.write(f"🔹 Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                         f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.stdout.write(f"🔹 Создание {len(to_create)} новых записей")
            with tqdm(total=len(to_create), desc="Создание", unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.stdout.write(f"🔹 Обновление {len(to_update)} записей")
            with tqdm(total=len(to_update), desc="Обновление", unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.stdout.write("🔹 Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with tqdm(total=len(all_reg_numbers), desc="Загрузка ID объектов", unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.stdout.write(f"🔹 Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.stdout.write("🔹 Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        year_info = f" для {year} года" if year else ""
        self.stdout.write(self.style.SUCCESS(f"\n✅ Парсинг полезных моделей{year_info} завершен"))
        self.stdout.write(f"   Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}")
        self.stdout.write(f"   Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.stdout.write(f"   Ошибок: {stats['errors']}")

        return stats

    def _bulk_create_objects(self, to_create: List[Dict], pbar) -> int:
        """Пакетное создание объектов IPObject"""
        created_count = 0
        batch_size = 1000

        for batch in batch_iterator(to_create, batch_size):
            create_objects = [IPObject(**data) for data in batch]
            IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
            created_count += len(batch)
            pbar.update(len(batch))

        return created_count

    def _bulk_update_objects(self, to_update: List[Dict], existing_objects: Dict, pbar) -> int:
        """Пакетное обновление объектов IPObject"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500

        for batch in batch_iterator(to_update, BATCH_UPDATE_SIZE):
            with transaction.atomic():
                for data in batch:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []
                    for field, value in data.items():
                        if field != 'registration_number' and getattr(obj, field) != value:
                            setattr(obj, field, value)
                            update_fields.append(field)
                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1
            pbar.update(len(batch))

        return updated_count
```


-----

# Файл: management\parsers\__init__.py

```
"""
Пакет с парсерами для различных типов РИД
"""

from .invention import InventionParser
from .utility_model import UtilityModelParser
from .industrial_design import IndustrialDesignParser
from .integrated_circuit import IntegratedCircuitTopologyParser
from .computer_program import ComputerProgramParser
from .database import DatabaseParser

# Импортируем процессоры из подпакета processors
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
Детектор типов сущностей с использованием Natasha и кэшированием
"""

# ИСПРАВЛЕНО: импортируем из текущего пакета (.text_processor)
from .text_processor import RussianTextProcessor


class EntityTypeDetector:
    """
    Детектор типов сущностей с использованием Natasha и кэшированием
    Определяет, является ли текст именем человека или названием организации
    """

    def __init__(self, cache_size: int = 50000):
        self.processor = RussianTextProcessor()
        # Кэш для результатов, чтобы не вызывать Natasha повторно
        self.cache = {}
        self.cache_size = cache_size
        self.cache_hits = 0
        self.cache_misses = 0

    def detect_type(self, text: str) -> str:
        """
        Определение типа сущности с использованием Natasha

        Args:
            text: Название сущности (ФИО или название организации)

        Returns:
            'person' или 'organization'
        """
        if not text or len(text) < 2:
            return 'organization'

        # Проверяем кэш
        if text in self.cache:
            self.cache_hits += 1
            return self.cache[text]

        self.cache_misses += 1

        # Используем процессор с Natasha для определения
        # is_person() внутри использует NER и другие методы Natasha
        if self.processor.is_person(text):
            result = 'person'
        else:
            result = 'organization'

        # Кэшируем результат с контролем размера
        self._add_to_cache(text, result)

        return result

    def detect_type_batch(self, texts: list) -> dict:
        """
        Пакетное определение типов для списка текстов

        Args:
            texts: Список текстов для анализа

        Returns:
            Словарь {текст: тип}
        """
        result = {}

        # Сначала проверяем кэш
        to_process = []
        for text in texts:
            if text in self.cache:
                result[text] = self.cache[text]
                self.cache_hits += 1
            else:
                to_process.append(text)
                self.cache_misses += 1

        # Обрабатываем новые тексты
        for text in to_process:
            if self.processor.is_person(text):
                result[text] = 'person'
            else:
                result[text] = 'organization'
            self._add_to_cache(text, result[text])

        return result

    def _add_to_cache(self, text: str, result: str):
        """
        Добавление результата в кэш с контролем размера
        """
        if len(self.cache) >= self.cache_size:
            # Очищаем 20% самых старых записей
            items = list(self.cache.items())
            self.cache = dict(items[-int(self.cache_size * 0.8):])

        self.cache[text] = result

    def get_cache_stats(self) -> dict:
        """
        Статистика кэша для отладки
        """
        total = self.cache_hits + self.cache_misses
        return {
            'size': len(self.cache),
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_ratio': self.cache_hits / total if total > 0 else 0
        }

    def clear_cache(self):
        """Очистка кэша для освобождения памяти"""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
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

# ИСПРАВЛЕНО: импортируем из текущего пакета (.text_processor)
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
Поддерживают фильтрацию по диапазону лет
"""

from datetime import datetime
import pandas as pd


def filter_by_registration_year(df, min_year, stdout=None, max_year=None):
    """
    Фильтрация DataFrame по году регистрации с поддержкой диапазона
    
    Args:
        df: DataFrame для фильтрации
        min_year: минимальный год
        stdout: поток вывода
        max_year: максимальный год (опционально)
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

    # Применяем фильтр по годам
    condition = df['_year'] >= min_year
    if max_year:
        condition &= df['_year'] <= max_year
    
    filtered_df = df[condition].copy() if '_year' in df.columns else df.copy()
    
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


def apply_filters(df, min_year, only_active, stdout=None, max_year=None):
    """
    Применение всех фильтров к DataFrame
    
    Args:
        df: DataFrame для фильтрации
        min_year: минимальный год
        only_active: фильтровать только активные
        stdout: поток вывода
        max_year: максимальный год (опционально)
    """
    original_count = len(df)

    if min_year is not None:
        df = filter_by_registration_year(df, min_year, stdout, max_year)

    if only_active:
        df = filter_by_actual(df, stdout)

    filtered_count = len(df)
    if stdout and filtered_count < original_count:
        stdout.write(f"  🔍 Фильтрация: {original_count} → {filtered_count} записей")

    return df
```


-----

# Файл: management\utils\progress.py

```
"""
Утилиты для отображения прогресс-баров
Вынесены отдельно для переиспользования в других парсерах
"""

import sys
from tqdm import tqdm
from contextlib import contextmanager
from typing import Optional, Iterable, Iterator, Any


class ProgressManager:
    """
    Менеджер для работы с прогресс-барами
    Все прогресс-бары отображаются в одной строке (как в оригинальном tqdm)
    """
    
    def __init__(self, enabled: bool = True, file=sys.stdout):
        self.enabled = enabled
        self.file = file
        self._current_bar = None  # Текущий активный прогресс-бар
    
    @contextmanager
    def task(self, description: str, total: Optional[int] = None, unit: str = "элем"):
        """
        Контекстный менеджер для задачи с прогресс-баром
        Все задачи используют одну строку (предыдущая закрывается)
        """
        # Если есть предыдущий бар, закрываем его
        if self._current_bar is not None:
            self._current_bar.close()
        
        # Создаем новый прогресс-бар
        bar = tqdm(
            total=total,
            desc=description,
            unit=unit,
            file=self.file,
            leave=False,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
        
        self._current_bar = bar
        
        try:
            yield bar
        finally:
            bar.close()
            self._current_bar = None
            print(file=self.file)
    
    @contextmanager
    def subtask(self, description: str, total: Optional[int] = None, unit: str = "элем"):
        """Алиас для task (для обратной совместимости)"""
        with self.task(description, total, unit) as bar:
            yield bar
    
    def step(self, message: str):
        """Вывод сообщения о шаге (всегда с новой строки)"""
        if self._current_bar is not None:
            self._current_bar.write(f"🔹 {message}")
        else:
            print(f"🔹 {message}", file=self.file)

    def success(self, message: str):
        """Вывод сообщения об успехе"""
        if self._current_bar is not None:
            self._current_bar.write(f"✅ {message}")
        else:
            print(f"✅ {message}", file=self.file)

    def warning(self, message: str):
        """Вывод предупреждения"""
        if self._current_bar is not None:
            self._current_bar.write(f"⚠️ {message}")
        else:
            print(f"⚠️ {message}", file=self.file)

    def error(self, message: str):
        """Вывод ошибки"""
        if self._current_bar is not None:
            self._current_bar.write(f"❌ {message}")
        else:
            print(f"❌ {message}", file=self.file)


def batch_iterator(iterable, batch_size: int):
    """Разбивает итерируемый объект на батчи"""
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
```


-----

# Файл: management\utils\__init__.py

```
"""
Утилиты для парсеров
"""

from .csv_loader import load_csv_with_strategies
from .filters import apply_filters
from .progress import ProgressManager, batch_iterator

__all__ = [
    'load_csv_with_strategies',
    'apply_filters',
    'ProgressManager',
    'batch_iterator',
]
```