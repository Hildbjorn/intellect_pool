# intellectual_property/management/commands/pars_fips_catalogue.py
"""
Команда для парсинга каталогов открытых данных ФИПС Роспатента.
Поддерживает все типы РИД: изобретения, полезные модели, промышленные образцы,
топологии интегральных микросхем, программы для ЭВМ и базы данных.
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm
import pandas as pd
import os
from datetime import datetime

from intellectual_property.models import (
    FipsOpenDataCatalogue, IPType, ProtectionDocumentType,
    IPObject, AdditionalPatent, IPImage
)
from core.models import City, Region, District, Person, Organization, FOIV, Country
from common.utils.text import TextUtils
from common.utils.dates import DateUtils

logger = logging.getLogger(__name__)


class BaseFIPSParser:
    """
    Базовый класс для всех парсеров каталогов ФИПС.
    Содержит общие методы для работы с данными.
    """
    
    def __init__(self, command):
        self.command = command
        self.stdout = command.stdout
        self.style = command.style
        
        # Кэши для оптимизации
        self.country_cache = {}
        self.person_cache = {}
        self.organization_cache = {}
        self.city_cache = {}
        
    def get_ip_type(self):
        """Должен быть переопределен в дочерних классах"""
        raise NotImplementedError
    
    def get_required_columns(self):
        """Возвращает список обязательных колонок для данного типа РИД"""
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
        
        # Пробуем разные форматы
        for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except (ValueError, TypeError):
                continue
        
        # Пробуем автоматическое определение
        try:
            return pd.to_datetime(date_str).date()
        except (ValueError, TypeError):
            return None
    
    def parse_bool(self, value):
        """Парсинг булевого значения"""
        if pd.isna(value) or not value:
            return False
        
        value = str(value).lower().strip()
        return value in ['1', 'true', 'yes', 'да', 'действует', 'true', 't', '1.0', 'активен']
    
    def get_or_create_country(self, code):
        """Получение или создание страны по коду"""
        if not code or pd.isna(code):
            return None
        
        code = str(code).upper().strip()
        if len(code) != 2:
            return None
        
        if code in self.country_cache:
            return self.country_cache[code]
        
        # Словарь для преобразования кодов в названия
        country_names = {
            'RU': ('Россия', 'Russia', 'РФ'),
            'US': ('США', 'USA', 'United States'),
            'DE': ('Германия', 'Germany', 'DE'),
            'FR': ('Франция', 'France', 'FR'),
            'GB': ('Великобритания', 'United Kingdom', 'GB'),
            'CN': ('Китай', 'China', 'CN'),
            'JP': ('Япония', 'Japan', 'JP'),
            'KZ': ('Казахстан', 'Kazakhstan', 'KZ'),
            'BY': ('Беларусь', 'Belarus', 'BY'),
            'UA': ('Украина', 'Ukraine', 'UA'),
        }
        
        try:
            country, created = Country.objects.get_or_create(
                code=code,
                defaults={
                    'name': country_names.get(code, (code, code))[0],
                    'name_en': country_names.get(code, (code, code))[1],
                }
            )
            self.country_cache[code] = country
            return country
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Ошибка создания страны {code}: {e}"))
            return None


class InventionParser(BaseFIPSParser):
    """Парсер для изобретений"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='invention').first()
    
    def get_required_columns(self):
        return ['registration number', 'invention name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с изобретениями"""
        self.stdout.write(self.style.SUCCESS("  Парсер изобретений готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class UtilityModelParser(BaseFIPSParser):
    """Парсер для полезных моделей"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='utility-model').first()
    
    def get_required_columns(self):
        return ['registration number', 'utility model name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с полезными моделями"""
        self.stdout.write(self.style.SUCCESS("  Парсер полезных моделей готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class IndustrialDesignParser(BaseFIPSParser):
    """Парсер для промышленных образцов"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='industrial-design').first()
    
    def get_required_columns(self):
        return ['registration number', 'industrial design name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с промышленными образцами"""
        self.stdout.write(self.style.SUCCESS("  Парсер промышленных образцов готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class IntegratedCircuitTopologyParser(BaseFIPSParser):
    """Парсер для топологий интегральных микросхем"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='integrated-circuit-topology').first()
    
    def get_required_columns(self):
        return ['registration number', 'microchip name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с топологиями микросхем"""
        self.stdout.write(self.style.SUCCESS("  Парсер топологий микросхем готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class ComputerProgramParser(BaseFIPSParser):
    """Парсер для программ для ЭВМ"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='computer-program').first()
    
    def get_required_columns(self):
        return ['registration number', 'program name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с программами для ЭВМ"""
        self.stdout.write(self.style.SUCCESS("  Парсер программ для ЭВМ готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class DatabaseParser(BaseFIPSParser):
    """Парсер для баз данных"""
    
    def get_ip_type(self):
        return IPType.objects.filter(slug='database').first()
    
    def get_required_columns(self):
        return ['registration number', 'db name']
    
    def parse_dataframe(self, df, catalogue):
        """Парсинг DataFrame с базами данных"""
        self.stdout.write(self.style.SUCCESS("  Парсер баз данных готов к работе"))
        # TODO: Реализовать логику парсинга
        return {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


class Command(BaseCommand):
    help = 'Парсинг каталогов открытых данных ФИПС Роспатента'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--catalogue-id',
            type=int,
            help='ID конкретного каталога для парсинга',
        )
        parser.add_argument(
            '--ip-type',
            type=str,
            choices=['invention', 'utility-model', 'industrial-design', 
                    'integrated-circuit-topology', 'computer-program', 'database'],
            help='Тип РИД для парсинга (если не указан, парсятся все)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Режим проверки без сохранения в БД',
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8',
            help='Кодировка CSV файла',
        )
        parser.add_argument(
            '--delimiter',
            type=str,
            default=',',
            help='Разделитель в CSV файле',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Размер пакета для bulk-операций',
        )
        parser.add_argument(
            '--min-year',
            type=int,
            default=2000,
            help='Минимальный год регистрации для фильтрации',
        )
        parser.add_argument(
            '--skip-filters',
            action='store_true',
            help='Пропустить фильтрацию (обработать все записи)',
        )
        parser.add_argument(
            '--only-active',
            action='store_true',
            help='Парсить только активные патенты (actual = True)',
        )
        parser.add_argument(
            '--max-rows',
            type=int,
            help='Максимальное количество строк для обработки (для тестирования)',
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Регистрируем парсеры для каждого типа РИД
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
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД\n"))
        
        if self.only_active:
            self.stdout.write(self.style.WARNING("📌 Режим: парсинг только активных записей (actual = True)"))
        
        # Получаем каталоги для парсинга
        catalogues = self.get_catalogues(options.get('catalogue_id'), options.get('ip_type'))
        
        if not catalogues:
            raise CommandError('Не найдены каталоги для парсинга')
        
        total_stats = {
            'catalogues': len(catalogues),
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Обрабатываем каждый каталог
        for catalogue in catalogues:
            self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
            self.stdout.write(self.style.SUCCESS(f"📁 Обработка каталога: {catalogue.name}"))
            self.stdout.write(self.style.SUCCESS(f"   ID: {catalogue.id}, Тип: {catalogue.ip_type.name if catalogue.ip_type else 'Неизвестно'}"))
            self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
            
            stats = self.process_catalogue(catalogue)
            
            # Обновляем общую статистику
            for key in ['processed', 'created', 'updated', 'skipped', 'errors']:
                total_stats[key] += stats.get(key, 0)
        
        # Выводим итоговую статистику
        self.print_final_stats(total_stats)
    
    def get_catalogues(self, catalogue_id=None, ip_type_slug=None):
        """
        Получение списка каталогов для парсинга.
        Можно получить по ID, по типу РИД или все непрочитанные.
        """
        queryset = FipsOpenDataCatalogue.objects.all()
        
        if catalogue_id:
            queryset = queryset.filter(id=catalogue_id)
        elif ip_type_slug:
            queryset = queryset.filter(ip_type__slug=ip_type_slug)
        else:
            # Если не указаны фильтры, берем все каталоги с файлами
            queryset = queryset.exclude(catalogue_file='')
        
        return queryset.order_by('ip_type__id', '-publication_date')
    
    def process_catalogue(self, catalogue):
        """Обработка одного каталога"""
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        if not catalogue.catalogue_file:
            self.stdout.write(self.style.ERROR(f"  ❌ У каталога ID={catalogue.id} не загружен файл"))
            stats['errors'] += 1
            return stats
        
        # Определяем тип РИД и соответствующий парсер
        ip_type_slug = catalogue.ip_type.slug if catalogue.ip_type else None
        
        if ip_type_slug not in self.parsers:
            self.stdout.write(self.style.ERROR(f"  ❌ Нет парсера для типа РИД: {ip_type_slug}"))
            stats['errors'] += 1
            return stats
        
        parser = self.parsers[ip_type_slug]
        
        # Загружаем CSV в DataFrame
        df = self.load_csv(catalogue)
        
        if df is None or df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Файл пуст или не удалось загрузить"))
            stats['skipped'] += 1
            return stats
        
        self.stdout.write(f"  📊 Загружено записей: {len(df)}")
        
        # Проверяем наличие обязательных колонок
        missing_columns = self.check_required_columns(df, parser.get_required_columns())
        if missing_columns:
            self.stdout.write(self.style.ERROR(f"  ❌ Отсутствуют обязательные колонки: {missing_columns}"))
            stats['errors'] += 1
            return stats
        
        # Применяем фильтры
        if not self.skip_filters:
            df = self.apply_filters(df)
        
        if df.empty:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Нет данных после фильтрации"))
            stats['skipped'] += 1
            return stats
        
        self.stdout.write(f"  📊 После фильтрации: {len(df)} записей")
        
        # Ограничиваем количество строк для тестирования
        if self.max_rows and len(df) > self.max_rows:
            df = df.head(self.max_rows)
            self.stdout.write(self.style.WARNING(f"  ⚠️ Ограничено до {self.max_rows} записей для тестирования"))
        
        # Запускаем парсер
        try:
            parser_stats = parser.parse_dataframe(df, catalogue)
            stats.update(parser_stats)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка при парсинге: {e}"))
            logger.error(f"Error parsing catalogue {catalogue.id}: {e}", exc_info=True)
            stats['errors'] += 1
        
        return stats
    
    def load_csv(self, catalogue):
        """Загрузка CSV файла в DataFrame"""
        file_path = catalogue.catalogue_file.path
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"  ❌ Файл не найден: {file_path}"))
            return None
        
        try:
            # Пробуем разные стратегии загрузки
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
                    
                    # Очищаем названия колонок от лишних символов
                    df.columns = [col.strip().strip('\ufeff').strip('"') for col in df.columns]
                    
                    return df
                except Exception as e:
                    continue
            
            raise Exception("Не удалось загрузить CSV ни одной стратегией")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Ошибка загрузки CSV: {e}"))
            return None
    
    def check_required_columns(self, df, required_columns):
        """Проверка наличия обязательных колонок"""
        missing = [col for col in required_columns if col not in df.columns]
        return missing
    
    def apply_filters(self, df):
        """Применение фильтров к DataFrame"""
        original_count = len(df)
        
        # Фильтр по году регистрации
        if 'registration date' in df.columns:
            df = self.filter_by_registration_year(df)
        
        # Фильтр по активности
        if self.only_active and 'actual' in df.columns:
            df = self.filter_by_actual(df)
        
        filtered_count = len(df)
        if filtered_count < original_count:
            self.stdout.write(f"  🔍 Фильтрация: {original_count} → {filtered_count} записей")
        
        return df
    
    def filter_by_registration_year(self, df):
        """Фильтрация по году регистрации"""
        def extract_year(date_str):
            try:
                # Используем парсер из базового класса через парсер
                # Но так как мы в Command, используем прямой парсинг
                if pd.isna(date_str) or not date_str:
                    return None
                
                date_str = str(date_str).strip()
                if not date_str:
                    return None
                
                # Пробуем разные форматы
                for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                    try:
                        return datetime.strptime(date_str, fmt).year
                    except (ValueError, TypeError):
                        continue
                
                # Пробуем автоматическое определение
                try:
                    return pd.to_datetime(date_str).year
                except (ValueError, TypeError):
                    return None
            except:
                return None
        
        self.stdout.write("  🔍 Фильтрация по году регистрации...")
        df['_year'] = df['registration date'].apply(extract_year)
        
        # Статистика по годам
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
        """Фильтрация по признаку actual = True"""
        def parse_actual(value):
            if pd.isna(value) or not value:
                return False
            value = str(value).lower().strip()
            return value in ['1', 'true', 'yes', 'да', 'действует', 'true', 't', '1.0', 'активен']
        
        df['_actual'] = df['actual'].apply(parse_actual)
        filtered_df = df[df['_actual'] == True].copy()
        filtered_df.drop('_actual', axis=1, inplace=True)
        
        return filtered_df
    
    def print_final_stats(self, stats):
        """Вывод итоговой статистики"""
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("📊 ИТОГОВАЯ СТАТИСТИКА"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
        self.stdout.write(f"📁 Обработано каталогов: {stats['catalogues']}")
        self.stdout.write(f"📝 Всего записей обработано: {stats['processed']}")
        self.stdout.write(f"✅ Создано: {stats['created']}")
        self.stdout.write(f"🔄 Обновлено: {stats['updated']}")
        self.stdout.write(f"⏭️  Пропущено: {stats['skipped']}")
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Ошибок: {stats['errors']}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Ошибок: {stats['errors']}"))
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены в БД"))
        
        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))