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

    # ============== НОВЫЙ МЕТОД ==============
    def get_years_from_catalogue(self, catalogue):
        """
        Определяет список годов, присутствующих в CSV файле каталога
        С подробным отладочным выводом
        """
        df = self.load_csv(catalogue)
        if df is None or df.empty:
            self.stdout.write(self.style.WARNING("  ⚠️ Не удалось загрузить CSV для определения годов"))
            return []
        
        if 'registration date' not in df.columns:
            self.stdout.write(self.style.WARNING("  ⚠️ Колонка 'registration date' не найдена, не могу определить годы"))
            return []
        
        # Извлекаем годы
        df['_year'] = df['registration date'].apply(self.extract_year_from_date)
        all_years = sorted(df['_year'].dropna().unique().astype(int).tolist())
        
        if not all_years:
            self.stdout.write(self.style.WARNING("  ⚠️ Не удалось извлечь годы из дат"))
            return []
        
        # Подробный отладочный вывод
        self.stdout.write(f"  📊 Все годы в каталоге: {all_years[0]} - {all_years[-1]} (всего {len(all_years)} лет)")
        
        # Показываем первые и последние годы для наглядности
        if len(all_years) > 20:
            self.stdout.write(f"     Первые 10 лет: {all_years[:10]}")
            self.stdout.write(f"     Последние 10 лет: {all_years[-10:]}")
        else:
            self.stdout.write(f"     Все годы: {all_years}")
        
        # Применяем фильтр по минимальному году
        if self.min_year and not self.skip_filters:
            years = [y for y in all_years if y >= self.min_year]
            if years:
                self.stdout.write(f"  🔍 После фильтрации (min_year={self.min_year}): {years[0]} - {years[-1]} (всего {len(years)} лет)")
            else:
                self.stdout.write(f"  🔍 После фильтрации (min_year={self.min_year}): нет данных")
            return years
        else:
            # Если skip_filters=True или min_year не задан, возвращаем все годы
            if self.skip_filters:
                self.stdout.write(f"  🔍 Фильтрация отключена (--skip-filters), обрабатываются все годы")
            return all_years

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
        years = sorted(df['_year'].dropna().unique().astype(int).tolist())
        
        # Применяем фильтр по годам
        if self.min_year:
            years = [y for y in years if y >= self.min_year]
        if self.max_year:
            years = [y for y in years if y <= self.max_year]
        
        # Применяем начальный год, если указан
        if self.start_year and self.start_year in years:
            start_idx = years.index(self.start_year)
            years = years[start_idx:]
        
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
        # Получаем список годов
        years = self.get_years_from_catalogue(catalogue)
        
        if not years:
            self.stdout.write(self.style.WARNING(
                f"  ⚠️ Не удалось определить годы в каталоге, обрабатываем целиком"
            ))
            return self._process_catalogue_normal(catalogue, parser, stats)
        
        self.stdout.write(self.style.SUCCESS(
            f"\n  📅 Найдены годы в каталоге: {years[0]} - {years[-1]} (всего {len(years)} лет)"
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
            
            if self.only_active:
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