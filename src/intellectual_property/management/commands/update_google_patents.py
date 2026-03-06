"""
Команда для обновления данных РИД путем прямого парсинга Google Patents.
Поддерживает все типы РИД с соответствующими полями для каждого типа.

Использует requests для получения HTML страниц и BeautifulSoup для парсинга.

Логика работы:
- --force: начинает с начала (обрабатывает все записи подряд)
- обычный запуск: находит первую запись с пустыми полями и начинает с неё

Мимикрия под реального пользователя:
- Ротация User-Agent
- Умные задержки между запросами
- Обработка rate limiting
"""

import logging
import re
import time
import random
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from tqdm import tqdm
from bs4 import BeautifulSoup

from intellectual_property.models import IPObject, IPType, ProgrammingLanguage, DBMS

logger = logging.getLogger(__name__)


class RateLimitException(Exception):
    """Исключение для слишком быстрых запросов"""
    pass


class Command(BaseCommand):
    help = 'Обновление данных РИД прямым парсингом Google Patents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ip-type',
            type=str,
            choices=[
                'invention', 'utility-model', 'industrial-design',
                'integrated-circuit-topology', 'computer-program', 'database', 'all'
            ],
            default='all',
            help='Тип РИД для обработки (по умолчанию all - все типы)'
        )

        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Размер пакета для обработки (по умолчанию 100)'
        )

        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Базовая задержка между запросами в секундах (по умолчанию 2.0)'
        )

        parser.add_argument(
            '--random-delay',
            action='store_true',
            default=True,
            help='Использовать случайную задержку (включено по умолчанию)'
        )

        parser.add_argument(
            '--max-requests',
            type=int,
            default=None,
            help='Максимальное количество запросов (для тестирования)'
        )

        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Режим проверки без сохранения в БД'
        )

        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительное обновление с начала (обрабатывает все записи подряд, даже если поля заполнены)'
        )

        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Таймаут запроса в секундах (по умолчанию 30)'
        )

        parser.add_argument(
            '--start-from-latest',
            action='store_true',
            default=True,
            help='Начинать с последних по дате регистрации (по умолчанию True)'
        )

        parser.add_argument(
            '--start-from-oldest',
            action='store_true',
            help='Начинать с самых старых записей (переопределяет --start-from-latest)'
        )

        parser.add_argument(
            '--start-from-id',
            type=int,
            help='Начать обработку с конкретного ID (переопределяет автоматическое определение)'
        )

        parser.add_argument(
            '--human-mode',
            action='store_true',
            default=True,
            help='Максимальная мимикрия под человека (включено по умолчанию)'
        )

        parser.add_argument(
            '--no-human-mode',
            action='store_false',
            dest='human_mode',
            help='Отключить мимикрию под человека (для тестирования)'
        )

        parser.add_argument(
            '--prefer-russian',
            action='store_true',
            default=True,
            help='Предпочитать русские тексты (включено по умолчанию)'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Соответствие типов РИД и их слагов
        self.type_slugs = {
            'invention': 'invention',
            'utility-model': 'utility-model',
            'industrial-design': 'industrial-design',
            'integrated-circuit-topology': 'integrated-circuit-topology',
            'computer-program': 'computer-program',
            'database': 'database',
        }

        # Карта полей для каждого типа РИД
        self.type_fields_map = {
            'invention': {
                'abstract': {'target': 'abstract', 'is_main': True},
                'description': {'target': 'description', 'is_main': True},
                'claims': {'target': 'claims', 'is_main': True},
            },
            'utility-model': {
                'abstract': {'target': 'abstract', 'is_main': True},
                'description': {'target': 'description', 'is_main': True},
                'claims': {'target': 'claims', 'is_main': True},
            },
            'industrial-design': {
                'abstract': {'target': 'abstract', 'is_main': True},
                'description': {'target': 'description', 'is_main': True},
            },
            'integrated-circuit-topology': {
                'abstract': {'target': 'abstract', 'is_main': True},
                'description': {'target': 'description', 'is_main': True},
            },
            'computer-program': {
                'abstract': {'target': 'abstract', 'is_main': True},
                'description': {'target': 'description', 'is_main': True},
                'programming_languages': {'target': 'programming_languages', 'is_m2m': True},
            },
            'database': {
                'abstract': {'target': 'abstract', 'is_main': True},
                'description': {'target': 'description', 'is_main': True},
                'dbms': {'target': 'dbms', 'is_m2m': True},
            },
        }

        # Статистика
        self.stats = {
            'total': 0,
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'rate_limited': 0,
            'special_messages': 0,
            'by_type': {},
        }

        self.session = None
        self.request_count = 0
        self.start_id = None

        # Пул современных User-Agent'ов
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]

        # Варианты Accept-Language
        self.accept_languages = [
            'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'ru,en-US;q=0.9,en;q=0.8,uk;q=0.7',
            'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
            'en-US,en;q=0.9,ru;q=0.8',
        ]

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        self.batch_size = options['batch_size']
        self.delay = options['delay']
        self.random_delay = options['random_delay']
        self.max_requests = options['max_requests']
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.timeout = options['timeout']
        self.start_from_id = options['start_from_id']
        self.human_mode = options['human_mode']
        self.prefer_russian = options.get('prefer_russian', True)

        if options['start_from_oldest']:
            self.order_by = 'registration_date'
            self.order_desc = False
            order_text = "от старых к новым"
        else:
            self.order_by = 'registration_date'
            self.order_desc = True
            order_text = "от новых к старым"

        ip_type_param = options['ip_type']

        self.print_header(order_text)
        self.init_session()

        type_slugs_to_process = self.get_type_slugs(ip_type_param)

        for slug in type_slugs_to_process:
            self.stats['by_type'][slug] = {
                'total': 0, 'success': 0, 'failed': 0,
                'rate_limited': 0, 'special': 0
            }

        try:
            self.run_processing(type_slugs_to_process)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n\n⏹️ Обработка прервана пользователем"))
            self.print_final_stats()
            sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n💥 Критическая ошибка: {e}"))
            logger.error(f"Critical error: {e}", exc_info=True)
            self.print_final_stats()
            sys.exit(1)

    def print_header(self, order_text):
        """Вывод заголовка"""
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("🚀 ЗАПУСК ОБНОВЛЕНИЯ ДАННЫХ РИД ИЗ GOOGLE PATENTS"))
        self.stdout.write(self.style.SUCCESS("="*80))

        if self.force:
            self.stdout.write(self.style.WARNING("\n📌 РЕЖИМ: принудительное обновление с начала (--force)"))

        self.stdout.write(f"\n📌 Порядок обработки: {order_text}")
        self.stdout.write(f"📌 Предпочитать русские тексты: {'ДА' if self.prefer_russian else 'НЕТ'}")

        if self.human_mode:
            self.stdout.write(f"📌 Мимикрия под человека: ВКЛЮЧЕНА")
            self.stdout.write(f"   • Ротация User-Agent: {len(self.user_agents)} вариантов")
            self.stdout.write(f"   • Умные задержки с длинными паузами")
        else:
            self.stdout.write(f"📌 Мимикрия под человека: ОТКЛЮЧЕНА")

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД\n"))

    def get_type_slugs(self, ip_type_param):
        """Получение списка слагов типов для обработки"""
        if ip_type_param == 'all':
            type_slugs = list(self.type_slugs.values())
            self.stdout.write(f"📋 Обработка всех типов РИД: {', '.join(type_slugs)}")
            return type_slugs
        else:
            type_slugs = [self.type_slugs[ip_type_param]]
            self.stdout.write(f"📋 Обработка типа РИД: {ip_type_param}")
            return type_slugs

    def init_session(self):
        """Инициализация HTTP-сессии"""
        self.session = requests.Session()
        
        # Базовые заголовки
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': random.choice(self.accept_languages),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def rotate_headers(self):
        """Ротация заголовков для каждого запроса"""
        if not self.human_mode:
            return

        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept-Language': random.choice(self.accept_languages),
        })

    def apply_delay(self):
        """Умная задержка между запросами"""
        if self.delay <= 0:
            return

        if not self.human_mode:
            time.sleep(self.delay)
            return

        # Периодические длинные паузы
        if self.request_count % random.randint(30, 70) == 0 and self.request_count > 0:
            long_delay = random.uniform(10, 40)
            if self.verbosity >= 1:
                self.stdout.write(f"\n   💤 ДЛИННАЯ ПАУЗА {long_delay:.1f} сек... (после {self.request_count} запросов)")
            time.sleep(long_delay)
            return

        if self.request_count % random.randint(10, 20) == 0 and self.request_count > 0:
            medium_delay = random.uniform(5, 20)
            if self.verbosity >= 2:
                self.stdout.write(f"\n   ⏱️ ПАУЗА {medium_delay:.1f} сек (изучение)...")
            time.sleep(medium_delay)
            return

        base_delay = self.delay * random.uniform(0.7, 2.5)
        time.sleep(base_delay)

    def get_queryset(self, type_slugs):
        """Получение queryset для обработки"""
        ip_types = IPType.objects.filter(slug__in=type_slugs)

        queryset = IPObject.objects.filter(
            ip_type__in=ip_types,
            registration_number__isnull=False
        ).exclude(
            registration_number=''
        ).select_related('ip_type')

        if self.start_from_id:
            self.start_id = self.start_from_id
            self.stdout.write(self.style.WARNING(f"🎯 Старт с явно указанного ID: {self.start_id}"))
            queryset = queryset.filter(id__gte=self.start_id)
        elif self.force:
            self.stdout.write(self.style.WARNING("🎯 Режим --force: начинаем с начала, обрабатываем все записи"))
        else:
            self.start_id = self.find_first_empty_record(queryset, ip_types)

            if self.start_id:
                self.stdout.write(self.style.WARNING(
                    f"🎯 Начинаем с ID {self.start_id} (первая запись с пустыми полями)"
                ))
                queryset = queryset.filter(id__gte=self.start_id)
            else:
                self.stdout.write(self.style.SUCCESS("✅ Все записи имеют заполненные поля! Обновлять нечего."))
                return IPObject.objects.none()

        if self.order_by:
            order_field = self.order_by
            if self.order_desc:
                order_field = f'-{order_field}'
            queryset = queryset.order_by(order_field)

        return queryset

    def find_first_empty_record(self, queryset, ip_types):
        """Находит первую запись с пустыми полями"""
        types_with_fields = []
        for ip_type in ip_types:
            fields_map = self.type_fields_map.get(ip_type.slug, {})
            if fields_map:
                types_with_fields.append(ip_type)
        
        if not types_with_fields:
            self.stdout.write(self.style.WARNING("⚠️ Нет типов РИД с полями для парсинга"))
            return None
        
        order_by = '-registration_date' if self.order_desc else 'registration_date'
        
        # Строим условия для проверки пустых полей
        empty_conditions = Q()
        for ip_type in types_with_fields:
            fields_map = self.type_fields_map.get(ip_type.slug, {})
            type_conditions = Q(ip_type=ip_type) & (
                Q(abstract__isnull=True) | Q(abstract='') |
                Q(description__isnull=True) | Q(description='') |
                Q(claims__isnull=True) | Q(claims='')
            )
            empty_conditions |= type_conditions
        
        empty_qs = IPObject.objects.filter(
            registration_number__isnull=False
        ).exclude(
            registration_number=''
        ).filter(empty_conditions).order_by(order_by, 'id')
        
        first_empty = empty_qs.first()
        return first_empty.id if first_empty else None

    def run_processing(self, type_slugs_to_process):
        """Запуск обработки"""
        queryset = self.get_queryset(type_slugs_to_process)
        self.stats['total'] = queryset.count()

        self.stdout.write(f"\n📊 Найдено записей для обработки: {self.stats['total']}")

        if self.stats['total'] == 0:
            self.stdout.write(self.style.WARNING("⚠️ Нет записей для обработки"))
            return

        self.process_in_batches(queryset)
        self.print_final_stats()

    def format_patent_number(self, registration_number):
        """
        Форматирование номера патента для Google Patents.
        Всегда добавляет префикс RU, если его нет.
        """
        # Очищаем номер от лишних символов
        clean_number = re.sub(r'[^\w]', '', registration_number)
        
        # Убираем возможный префикс RU для унификации
        clean_number = re.sub(r'^RU', '', clean_number, flags=re.IGNORECASE)
        
        # Всегда добавляем RU
        return f"RU{clean_number}"

    def process_in_batches(self, queryset):
        """Обработка записей по батчам"""
        total = queryset.count()

        if self.max_requests and self.max_requests < total:
            self.stdout.write(self.style.WARNING(
                f"\n⏹️ Будет обработано только {self.max_requests} записей из {total} (лимит запросов)"
            ))
            queryset = queryset[:self.max_requests]
            total = self.max_requests

        with tqdm(total=total, desc="Обработка записей", unit="зап") as pbar:
            for ip_object in queryset.iterator(chunk_size=self.batch_size):
                if self.max_requests and self.request_count >= self.max_requests:
                    self.stdout.write(self.style.WARNING(f"\n⏹️ Достигнут лимит запросов ({self.max_requests})"))
                    return

                try:
                    self.process_single_object(ip_object)
                except RateLimitException:
                    self.stats['rate_limited'] += 1
                    type_slug = ip_object.ip_type.slug
                    if type_slug in self.stats['by_type']:
                        self.stats['by_type'][type_slug]['rate_limited'] += 1
                    
                    if self.verbosity >= 1:
                        self.stdout.write(self.style.WARNING(
                            "\n   ⏳ Rate limit. Пауза 60 сек..."
                        ))
                    time.sleep(60)
                except Exception as e:
                    self.stats['errors'] += 1
                    if self.verbosity >= 1:
                        self.stdout.write(self.style.ERROR(f"\n❌ Неожиданная ошибка: {e}"))
                    logger.error(f"Unexpected error processing IPObject {ip_object.id}: {e}", exc_info=True)

                pbar.update(1)
                pbar.set_postfix({
                    'OK': self.stats['success'],
                    'ERR': self.stats['failed'],
                    'SPC': self.stats['special_messages'],
                    'RTL': self.stats['rate_limited'],
                    'REQ': self.request_count
                })

                self.apply_delay()

    def process_single_object(self, ip_object):
        """Обработка одного объекта РИД"""
        self.stats['processed'] += 1
        type_slug = ip_object.ip_type.slug

        self.stats['by_type'][type_slug]['total'] += 1

        if self.verbosity >= 2:
            reg_date = ip_object.registration_date.strftime('%d.%m.%Y') if ip_object.registration_date else 'нет даты'
            self.stdout.write(f"\n🔍 Обработка ID={ip_object.id}, тип={type_slug}, дата={reg_date}")
            self.stdout.write(f"   Рег. номер: {ip_object.registration_number}")

        if not ip_object.registration_number:
            self.stats['skipped'] += 1
            return

        # Форматируем номер патента (всегда с RU)
        patent_number = self.format_patent_number(ip_object.registration_number)
        url = f"https://patents.google.com/patent/{patent_number}"
        
        if self.verbosity >= 2:
            self.stdout.write(f"   🔗 URL: {url}")

        fields_map = self.type_fields_map.get(type_slug, {})

        if not fields_map:
            self.stats['skipped'] += 1
            return

        # Проверка на необходимость обновления
        if not self.force:
            needs_update = False
            for target_field in fields_map.keys():
                if target_field in ['programming_languages', 'dbms']:
                    if not getattr(ip_object, target_field).exists():
                        needs_update = True
                        break
                else:
                    current_value = getattr(ip_object, target_field)
                    if not current_value or not current_value.strip():
                        needs_update = True
                        break
            
            if not needs_update:
                if self.verbosity >= 2:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Все поля уже заполнены, пропуск"))
                self.stats['skipped'] += 1
                return

        # Ротируем заголовки
        self.rotate_headers()
        self.request_count += 1

        try:
            # Прямой запрос к странице
            html_content = self.fetch_patent_page(url)
            
            if not html_content:
                self.stats['failed'] += 1
                self.stats['by_type'][type_slug]['failed'] += 1
                return

            # Проверяем, не вернулась ли страница с ошибкой
            if len(html_content) < 1000 and "Документ с данным номером отсутствует" in html_content:
                self.stats['special_messages'] += 1
                self.stats['by_type'][type_slug]['special'] += 1
                
                parsed_data = {
                    'abstract': {
                        'value': f"[ОТВЕТ СЕРВЕРА] Документ с данным номером отсутствует",
                        'is_m2m': False
                    }
                }
                
                updated = self.update_object(ip_object, parsed_data, fields_map)
                
                if updated:
                    self.stats['success'] += 1
                    self.stats['by_type'][type_slug]['success'] += 1
                else:
                    self.stats['skipped'] += 1
                
                return

            # Парсим HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Извлекаем данные
            parsed_data = self.parse_all_fields(soup, fields_map)
            
            if parsed_data:
                updated = self.update_object(ip_object, parsed_data, fields_map)
                
                if updated:
                    self.stats['success'] += 1
                    self.stats['by_type'][type_slug]['success'] += 1
                    
                    if self.verbosity >= 2:
                        fields_updated = ', '.join(parsed_data.keys())
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Данные обновлены: {fields_updated}"))
                else:
                    self.stats['skipped'] += 1
                    if self.verbosity >= 2:
                        self.stdout.write("   ℹ️ Нет изменений")
            else:
                self.stats['failed'] += 1
                self.stats['by_type'][type_slug]['failed'] += 1
                if self.verbosity >= 2:
                    self.stdout.write(self.style.WARNING("   ⚠️ Не удалось извлечь данные"))

        except Exception as e:
            self.stats['errors'] += 1
            self.stats['failed'] += 1
            self.stats['by_type'][type_slug]['failed'] += 1

            if self.verbosity >= 1:
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка: {e}"))
            logger.error(f"Error processing IPObject {ip_object.id}: {e}", exc_info=True)

    def fetch_patent_page(self, url):
        """Прямой запрос к Google Patents"""
        try:
            if self.verbosity >= 2:
                self.stdout.write(f"   📡 Запрос к {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 429:
                raise RateLimitException()
            
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            if self.verbosity >= 3:
                self.stdout.write(f"   📄 Получено {len(response.text)} символов")
            
            return response.text
            
        except RateLimitException:
            raise
        except Exception as e:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка запроса: {e}"))
            return None

    def parse_all_fields(self, soup, fields_map):
        """Парсинг всех полей из BeautifulSoup объекта"""
        result = {}
        
        if self.verbosity >= 3:
            self.stdout.write(f"      🔍 parse_all_fields: fields_map keys = {list(fields_map.keys())}")
        
        for target_field in fields_map.keys():
            if self.verbosity >= 3:
                self.stdout.write(f"      🔍 Обработка поля: {target_field}")
            
            if target_field == 'abstract':
                value = self.parse_abstract(soup)
            elif target_field == 'description':
                value = self.parse_description(soup)
            elif target_field == 'claims':
                value = self.parse_claims(soup)
            elif target_field == 'programming_languages':
                value = self.parse_programming_languages(soup)
            elif target_field == 'dbms':
                value = self.parse_dbms(soup)
            else:
                continue
            
            if value:
                result[target_field] = {
                    'value': value,
                    'is_m2m': target_field in ['programming_languages', 'dbms']
                }
                if self.verbosity >= 2:
                    preview = str(value)[:100] + '...' if len(str(value)) > 100 else str(value)
                    self.stdout.write(f"      ✅ Найдено {target_field}: {preview}")
            else:
                if self.verbosity >= 2:
                    self.stdout.write(f"      ❌ {target_field} не найден")
        
        return result if result else None

    def parse_abstract(self, soup):
        """Извлечение реферата"""
        if not soup:
            return None
        
        # СПОСОБ 1: Ищем abstract с lang="RU"
        abstract_elem = soup.find('abstract', {'lang': 'RU'})
        if abstract_elem:
            texts = []
            for div in abstract_elem.find_all('div'):
                text = div.get_text(strip=True)
                if text and self.contains_cyrillic(text):
                    texts.append(text)
            
            if texts:
                full_text = '\n\n'.join(texts)
                # Убираем слово "Abstract" в начале, если оно есть
                full_text = self.remove_header(full_text, 'Abstract')
                return self.clean_text(full_text)
        
        # СПОСОБ 2: Ищем в секции с заголовком
        abstract_header = soup.find(['h2', 'h3'], string=re.compile(r'Abstract', re.I))
        if abstract_header:
            parent = abstract_header.find_parent()
            if parent:
                text = parent.get_text(strip=True)
                if text and self.contains_cyrillic(text):
                    # Убираем заголовок
                    header_text = abstract_header.get_text(strip=True)
                    if text.startswith(header_text):
                        text = text[len(header_text):].strip()
                    return self.clean_text(text)
        
        return None

    def parse_description(self, soup):
        """Извлечение описания"""
        if not soup:
            return None
        
        # СПОСОБ 1: Ищем description с lang="RU"
        desc_elem = soup.find('description', {'lang': 'RU'})
        if desc_elem:
            texts = []
            for p in desc_elem.find_all('div', class_='description-paragraph'):
                text = p.get_text(strip=True)
                if text and self.contains_cyrillic(text):
                    # Убираем номер параграфа
                    text = re.sub(r'^\s*\d+\s+', '', text)
                    texts.append(text)
            
            if texts:
                full_text = '\n\n'.join(texts)
                # Убираем слово "Description" в начале, если оно есть
                full_text = self.remove_header(full_text, 'Description')
                return self.clean_text(full_text)
        
        # СПОСОБ 2: Ищем секцию с заголовком "Description"
        desc_header = soup.find(['h2', 'h3'], string=re.compile(r'Description', re.I))
        if desc_header:
            parent = desc_header.find_parent('section')
            if parent:
                text = parent.get_text(strip=True)
                if text and self.contains_cyrillic(text):
                    # Убираем заголовок "Description" из текста
                    header_text = desc_header.get_text(strip=True)
                    if text.startswith(header_text):
                        text = text[len(header_text):].strip()
                    return self.clean_text(text)
        
        return None

    def parse_claims(self, soup):
        """Извлечение формулы"""
        if not soup:
            return None
        
        # СПОСОБ 1: Ищем claims с lang="RU"
        claims_elem = soup.find('claims', {'lang': 'RU'})
        if claims_elem:
            texts = []
            for claim in claims_elem.find_all('div', class_='claim'):
                claim_text = claim.find('div', class_='claim-text')
                if claim_text:
                    text = claim_text.get_text(strip=True)
                    if text and self.contains_cyrillic(text):
                        texts.append(text)
            
            if texts:
                full_text = '\n\n'.join(texts)
                # Убираем слово "Claims" в начале, если оно есть
                full_text = self.remove_header(full_text, 'Claims')
                return self.clean_text(full_text)
        
        # СПОСОБ 2: Ищем секцию с заголовком "Claims"
        claims_header = soup.find(['h2', 'h3'], string=re.compile(r'Claims', re.I))
        if claims_header:
            parent = claims_header.find_parent('section')
            if parent:
                text = parent.get_text(strip=True)
                if text and self.contains_cyrillic(text):
                    # Убираем заголовок
                    header_text = claims_header.get_text(strip=True)
                    if text.startswith(header_text):
                        text = text[len(header_text):].strip()
                    return self.clean_text(text)
        
        return None

    def remove_header(self, text, header):
        """Удаляет заголовок из начала текста, если он там есть"""
        if not text or not header:
            return text
        
        # Проверяем разные варианты написания
        patterns = [
            rf'^{header}\s*',           # "Description" в начале
            rf'^{header}:\s*',          # "Description:" в начале
            rf'^{header}\s+translated\s+from\s*',  # "Description translated from"
            rf'^{header}\s+translated\s+from:?\s*', # "Description translated from:"
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                break
        
        return text.strip()

    def parse_programming_languages(self, soup):
        """Извлечение языков программирования"""
        if not soup:
            return None
        
        text = soup.get_text()
        
        prog_langs = [
            'Python', 'Java', 'C++', 'JavaScript', 'C#', 'PHP', 'Ruby', 
            'Swift', 'Kotlin', 'Go', 'Rust', 'TypeScript', 'Perl', 'Scala',
        ]
        
        found_langs = []
        for lang in prog_langs:
            if re.search(rf'\b{re.escape(lang)}\b', text, re.I):
                found_langs.append(lang)
        
        return found_langs if found_langs else None

    def parse_dbms(self, soup):
        """Извлечение СУБД"""
        if not soup:
            return None
        
        text = soup.get_text()
        
        dbms_list = [
            'MySQL', 'PostgreSQL', 'Oracle', 'Microsoft SQL Server', 'SQLite',
            'MongoDB', 'Redis', 'Cassandra', 'MariaDB', 'DB2',
        ]
        
        found_dbms = []
        for dbms in dbms_list:
            if re.search(rf'\b{re.escape(dbms)}\b', text, re.I):
                found_dbms.append(dbms)
        
        return found_dbms if found_dbms else None

    def contains_cyrillic(self, text):
        """Проверяет, содержит ли текст кириллицу"""
        if not text or not isinstance(text, str):
            return False
        return bool(re.search('[а-яА-Я]', text))

    def clean_text(self, text):
        """Очистка текста от лишних символов"""
        if not text or not isinstance(text, str):
            return text
        
        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        # Удаляем множественные пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text)
        # Удаляем пробелы в начале и конце
        text = text.strip()
        
        return text

    def update_object(self, ip_object, parsed_data, fields_map):
        """Обновление объекта РИД"""
        if self.dry_run:
            if self.verbosity >= 2:
                self.stdout.write("   📝 DRY-RUN: данные для обновления:")
                for target_field, field_data in parsed_data.items():
                    new_value = field_data['value']
                    
                    if field_data.get('is_m2m', False):
                        current = list(getattr(ip_object, target_field).all())
                        self.stdout.write(f"      {target_field}: {current} -> {new_value}")
                    else:
                        preview = str(new_value)[:100] + '...' if len(str(new_value)) > 100 else str(new_value)
                        self.stdout.write(f"      {target_field}: '{preview}'")
            return True

        updated = False

        with transaction.atomic():
            for target_field, field_data in parsed_data.items():
                value = field_data['value']
                is_m2m = field_data.get('is_m2m', False)

                if is_m2m:
                    if target_field == 'programming_languages':
                        updated |= self.update_m2m_field(ip_object, ProgrammingLanguage, 'programming_languages', value)
                    elif target_field == 'dbms':
                        updated |= self.update_m2m_field(ip_object, DBMS, 'dbms', value)
                else:
                    current_value = getattr(ip_object, target_field)

                    if self.force or current_value != value:
                        setattr(ip_object, target_field, value)
                        updated = True

            if updated:
                update_fields = list(parsed_data.keys())
                ip_object.save(update_fields=update_fields)

        return updated

    def update_m2m_field(self, ip_object, model_class, field_name, values):
        """Обновление ManyToMany поля"""
        if not values:
            return False

        manager = getattr(ip_object, field_name)
        objects_to_add = []

        for value in values:
            if isinstance(value, str) and value.strip():
                obj, _ = model_class.objects.get_or_create(name=value.strip())
                objects_to_add.append(obj)

        if objects_to_add:
            if self.force:
                manager.clear()
                manager.add(*objects_to_add)
                return True
            else:
                existing = set(manager.all())
                new_objects = [obj for obj in objects_to_add if obj not in existing]
                if new_objects:
                    manager.add(*new_objects)
                    return True

        return False

    def print_final_stats(self):
        """Вывод итоговой статистики"""
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("📊 ИТОГОВАЯ СТАТИСТИКА"))
        self.stdout.write(self.style.SUCCESS("="*80))

        self.stdout.write(f"📁 Всего записей: {self.stats['total']}")
        self.stdout.write(f"📝 Обработано: {self.stats['processed']}")
        self.stdout.write(f"✅ Успешно обновлено: {self.stats['success']}")

        if self.stats['special_messages'] > 0:
            self.stdout.write(f"📝 Специальных сообщений: {self.stats['special_messages']}")

        if self.stats['rate_limited'] > 0:
            self.stdout.write(f"⏳ Срабатываний rate limit: {self.stats['rate_limited']}")

        self.stdout.write(f"❌ Неудачно: {self.stats['failed']}")
        self.stdout.write(f"⏭️  Пропущено: {self.stats['skipped']}")

        if self.stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"💥 Ошибок: {self.stats['errors']}"))

        self.stdout.write(f"📡 Выполнено запросов: {self.request_count}")

        if self.start_id:
            self.stdout.write(f"🎯 Стартовая позиция: ID {self.start_id}")

        if any(stats['total'] > 0 for stats in self.stats['by_type'].values()):
            self.stdout.write(self.style.SUCCESS("\n📊 ПО ТИПАМ РИД:"))
            for type_slug, stats in self.stats['by_type'].items():
                if stats['total'] > 0:
                    success_rate = (stats['success'] / stats['total']) * 100 if stats['total'] > 0 else 0
                    special_info = f", спец={stats['special']}" if stats['special'] > 0 else ""
                    rate_info = f", rate={stats['rate_limited']}" if stats['rate_limited'] > 0 else ""
                    self.stdout.write(
                        f"   {type_slug}: всего={stats['total']}, "
                        f"✅={stats['success']}, ❌={stats['failed']}{special_info}{rate_info}, "
                        f"({success_rate:.1f}%)"
                    )

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены в БД"))

        self.stdout.write(self.style.SUCCESS("="*80))