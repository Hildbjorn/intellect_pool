"""
Команда для обновления данных РИД путем парсинга страниц ФИПС по publication_url.
Поддерживает все типы РИД с соответствующими полями для каждого типа.

Логика работы:
- --force: начинает с начала (обрабатывает все записи подряд)
- --only-actual: обновляет только поле actual по всем записям
- обычный запуск: находит первую запись с пустым abstract и начинает с неё

Мимикрия под реального пользователя:
- Ротация User-Agent (пул современных браузеров)
- Разнообразные Accept-Language заголовки
- Эмуляция полной браузерной сессии
- Умные задержки с длинными паузами
- Случайные вариации в заголовках

Обработка специальных сообщений:
- Блокировка → остановка парсера
- "Слишком быстрый просмотр" → пауза 60 сек и повтор
- "Документ с данным номером отсутствует" → запись в поле abstract
- Другие короткие ответы → запись в поле abstract как ошибка
"""

import logging
import re
import time
import random
import sys
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models
from django.db.models import Q, F
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType, ProgrammingLanguage, DBMS
from django.conf import settings

logger = logging.getLogger(__name__)


class BlockDetectedException(Exception):
    """Исключение, возникающее при обнаружении блокировки"""
    pass


class RateLimitException(Exception):
    """Исключение для слишком быстрых запросов"""
    pass


class Command(BaseCommand):
    help = 'Обновление данных РИД парсингом страниц ФИПС по publication_url'

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
            '--only-actual',
            action='store_true',
            help='Обновлять только поле actual (статус) по всем записям'
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
            '--block-retry-delay',
            type=int,
            default=3600,
            help='Задержка перед повторной попыткой после блокировки в секундах (по умолчанию 3600 - 1 час)'
        )

        parser.add_argument(
            '--auto-retry-after-block',
            action='store_true',
            help='Автоматически повторять попытку после блокировки через указанную задержку'
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
                'abstract': {'source': 'parse_abstract', 'target': 'abstract', 'is_main': True},
                'claims': {'source': 'parse_claims', 'target': 'claims', 'is_main': True},
                'actual': {'source': 'parse_status', 'target': 'actual'},
            },
            'utility-model': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract', 'is_main': True},
                'claims': {'source': 'parse_claims', 'target': 'claims', 'is_main': True},
                'actual': {'source': 'parse_status', 'target': 'actual'},
            },
            'industrial-design': {
                'actual': {'source': 'parse_status', 'target': 'actual'},
            },
            'integrated-circuit-topology': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract', 'is_main': True},
            },
            'computer-program': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract', 'is_main': True},
                'programming_languages': {'source': 'parse_programming_languages', 'target': 'programming_languages', 'is_m2m': True},
            },
            'database': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract', 'is_main': True},
                'dbms': {'source': 'parse_dbms', 'target': 'dbms', 'is_m2m': True},
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
            'actual_updated': 0,
            'blocked': 0,
            'rate_limited': 0,
            'special_messages': 0,
            'by_type': {},
        }

        self.session = None
        self.request_count = 0
        self.block_detected = False
        self.block_info = {}
        self.start_id = None

        # ========== НАСТРОЙКИ МИМИКРИИ ==========

        # Пул современных User-Agent'ов (без изменений)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/121.0 Firefox/121.0',
        ]

        # Варианты Accept-Language
        self.accept_languages = [
            'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'ru,en-US;q=0.9,en;q=0.8,uk;q=0.7',
            'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
            'en-US,en;q=0.9,ru;q=0.8',
            'ru,en;q=0.9,uk;q=0.8',
            'ru-RU,ru;q=0.9,en;q=0.5',
            'ru,en;q=0.8',
        ]

        # Варианты Accept
        self.accept_variants = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        ]

        # Заголовки Sec-Fetch
        self.sec_fetch_dest = ['document', 'empty', 'iframe']
        self.sec_fetch_mode = ['navigate', 'cors', 'same-origin']

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        self.batch_size = options['batch_size']
        self.delay = options['delay']
        self.random_delay = options['random_delay']
        self.max_requests = options['max_requests']
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.timeout = options['timeout']
        self.only_actual = options['only_actual']
        self.block_retry_delay = options['block_retry_delay']
        self.auto_retry_after_block = options['auto_retry_after_block']
        self.start_from_id = options['start_from_id']
        self.human_mode = options['human_mode']

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
            self.stats['by_type'][slug] = {'total': 0, 'success': 0, 'failed': 0,
                                           'actual_updated': 0, 'blocked': 0, 'special': 0, 'rate_limited': 0}

        try:
            self.run_with_block_handling(type_slugs_to_process)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n\n⏹️ Обработка прервана пользователем"))
            self.print_final_stats()
            sys.exit(1)
        except BlockDetectedException as e:
            self.handle_block_detected(str(e))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n💥 Критическая ошибка: {e}"))
            logger.error(f"Critical error: {e}", exc_info=True)
            self.print_final_stats()
            sys.exit(1)

    def print_header(self, order_text):
        """Вывод заголовка"""
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("🚀 ЗАПУСК ОБНОВЛЕНИЯ ДАННЫХ РИД"))
        self.stdout.write(self.style.SUCCESS("="*80))

        if self.only_actual:
            self.stdout.write(self.style.WARNING("\n📌 РЕЖИМ: обновление только поля actual (статус)"))
        if self.force:
            self.stdout.write(self.style.WARNING("\n📌 РЕЖИМ: принудительное обновление с начала (--force)"))

        self.stdout.write(f"\n📌 Порядок обработки: {order_text}")

        if self.human_mode:
            self.stdout.write(f"📌 Мимикрия под человека: ВКЛЮЧЕНА")
            self.stdout.write(f"   • Ротация User-Agent: {len(self.user_agents)} вариантов")
            self.stdout.write(f"   • Умные задержки с длинными паузами")
            self.stdout.write(f"   • Эмуляция браузерной сессии")
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

    def run_with_block_handling(self, type_slugs_to_process):
        """Запуск обработки с обработкой блокировок"""
        attempt = 1
        max_attempts = 3 if self.auto_retry_after_block else 1

        while attempt <= max_attempts:
            if attempt > 1:
                self.stdout.write(self.style.WARNING(
                    f"\n🔄 Попытка {attempt} после блокировки (через {self.block_retry_delay} сек)"
                ))
                time.sleep(self.block_retry_delay)

            try:
                queryset = self.get_queryset(type_slugs_to_process)
                self.stats['total'] = queryset.count()

                self.stdout.write(f"\n📊 Найдено записей для обработки: {self.stats['total']}")

                if self.stats['total'] == 0:
                    self.stdout.write(self.style.WARNING("⚠️ Нет записей для обработки"))
                    return

                self.process_in_batches(queryset)
                break

            except BlockDetectedException as e:
                self.stats['blocked'] += 1
                self.block_detected = True

                if attempt < max_attempts:
                    attempt += 1
                    continue
                else:
                    raise

    def init_session(self):
        """Инициализация HTTP-сессии с мимикрией под реальный браузер"""
        self.session = requests.Session()

        if not self.human_mode:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })
            return

        self.session.headers.update({
            'Accept': random.choice(self.accept_variants),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })

        self.rotate_headers()
        self.emulate_browser_session()

    def rotate_headers(self):
        """Ротация заголовков для каждого запроса"""
        if not self.human_mode:
            return

        user_agent = random.choice(self.user_agents)
        self.session.headers.update({'User-Agent': user_agent})

        accept_language = random.choice(self.accept_languages)
        self.session.headers.update({'Accept-Language': accept_language})

        if random.random() < 0.3:
            self.session.headers.update({'Accept': random.choice(self.accept_variants)})

        if random.random() < 0.5:
            self.session.headers.update({
                'Sec-Fetch-Dest': random.choice(self.sec_fetch_dest),
                'Sec-Fetch-Mode': random.choice(self.sec_fetch_mode),
                'Sec-Fetch-Site': random.choice(['same-origin', 'same-site', 'cross-site']),
            })

        if random.random() < 0.2:
            self.session.headers.update({'DNT': '1'})
        else:
            self.session.headers.pop('DNT', None)

    def emulate_browser_session(self):
        """Эмуляция полной сессии браузера"""
        if not self.human_mode:
            return

        try:
            if self.verbosity >= 2:
                self.stdout.write("   🌐 Эмуляция загрузки главной страницы ФИПС...")

            time.sleep(random.uniform(1, 3))
            self.session.get('https://www1.fips.ru/', timeout=self.timeout, allow_redirects=True)
            time.sleep(random.uniform(2, 4))

            if random.random() < 0.7:
                pages = [
                    'https://www1.fips.ru/about/',
                    'https://www1.fips.ru/activities/',
                    'https://www1.fips.ru/information-systems/',
                    'https://www1.fips.ru/news/',
                ]
                for _ in range(random.randint(1, 3)):
                    page = random.choice(pages)
                    self.session.get(page, timeout=self.timeout)
                    time.sleep(random.uniform(1, 3))

            if self.verbosity >= 2:
                self.stdout.write(f"   ✅ Куки получены: {len(self.session.cookies)} шт.")
        except Exception as e:
            if self.verbosity >= 2:
                self.stdout.write(f"   ⚠️ Не удалось загрузить главную страницу: {e}")

    def apply_delay(self):
        """Умная задержка между запросами"""
        if self.delay <= 0 or self.block_detected:
            return

        if not self.human_mode:
            time.sleep(self.delay)
            return

        if self.request_count % random.randint(30, 70) == 0:
            long_delay = random.uniform(10, 40)
            if self.verbosity >= 1:
                self.stdout.write(f"\n   💤 ДЛИННАЯ ПАУЗА {long_delay:.1f} сек... (после {self.request_count} запросов)")
            time.sleep(long_delay)
            return

        if self.request_count % random.randint(10, 20) == 0:
            medium_delay = random.uniform(5, 20)
            if self.verbosity >= 2:
                self.stdout.write(f"\n   ⏱️ ПАУЗА {medium_delay:.1f} сек (изучение)...")
            time.sleep(medium_delay)
            return

        base_delay = self.delay * random.uniform(0.7, 2.5)
        extra_delay = 0

        if random.random() < 0.3:
            extra_delay = random.uniform(1, 5)
            if self.verbosity >= 3:
                self.stdout.write(f"      🤔 Читает... +{extra_delay:.1f} сек")

        if random.random() < 0.1:
            if self.verbosity >= 2:
                self.stdout.write("      🤔 Пауза-раздумье...")
            time.sleep(random.uniform(2, 6))

        time.sleep(base_delay + extra_delay)

    def get_queryset(self, type_slugs):
        """Получение queryset для обработки"""
        ip_types = IPType.objects.filter(slug__in=type_slugs)

        queryset = IPObject.objects.filter(
            ip_type__in=ip_types,
            publication_url__isnull=False
        ).exclude(
            publication_url=''
        ).select_related('ip_type')

        if self.start_from_id:
            self.start_id = self.start_from_id
            self.stdout.write(self.style.WARNING(f"🎯 Старт с явно указанного ID: {self.start_id}"))
            queryset = queryset.filter(id__gte=self.start_id)
        elif self.force:
            self.stdout.write(self.style.WARNING("🎯 Режим --force: начинаем с начала, обрабатываем все записи"))
        elif self.only_actual:
            self.stdout.write(self.style.WARNING("🎯 Режим --only-actual: обновляем статус у всех записей"))
        else:
            self.start_id = self.find_first_empty_abstract(queryset, ip_types)

            if self.start_id:
                self.stdout.write(self.style.WARNING(
                    f"🎯 Начинаем с ID {self.start_id} (первая запись с пустым abstract в сортировке от новых к старым)"
                ))
                queryset = queryset.filter(id__gte=self.start_id)
            else:
                self.stdout.write(self.style.SUCCESS("✅ Все записи имеют заполненный abstract! Обновлять нечего."))
                return IPObject.objects.none()

        if self.order_by:
            order_field = self.order_by
            if self.order_desc:
                order_field = f'-{order_field}'
            queryset = queryset.order_by(order_field)

        return queryset

    def find_first_empty_abstract(self, queryset, ip_types):
        """Находит первую запись с пустым abstract"""
        types_with_abstract = []
        for ip_type in ip_types:
            fields_map = self.type_fields_map.get(ip_type.slug, {})
            for field_info in fields_map.values():
                if field_info.get('is_main', False) and field_info['target'] == 'abstract':
                    types_with_abstract.append(ip_type)
                    break

        if not types_with_abstract:
            self.stdout.write(self.style.WARNING("⚠️ Нет типов РИД, у которых abstract является основным полем"))
            return None

        order_by = '-registration_date' if self.order_desc else 'registration_date'

        empty_abstract_qs = IPObject.objects.filter(
            ip_type__in=types_with_abstract,
            publication_url__isnull=False
        ).exclude(
            publication_url=''
        ).filter(
            Q(abstract__isnull=True) | Q(abstract='')
        ).order_by(order_by, 'id')

        first_empty = empty_abstract_qs.first()
        return first_empty.id if first_empty else None

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

                if self.block_detected:
                    self.stdout.write(self.style.ERROR("\n🚫 Обнаружена блокировка. Остановка обработки."))
                    return

                try:
                    self.process_single_object(ip_object)
                except BlockDetectedException:
                    raise
                except Exception as e:
                    self.stats['errors'] += 1
                    if self.verbosity >= 1:
                        self.stdout.write(self.style.ERROR(f"\n❌ Неожиданная ошибка: {e}"))
                    logger.error(f"Unexpected error processing IPObject {ip_object.id}: {e}", exc_info=True)

                pbar.update(1)
                pbar.set_postfix({
                    'OK': self.stats['success'],
                    'ACT': self.stats['actual_updated'],
                    'ERR': self.stats['failed'],
                    'SPC': self.stats['special_messages'],
                    'RTL': self.stats['rate_limited'],
                    'BLK': self.stats['blocked'],
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
            self.stdout.write(f"   URL: {ip_object.publication_url}")

        if not ip_object.publication_url:
            self.stats['skipped'] += 1
            if self.verbosity >= 2:
                self.stdout.write(self.style.WARNING("   ⚠️ Нет publication_url, пропуск"))
            return

        full_fields_map = self.type_fields_map.get(type_slug, {})

        if self.only_actual:
            fields_map = {k: v for k, v in full_fields_map.items() if v['target'] == 'actual'}
            if not fields_map:
                self.stats['skipped'] += 1
                if self.verbosity >= 2:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Тип {type_slug} не имеет поля actual, пропуск"))
                return
        else:
            fields_map = full_fields_map

        if not fields_map:
            self.stats['skipped'] += 1
            if self.verbosity >= 2:
                self.stdout.write(self.style.WARNING(f"   ⚠️ Нет карты полей для типа {type_slug}"))
            return

        if not self.force and not self.only_actual:
            if ip_object.abstract and ip_object.abstract.strip():
                if self.verbosity >= 2:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Abstract уже заполнен, пропуск"))
                self.stats['skipped'] += 1
                return

        self.rotate_headers()

        # Загружаем страницу с обработкой rate limit
        html_content, special_message = self.fetch_page_with_retry(ip_object.publication_url)

        if special_message:
            self.stats['special_messages'] += 1
            self.stats['by_type'][type_slug]['special'] += 1

            parsed_data = {
                'abstract': {
                    'value': f"[ОТВЕТ СЕРВЕРА] {special_message}",
                    'is_m2m': False
                }
            }

            if 'actual' in fields_map:
                parsed_data['actual'] = {
                    'value': False,
                    'is_m2m': False
                }

            updated, actual_updated = self.update_object(ip_object, parsed_data, fields_map)

            if updated:
                self.stats['success'] += 1
                self.stats['by_type'][type_slug]['success'] += 1
                if actual_updated:
                    self.stats['actual_updated'] += 1
                    self.stats['by_type'][type_slug]['actual_updated'] += 1
            else:
                self.stats['skipped'] += 1

            return

        if html_content is None:
            self.stats['failed'] += 1
            self.stats['by_type'][type_slug]['failed'] += 1
            return

        try:
            parsed_data = self.parse_page(html_content, type_slug, fields_map)

            if parsed_data:
                updated, actual_updated = self.update_object(ip_object, parsed_data, fields_map)

                if updated:
                    self.stats['success'] += 1
                    self.stats['by_type'][type_slug]['success'] += 1

                    if actual_updated:
                        self.stats['actual_updated'] += 1
                        self.stats['by_type'][type_slug]['actual_updated'] += 1

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

        except Exception as e:
            self.stats['errors'] += 1
            self.stats['failed'] += 1
            self.stats['by_type'][type_slug]['failed'] += 1

            if self.verbosity >= 1:
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка парсинга: {e}"))
            logger.error(f"Error parsing IPObject {ip_object.id}: {e}", exc_info=True)

    def fetch_page_with_retry(self, url, max_retries=3):
        """Загрузка страницы с повторными попытками при rate limit"""
        for attempt in range(max_retries):
            html_content, special_message = self.fetch_page(url)

            if special_message == "RATE_LIMIT":
                self.stats['rate_limited'] += 1
                wait_time = 60 * (attempt + 1)  # 60, 120, 180 секунд
                if self.verbosity >= 1:
                    self.stdout.write(self.style.WARNING(
                        f"\n   ⏳ Слишком быстрый просмотр. Пауза {wait_time} сек... (попытка {attempt + 1}/{max_retries})"
                    ))
                time.sleep(wait_time)
                continue

            return html_content, special_message

        # Если все попытки исчерпаны
        return None, "Превышено количество попыток из-за rate limit"

    def fetch_page(self, url):
        """Загрузка страницы по URL с правильным приоритетом проверок"""
        try:
            self.request_count += 1

            if self.human_mode and random.random() < 0.3:
                time.sleep(random.uniform(0.3, 1.5))

            response = self.session.get(url, timeout=self.timeout)

            # Проверяем HTTP статус 429 (явный rate limit)
            if response.status_code == 429:
                return None, "RATE_LIMIT"

            response.encoding = 'windows-1251'

            if response.status_code == 200:
                html_content = response.text

                # 1. СНАЧАЛА ПРОВЕРЯЕМ НА RATE LIMIT
                if self.is_rate_limit_message(html_content):
                    return None, "RATE_LIMIT"

                # 2. ПРОВЕРЯЕМ НА ЖЁСТКУЮ БЛОКИРОВКУ (САМЫЙ ВЫСОКИЙ ПРИОРИТЕТ!)
                if self.is_hard_block(html_content):
                    # НЕ ВОЗВРАЩАЕМ, А ГЕНЕРИРУЕМ ИСКЛЮЧЕНИЕ!
                    self.detect_block(html_content, url)
                    # detect_block сам выбросит BlockDetectedException

                # 3. ТОЛЬКО ЕСЛИ ЭТО НЕ БЛОКИРОВКА, проверяем специальные сообщения
                special_message = self.check_for_special_message(html_content)
                if special_message:
                    return html_content, special_message

                # 4. Обычная страница
                if self.verbosity >= 3:
                    self.stdout.write(f"   📥 Загружено {len(html_content)} символов")
                return html_content, None
            else:
                if self.verbosity >= 2:
                    self.stdout.write(self.style.ERROR(f"   ❌ HTTP {response.status_code}"))
                return None, None

        except BlockDetectedException:
            # Пробрасываем выше для остановки парсера
            raise
        except Exception as e:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка: {e}"))
            return None, None

    def is_hard_block(self, html_content):
        """Проверка на жёсткую блокировку"""
        if not html_content:
            return False

        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)

        hard_block_phrases = [
            'Вы заблокированы до',
            'ваш IP заблокирован',
            'your IP has been blocked',
        ]

        for phrase in hard_block_phrases:
            if phrase.lower() in text.lower():
                return True

        return False

    def is_rate_limit_message(self, html_content):
        """Проверка на сообщение о слишком быстром просмотре"""
        if not html_content:
            return False

        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(strip=True)

        rate_limit_phrases = [
            'Слишком быстрый просмотр документов',
            'Too many requests',
            'слишком много запросов',
        ]

        for phrase in rate_limit_phrases:
            if phrase.lower() in text.lower():
                return True

        return False

    def check_for_special_message(self, html_content):
        """Проверка на специальные сообщения (не блокировка)"""
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(strip=True)

        # Если текст очень короткий и нет структуры страницы
        if len(text) < 200 and not soup.find('div', id='Abs') and not soup.find('p', class_='TitCla'):
            if 'Документ с данным номером отсутствует' in text:
                return "Документ с данным номером отсутствует"
            elif text:
                return text[:200]

        return None

    def check_for_strict_block(self, html_content, url):
        """
        Проверка на ЖЕСТКУЮ блокировку (только явные фразы)
        """
        if not html_content:
            return

        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)

        strict_block_phrases = [
            'Вы заблокированы до',
            'ваш IP заблокирован',
            'your IP has been blocked',
            'доступ ограничен',
            'access denied',
        ]

        for phrase in strict_block_phrases:
            if phrase.lower() in text.lower():
                self.detect_block(html_content, url)
                return

    def detect_block(self, html_content, url, status_code=None):
        """Обнаружение жесткой блокировки"""
        block_info = {
            'url': url,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status_code': status_code,
            'request_count': self.request_count,
            'server_message': self.extract_server_message(html_content),
        }

        date_pattern = re.compile(r'Вы заблокированы до\s+(\d{2}\.\d{2}\.\d{4})\s+включительно', re.IGNORECASE)
        date_match = date_pattern.search(html_content)
        if date_match:
            block_info['block_until'] = date_match.group(1)

        id_pattern = re.compile(r'идентификатор(?:ом)? подключения:?\s*(\d+)', re.IGNORECASE)
        id_match = id_pattern.search(html_content)
        if id_match:
            block_info['connection_id'] = id_match.group(1)

        self.block_info = block_info
        self.block_detected = True
        self.stats['blocked'] += 1

        message = self.format_block_message(block_info)

        self.stdout.write(self.style.ERROR(f"\n{'='*80}"))
        self.stdout.write(self.style.ERROR("🚫 ОБНАРУЖЕНА БЛОКИРОВКА"))
        self.stdout.write(self.style.ERROR(f"{'='*80}"))
        self.stdout.write(self.style.ERROR(message))
        self.stdout.write(self.style.ERROR(f"{'='*80}\n"))

        logger.warning(f"Block detected: {block_info}")
        raise BlockDetectedException(message)

    def extract_server_message(self, html_content):
        """Извлечение читаемого сообщения сервера"""
        if not html_content:
            return "Нет содержимого"

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            if lines:
                message = '\n'.join(lines[:5])
                return message[:500] + '...' if len(message) > 500 else message
            return "Пустой ответ сервера"
        except Exception as e:
            return f"Ошибка извлечения сообщения: {e}"

    def format_block_message(self, block_info):
        """Форматирование сообщения о блокировке"""
        lines = []
        lines.append(f"🔸 URL: {block_info['url']}")
        lines.append(f"🔸 Время: {block_info['timestamp']}")
        lines.append(f"🔸 Выполнено запросов до блокировки: {block_info['request_count']}")

        if block_info.get('status_code'):
            lines.append(f"🔸 HTTP статус: {block_info['status_code']}")

        if block_info.get('block_until'):
            lines.append(f"🔸 Заблокирован до: {block_info['block_until']} включительно")
            try:
                block_date = datetime.strptime(block_info['block_until'], '%d.%m.%Y').date()
                today = date.today()
                days_left = (block_date - today).days
                if days_left > 0:
                    lines.append(f"🔸 Осталось дней: {days_left}")
            except:
                pass

        if block_info.get('connection_id'):
            lines.append(f"🔸 ID подключения: {block_info['connection_id']}")
            lines.append(f"🔸 Для разблокировки напишите в техподдержку с указанием этого ID")

        if block_info.get('server_message'):
            lines.append(f"\n📨 СООБЩЕНИЕ СЕРВЕРА:")
            lines.append(f"{block_info['server_message']}")

        return '\n'.join(lines)

    def handle_block_detected(self, message):
        """Обработка обнаруженной блокировки"""
        self.stdout.write(self.style.ERROR("\n" + "="*80))
        self.stdout.write(self.style.ERROR("🚫 РАБОТА ПРЕРВАНА ИЗ-ЗА БЛОКИРОВКИ"))
        self.stdout.write(self.style.ERROR("="*80))
        self.stdout.write(self.style.ERROR(message))

        if self.auto_retry_after_block:
            self.stdout.write(self.style.WARNING(
                f"\n🔄 Автоматический повтор через {self.block_retry_delay} сек не удался"
            ))

        self.stdout.write(self.style.WARNING("\n📌 Рекомендации:"))
        self.stdout.write("   1. Увеличьте задержку между запросами (--delay 3-5)")
        self.stdout.write("   2. Используйте случайную задержку (--random-delay)")
        self.stdout.write("   3. Уменьшите количество запросов (--max-requests)")
        self.stdout.write("   4. Подождите указанное время до разблокировки")

        self.print_final_stats()
        sys.exit(1)

    def parse_page(self, html, type_slug, fields_map):
        """Парсинг страницы в соответствии с типом РИД"""
        soup = BeautifulSoup(html, 'html.parser')
        result = {}

        for field_info in fields_map.values():
            source_method = field_info['source']

            if hasattr(self, source_method):
                value = getattr(self, source_method)(soup, type_slug)

                if value is not None and value != '':
                    result[field_info['target']] = {
                        'value': value,
                        'is_m2m': field_info.get('is_m2m', False)
                    }

        return result if result else None

    def parse_abstract(self, soup, type_slug):
        """Парсинг реферата"""
        abs_div = soup.find('div', id='Abs')
        if abs_div:
            abs_text = abs_div.get_text(strip=True)
            if 'Реферат:' in abs_text:
                abs_text = abs_text.split('Реферат:', 1)[-1].strip()
            return abs_text
        return None

    def parse_claims(self, soup, type_slug):
        """Парсинг формулы изобретения"""
        formula_start = soup.find('p', class_='TitCla')
        if formula_start:
            formula_text = formula_start.get_text(strip=True)
            if ('Формула изобретения' in formula_text or 'Формула полезной модели' in formula_text):
                formula_content = []
                next_elem = formula_start.find_next_sibling()
                while next_elem and not (hasattr(next_elem, 'name') and
                                         next_elem.name == 'a' and
                                         'ClEnd' in next_elem.get('href', '')):
                    if hasattr(next_elem, 'get_text'):
                        text = next_elem.get_text(strip=True)
                        if text:
                            formula_content.append(text)
                    next_elem = next_elem.find_next_sibling()
                if formula_content:
                    return '\n'.join(formula_content)
        return None

    def parse_status(self, soup, type_slug):
        """Парсинг статуса для определения actual"""
        status_rows = soup.find_all('tr')
        for row in status_rows:
            status_label = row.find('td', id='StatusL')
            if status_label and 'Статус:' in status_label.get_text():
                status_value = row.find('td', id='StatusR')
                if status_value:
                    status_text = status_value.get_text(strip=True)
                    first_word = status_text.split()[0].lower() if status_text.split() else ''
                    return first_word == 'действует'
        return False

    def parse_programming_languages(self, soup, type_slug):
        """Парсинг языков программирования"""
        b_tag = soup.find('b', string=re.compile(r'Язык программирования:', re.IGNORECASE))
        if b_tag and b_tag.parent:
            full_text = b_tag.parent.get_text()
            quoted = re.findall(r'"([^"]*)"', full_text)
            if quoted:
                languages = [lang.strip() for lang in quoted[0].split(',')]
                return languages
        return None

    def parse_dbms(self, soup, type_slug):
        """Парсинг СУБД"""
        b_tag = soup.find('b', string=re.compile(r'Вид и версия системы управления базой данных:', re.IGNORECASE))
        if b_tag and b_tag.parent:
            full_text = b_tag.parent.get_text()
            quoted = re.findall(r'"([^"]*)"', full_text)
            if quoted:
                dbms_list = [db.strip() for db in quoted[0].split(',')]
                return dbms_list
        return None

    def update_object(self, ip_object, parsed_data, fields_map):
        """Обновление объекта РИД"""
        if self.dry_run:
            if self.verbosity >= 2:
                self.stdout.write("   📝 DRY-RUN: данные для обновления:")
                for target_field, field_data in parsed_data.items():
                    new_value = field_data['value']
                    current_value = getattr(ip_object, target_field)

                    if field_data.get('is_m2m', False):
                        current = list(getattr(ip_object, target_field).all())
                        self.stdout.write(f"      {target_field}: {current} -> {new_value}")
                    else:
                        self.stdout.write(f"      {target_field}: '{current_value}' -> '{new_value}'")
            return True, 'actual' in parsed_data

        updated = False
        actual_updated = False

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

                        if target_field == 'actual':
                            actual_updated = True

            if updated:
                ip_object.save(update_fields=list(parsed_data.keys()))

        return updated, actual_updated

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

        if self.stats['actual_updated'] > 0:
            self.stdout.write(f"🔄 Обновлено поле actual: {self.stats['actual_updated']}")

        if self.stats['special_messages'] > 0:
            self.stdout.write(f"📝 Специальных сообщений: {self.stats['special_messages']}")

        if self.stats['rate_limited'] > 0:
            self.stdout.write(f"⏳ Срабатываний rate limit: {self.stats['rate_limited']}")

        if self.stats['blocked'] > 0:
            self.stdout.write(self.style.ERROR(f"🚫 Обнаружено блокировок: {self.stats['blocked']}"))

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
                    actual_info = f", actual={stats['actual_updated']}" if stats['actual_updated'] > 0 else ""
                    special_info = f", спец={stats['special']}" if stats['special'] > 0 else ""
                    rate_info = f", rate={stats['rate_limited']}" if stats['rate_limited'] > 0 else ""
                    blocked_info = f", блок={stats['blocked']}" if stats['blocked'] > 0 else ""
                    self.stdout.write(
                        f"   {type_slug}: всего={stats['total']}, "
                        f"✅={stats['success']}, ❌={stats['failed']}{actual_info}{special_info}{rate_info}{blocked_info}, "
                        f"({success_rate:.1f}%)"
                    )

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены в БД"))

        if self.block_detected:
            self.stdout.write(self.style.ERROR("\n🚫 РАБОТА ПРЕРВАНА ИЗ-ЗА БЛОКИРОВКИ"))
            if self.block_info:
                self.stdout.write(self.style.ERROR(self.format_block_message(self.block_info)))

        self.stdout.write(self.style.SUCCESS("="*80))
