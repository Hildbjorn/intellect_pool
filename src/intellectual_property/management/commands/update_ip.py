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
        
        # Паттерны для обнаружения блокировки
        self.block_patterns = [
            re.compile(r'Вы заблокированы до\s+(\d{2}\.\d{2}\.\d{4})\s+включительно', re.IGNORECASE),
            re.compile(r'идентификатор(?:ом)? подключения:?\s*(\d+)', re.IGNORECASE),
            re.compile(r'доступ\s+заблокирован', re.IGNORECASE),
            re.compile(r'вы\s+заблокированы', re.IGNORECASE),
            re.compile(r'your\s+access\s+is\s+blocked', re.IGNORECASE),
            re.compile(r'too\s+many\s+requests', re.IGNORECASE),
            re.compile(r'429', re.IGNORECASE),
        ]
        
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
            'by_type': {},
        }
        
        self.session = None
        self.request_count = 0
        self.block_detected = False
        self.block_info = {}
        self.start_id = None  # ID, с которого начинаем обработку
        
        # ========== НАСТРОЙКИ МИМИКРИИ ==========
        
        # Пул современных User-Agent'ов
        self.user_agents = [
            # Windows + Chrome
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            
            # Windows + Firefox
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            
            # Windows + Edge
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            
            # macOS + Safari
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            
            # Linux + Chrome
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            
            # Мобильные (иногда полезно)
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
        
        # Варианты Accept (иногда браузеры их меняют)
        self.accept_variants = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        ]
        
        # Заголовки Sec-Fetch (браузерные)
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
        
        # Определяем порядок сортировки
        if options['start_from_oldest']:
            self.order_by = 'registration_date'
            self.order_desc = False
            order_text = "от старых к новым"
        else:
            # По умолчанию от новых к старым
            self.order_by = 'registration_date'
            self.order_desc = True
            order_text = "от новых к старым"
        
        ip_type_param = options['ip_type']
        
        self.print_header(order_text)
        
        # Инициализируем сессию с мимикрией
        self.init_session()
        
        # Получаем список типов для обработки
        type_slugs_to_process = self.get_type_slugs(ip_type_param)
        
        # Инициализируем статистику по типам
        for slug in type_slugs_to_process:
            self.stats['by_type'][slug] = {'total': 0, 'success': 0, 'failed': 0, 'actual_updated': 0, 'blocked': 0}
        
        # Основной цикл обработки с поддержкой повторных попыток после блокировки
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
                # Получаем queryset для обработки
                queryset = self.get_queryset(type_slugs_to_process)
                self.stats['total'] = queryset.count()
                
                self.stdout.write(f"\n📊 Найдено записей для обработки: {self.stats['total']}")
                
                if self.stats['total'] == 0:
                    self.stdout.write(self.style.WARNING("⚠️ Нет записей для обработки"))
                    return
                
                # Обрабатываем по батчам
                self.process_in_batches(queryset)
                
                # Если дошли сюда без исключения - успешно завершили
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
            # Режим без мимикрии - минимальные заголовки
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })
            return
        
        # ===== РЕЖИМ ПОЛНОЙ МИМИКРИИ =====
        
        # Устанавливаем начальные заголовки (базовые)
        self.session.headers.update({
            'Accept': random.choice(self.accept_variants),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })
        
        # Устанавливаем случайный User-Agent и Accept-Language
        self.rotate_headers()
        
        # Эмулируем загрузку главной страницы для получения cookies
        self.emulate_browser_session()

    def rotate_headers(self):
        """Ротация заголовков для каждого запроса"""
        if not self.human_mode:
            return
        
        # Случайный User-Agent
        user_agent = random.choice(self.user_agents)
        self.session.headers.update({'User-Agent': user_agent})
        
        # Случайный Accept-Language
        accept_language = random.choice(self.accept_languages)
        self.session.headers.update({'Accept-Language': accept_language})
        
        # Случайный Accept (иногда меняется)
        if random.random() < 0.3:  # 30% запросов
            self.session.headers.update({'Accept': random.choice(self.accept_variants)})
        
        # Случайные Sec-Fetch заголовки (браузерные)
        if random.random() < 0.5:
            self.session.headers.update({
                'Sec-Fetch-Dest': random.choice(self.sec_fetch_dest),
                'Sec-Fetch-Mode': random.choice(self.sec_fetch_mode),
                'Sec-Fetch-Site': random.choice(['same-origin', 'same-site', 'cross-site']),
            })
        
        # Иногда добавляем заголовок DNT (Do Not Track)
        if random.random() < 0.2:
            self.session.headers.update({'DNT': '1'})
        else:
            self.session.headers.pop('DNT', None)

    def emulate_browser_session(self):
        """Эмуляция полной сессии браузера - загрузка главной страницы и получение cookies"""
        if not self.human_mode:
            return
        
        try:
            if self.verbosity >= 2:
                self.stdout.write("   🌐 Эмуляция загрузки главной страницы ФИПС...")
            
            # Небольшая пауза перед первой загрузкой (как человек)
            time.sleep(random.uniform(1, 3))
            
            # Загружаем главную страницу
            main_page_response = self.session.get(
                'https://www1.fips.ru/', 
                timeout=self.timeout,
                allow_redirects=True
            )
            
            # Куки сохранятся автоматически в self.session.cookies
            
            # Небольшая пауза после загрузки главной
            time.sleep(random.uniform(2, 4))
            
            # Иногда загружаем ещё пару страниц для большей естественности
            if random.random() < 0.7:  # 70% случаев
                pages = [
                    'https://www1.fips.ru/about/',
                    'https://www1.fips.ru/activities/',
                    'https://www1.fips.ru/information-systems/',
                    'https://www1.fips.ru/news/',
                ]
                # Загружаем 1-3 случайные страницы
                for _ in range(random.randint(1, 3)):
                    page = random.choice(pages)
                    self.session.get(page, timeout=self.timeout)
                    time.sleep(random.uniform(1, 3))
            
            if self.verbosity >= 2:
                self.stdout.write(f"   ✅ Куки получены: {len(self.session.cookies)} шт.")
                
        except Exception as e:
            if self.verbosity >= 2:
                self.stdout.write(f"   ⚠️ Не удалось загрузить главную страницу: {e}")
            # Продолжаем работу без кук, возможно, они и не нужны

    def apply_delay(self):
        """Умная задержка между запросами с имитацией человеческого поведения"""
        if self.delay <= 0 or self.block_detected:
            return
        
        if not self.human_mode:
            # Простая задержка без мимикрии
            time.sleep(self.delay)
            return
        
        # ===== УМНЫЕ ЗАДЕРЖКИ С МИМИКРИЕЙ =====
        
        # Каждые 30-70 запросов делаем длинную паузу (как будто пользователь отошел)
        if self.request_count % random.randint(30, 70) == 0:
            long_delay = random.uniform(45, 180)  # 45 секунд - 3 минуты
            if self.verbosity >= 1:
                self.stdout.write(f"\n   💤 ДЛИННАЯ ПАУЗА {long_delay:.1f} сек... (после {self.request_count} запросов)")
            time.sleep(long_delay)
            return
        
        # Каждые 10-20 запросов делаем среднюю паузу (изучение страницы)
        if self.request_count % random.randint(10, 20) == 0:
            medium_delay = random.uniform(8, 25)  # 8-25 секунд
            if self.verbosity >= 2:
                self.stdout.write(f"\n   ⏱️ ПАУЗА {medium_delay:.1f} сек (изучение)...")
            time.sleep(medium_delay)
            return
        
        # Обычная задержка с вариациями
        base_delay = self.delay * random.uniform(0.7, 2.5)
        
        # Иногда добавляем "микро-паузы" (как будто пользователь читает)
        extra_delay = 0
        if random.random() < 0.3:  # 30% случаев
            extra_delay = random.uniform(1, 5)
            if self.verbosity >= 3:
                self.stdout.write(f"      🤔 Читает... +{extra_delay:.1f} сек")
        
        # Иногда делаем две короткие паузы подряд (имитация задумчивости)
        if random.random() < 0.1:  # 10% случаев
            if self.verbosity >= 2:
                self.stdout.write("      🤔 Пауза-раздумье...")
            time.sleep(random.uniform(2, 6))
        
        total_delay = base_delay + extra_delay
        time.sleep(total_delay)

    def get_queryset(self, type_slugs):
        """Получение queryset для обработки с умным определением стартовой позиции"""
        # Получаем типы по слагам
        ip_types = IPType.objects.filter(slug__in=type_slugs)
        
        # Базовый queryset
        queryset = IPObject.objects.filter(
            ip_type__in=ip_types,
            publication_url__isnull=False
        ).exclude(
            publication_url=''
        ).select_related('ip_type')
        
        # Определяем стартовую позицию
        if self.start_from_id:
            # Явно указанный ID
            self.start_id = self.start_from_id
            self.stdout.write(self.style.WARNING(
                f"🎯 Старт с явно указанного ID: {self.start_id}"
            ))
            queryset = queryset.filter(id__gte=self.start_id)
        
        elif self.force:
            # Режим force - начинаем с начала, обрабатываем все
            self.stdout.write(self.style.WARNING(
                "🎯 Режим --force: начинаем с начала, обрабатываем все записи"
            ))
            # Ничего не фильтруем дополнительно
        
        elif self.only_actual:
            # Режим only-actual - обновляем статус у всех
            self.stdout.write(self.style.WARNING(
                "🎯 Режим --only-actual: обновляем статус у всех записей"
            ))
            # Ничего не фильтруем, берем все
        
        else:
            # Обычный режим - находим первую запись с пустым abstract
            # (с учетом сортировки от новых к старым)
            self.start_id = self.find_first_empty_abstract(queryset, ip_types)
            
            if self.start_id:
                self.stdout.write(self.style.WARNING(
                    f"🎯 Начинаем с ID {self.start_id} (первая запись с пустым abstract в сортировке от новых к старым)"
                ))
                queryset = queryset.filter(id__gte=self.start_id)
            else:
                self.stdout.write(self.style.SUCCESS(
                    "✅ Все записи имеют заполненный abstract! Обновлять нечего."
                ))
                return IPObject.objects.none()  # Пустой queryset
        
        # Применяем сортировку
        if self.order_by:
            order_field = self.order_by
            if self.order_desc:
                order_field = f'-{order_field}'
            
            queryset = queryset.order_by(order_field)
        
        return queryset

    def find_first_empty_abstract(self, queryset, ip_types):
        """
        Находит первую запись с пустым abstract для типов, у которых abstract является основным полем
        Учитывает сортировку от новых к старым
        """
        # Собираем типы, у которых есть поле abstract как основное
        types_with_abstract = []
        for ip_type in ip_types:
            fields_map = self.type_fields_map.get(ip_type.slug, {})
            for field_key, field_info in fields_map.items():
                if field_info.get('is_main', False) and field_info['target'] == 'abstract':
                    types_with_abstract.append(ip_type)
                    break
        
        if not types_with_abstract:
            self.stdout.write(self.style.WARNING(
                "⚠️ Нет типов РИД, у которых abstract является основным полем"
            ))
            return None
        
        # Определяем порядок сортировки
        order_by = '-registration_date' if self.order_desc else 'registration_date'
        
        # Ищем первую запись с пустым abstract в отсортированном списке
        empty_abstract_qs = IPObject.objects.filter(
            ip_type__in=types_with_abstract,
            publication_url__isnull=False
        ).exclude(
            publication_url=''
        ).filter(
            Q(abstract__isnull=True) | Q(abstract='')
        ).order_by(order_by, 'id')  # Сортируем по дате и ID
        
        first_empty = empty_abstract_qs.first()
        
        if first_empty:
            return first_empty.id
        
        return None

    def process_in_batches(self, queryset):
        """Обработка записей по батчам"""
        total = queryset.count()
        
        # Для тестирования ограничиваем количество запросов
        if self.max_requests and self.max_requests < total:
            self.stdout.write(self.style.WARNING(
                f"\n⏹️ Будет обработано только {self.max_requests} записей из {total} (лимит запросов)"
            ))
            # Получаем первые N записей
            queryset = queryset[:self.max_requests]
            total = self.max_requests
        
        with tqdm(total=total, desc="Обработка записей", unit="зап") as pbar:
            for ip_object in queryset.iterator(chunk_size=self.batch_size):
                # Проверяем лимит запросов
                if self.max_requests and self.request_count >= self.max_requests:
                    self.stdout.write(self.style.WARNING(
                        f"\n⏹️ Достигнут лимит запросов ({self.max_requests})"
                    ))
                    return
                
                # Проверяем, не была ли обнаружена блокировка в предыдущем запросе
                if self.block_detected:
                    self.stdout.write(self.style.ERROR(
                        "\n🚫 Обнаружена блокировка. Остановка обработки."
                    ))
                    return
                
                # Обрабатываем запись
                try:
                    self.process_single_object(ip_object)
                except BlockDetectedException:
                    # Пробрасываем исключение для остановки всего процесса
                    raise
                except Exception as e:
                    # Логируем другие ошибки, но продолжаем
                    self.stats['errors'] += 1
                    if self.verbosity >= 1:
                        self.stdout.write(self.style.ERROR(f"\n❌ Неожиданная ошибка: {e}"))
                    logger.error(f"Unexpected error processing IPObject {ip_object.id}: {e}", exc_info=True)
                
                # Обновляем прогресс
                pbar.update(1)
                pbar.set_postfix({
                    'OK': self.stats['success'],
                    'ACT': self.stats['actual_updated'],
                    'ERR': self.stats['failed'],
                    'BLK': self.stats['blocked'],
                    'REQ': self.request_count
                })
                
                # Задержка между запросами
                self.apply_delay()

    def process_single_object(self, ip_object):
        """Обработка одного объекта РИД"""
        self.stats['processed'] += 1
        type_slug = ip_object.ip_type.slug
        
        self.stats['by_type'][type_slug]['total'] += 1
        
        reg_date = ip_object.registration_date.strftime('%d.%m.%Y') if ip_object.registration_date else 'нет даты'
        
        if self.verbosity >= 2:
            self.stdout.write(f"\n🔍 Обработка ID={ip_object.id}, тип={type_slug}, дата={reg_date}")
            self.stdout.write(f"   URL: {ip_object.publication_url}")
        
        # Проверяем наличие URL
        if not ip_object.publication_url:
            self.stats['skipped'] += 1
            if self.verbosity >= 2:
                self.stdout.write(self.style.WARNING("   ⚠️ Нет publication_url, пропуск"))
            return
        
        # Получаем карту полей для данного типа
        full_fields_map = self.type_fields_map.get(type_slug, {})
        
        # Если режим only_actual, оставляем только поле actual
        if self.only_actual:
            fields_map = {k: v for k, v in full_fields_map.items() if v['target'] == 'actual'}
            if not fields_map:
                # Для типов без поля actual пропускаем
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
        
        # В обычном режиме (не force и не only-actual) пропускаем, если abstract уже заполнен
        if not self.force and not self.only_actual:
            # Проверяем, заполнено ли основное поле (abstract)
            if ip_object.abstract and ip_object.abstract.strip():
                if self.verbosity >= 2:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Abstract уже заполнен, пропуск"))
                self.stats['skipped'] += 1
                return
        
        # Ротация заголовков перед запросом
        self.rotate_headers()
        
        # Загружаем страницу
        html_content = self.fetch_page(ip_object.publication_url)
        
        if not html_content:
            self.stats['failed'] += 1
            self.stats['by_type'][type_slug]['failed'] += 1
            return
        
        # Парсим данные
        try:
            parsed_data = self.parse_page(html_content, type_slug, fields_map)
            
            if parsed_data:
                # Обновляем объект
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

    def fetch_page(self, url):
        """Загрузка страницы по URL с детектором блокировки"""
        try:
            self.request_count += 1
            
            # Небольшая случайная задержка перед запросом (как будто пользователь нажимает ссылку)
            if self.human_mode and random.random() < 0.3:
                click_delay = random.uniform(0.3, 1.5)
                time.sleep(click_delay)
            
            response = self.session.get(url, timeout=self.timeout)
            
            # Проверяем HTTP статус на блокировку
            if response.status_code == 429:
                self.detect_block(response.text, url, status_code=429)
            
            response.encoding = 'windows-1251'  # ФИПС использует windows-1251
            
            if response.status_code == 200:
                # Проверяем содержимое на признаки блокировки
                self.check_for_block(response.text, url)
                
                if self.verbosity >= 3:
                    self.stdout.write(f"   📥 Загружено {len(response.text)} символов")
                return response.text
            else:
                if self.verbosity >= 2:
                    self.stdout.write(self.style.ERROR(f"   ❌ HTTP {response.status_code}"))
                return None
                
        except requests.exceptions.Timeout:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(f"   ⏰ Таймаут"))
            return None
        except requests.exceptions.ConnectionError:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(f"   🔌 Ошибка соединения"))
            return None
        except BlockDetectedException:
            # Пробрасываем исключение о блокировке
            raise
        except Exception as e:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка: {e}"))
            return None

    def check_for_block(self, html_content, url):
        """Проверка HTML-содержимого на наличие признаков блокировки"""
        if not html_content:
            return
        
        # Проверяем по всем паттернам
        for pattern in self.block_patterns:
            match = pattern.search(html_content)
            if match:
                self.detect_block(html_content, url, pattern_match=match)
                return

    def detect_block(self, html_content, url, status_code=None, pattern_match=None):
        """
        Обнаружение блокировки и генерация исключения
        """
        block_info = {
            'url': url,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status_code': status_code,
            'request_count': self.request_count,
        }
        
        # Пытаемся извлечь дату блокировки
        date_pattern = re.compile(r'Вы заблокированы до\s+(\d{2}\.\d{2}\.\d{4})\s+включительно', re.IGNORECASE)
        date_match = date_pattern.search(html_content)
        if date_match:
            block_info['block_until'] = date_match.group(1)
        
        # Пытаемся извлечь ID подключения
        id_pattern = re.compile(r'идентификатор(?:ом)? подключения:?\s*(\d+)', re.IGNORECASE)
        id_match = id_pattern.search(html_content)
        if id_match:
            block_info['connection_id'] = id_match.group(1)
        
        self.block_info = block_info
        self.block_detected = True
        self.stats['blocked'] += 1
        
        # Формируем сообщение о блокировке
        message = self.format_block_message(block_info)
        
        # Выводим сообщение
        self.stdout.write(self.style.ERROR(f"\n{'='*80}"))
        self.stdout.write(self.style.ERROR("🚫 ОБНАРУЖЕНА БЛОКИРОВКА"))
        self.stdout.write(self.style.ERROR(f"{'='*80}"))
        self.stdout.write(self.style.ERROR(message))
        self.stdout.write(self.style.ERROR(f"{'='*80}\n"))
        
        # Логируем
        logger.warning(f"Block detected: {block_info}")
        
        # Генерируем исключение
        raise BlockDetectedException(message)

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
            
            # Рассчитываем оставшееся время
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
        
        return '\n'.join(lines)

    def handle_block_detected(self, message):
        """Обработка обнаруженной блокировки"""
        self.stdout.write(self.style.ERROR("\n" + "="*80))
        self.stdout.write(self.style.ERROR("🚫 РАБОТА ПРЕРВАНА ИЗ-ЗА БЛОКИРОВКИ"))
        self.stdout.write(self.style.ERROR("="*80))
        self.stdout.write(self.style.ERROR(message))
        
        if self.auto_retry_after_block:
            self.stdout.write(self.style.WARNING(
                f"\n🔄 Автоматический повтор через {self.block_retry_delay} сек не удался (превышено количество попыток)"
            ))
        
        self.stdout.write(self.style.WARNING("\n📌 Рекомендации:"))
        self.stdout.write("   1. Увеличьте задержку между запросами (--delay 3-5)")
        self.stdout.write("   2. Используйте случайную задержку (--random-delay включен по умолчанию)")
        self.stdout.write("   3. Уменьшите количество запросов (--max-requests)")
        self.stdout.write("   4. Подождите указанное время до разблокировки")
        
        self.print_final_stats()
        sys.exit(1)

    def parse_page(self, html, type_slug, fields_map):
        """Парсинг страницы в соответствии с типом РИД"""
        soup = BeautifulSoup(html, 'html.parser')
        result = {}
        
        for field_key, field_info in fields_map.items():
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
        """Парсинг реферата (общий для всех типов)"""
        abs_div = soup.find('div', id='Abs')
        
        if abs_div:
            abs_text = abs_div.get_text(strip=True)
            if 'Реферат:' in abs_text:
                abs_text = abs_text.split('Реферат:', 1)[-1].strip()
            return abs_text
        
        return None

    def parse_claims(self, soup, type_slug):
        """Парсинг формулы изобретения/полезной модели"""
        # Для изобретений и полезных моделей
        formula_start = soup.find('p', class_='TitCla')
        
        if formula_start:
            formula_text = formula_start.get_text(strip=True)
            
            # Проверяем, что это формула изобретения или полезной модели
            if ('Формула изобретения' in formula_text or 
                'Формула полезной модели' in formula_text):
                
                # Собираем всю формулу
                formula_content = []
                next_elem = formula_start.find_next_sibling()
                
                while next_elem and not (
                    hasattr(next_elem, 'name') and 
                    next_elem.name == 'a' and 
                    'ClEnd' in next_elem.get('href', '')
                ):
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
                    
                    # Берем ПЕРВОЕ слово статуса
                    first_word = status_text.split()[0].lower() if status_text.split() else ''
                    
                    # Если первое слово "действует" - True, иначе False
                    return first_word == 'действует'
        
        return False  # По умолчанию считаем недействующим

    def parse_programming_languages(self, soup, type_slug):
        """Парсинг языков программирования для программ ЭВМ"""
        b_tag = soup.find('b', string=re.compile(r'Язык программирования:', re.IGNORECASE))
        
        if b_tag:
            parent = b_tag.parent
            if parent:
                full_text = parent.get_text()
                quoted = re.findall(r'"([^"]*)"', full_text)
                if quoted:
                    languages_str = quoted[0]
                    languages = [lang.strip() for lang in languages_str.split(',')]
                    return languages
        
        return None

    def parse_dbms(self, soup, type_slug):
        """Парсинг СУБД для баз данных"""
        b_tag = soup.find('b', string=re.compile(r'Вид и версия системы управления базой данных:', re.IGNORECASE))
        
        if b_tag:
            parent = b_tag.parent
            if parent:
                full_text = parent.get_text()
                quoted = re.findall(r'"([^"]*)"', full_text)
                if quoted:
                    dbms_str = quoted[0]
                    dbms_list = [db.strip() for db in dbms_str.split(',')]
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
                        updated |= self.update_m2m_field(
                            ip_object, 
                            ProgrammingLanguage, 
                            'programming_languages', 
                            value
                        )
                    elif target_field == 'dbms':
                        updated |= self.update_m2m_field(
                            ip_object, 
                            DBMS, 
                            'dbms', 
                            value
                        )
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
                obj, created = model_class.objects.get_or_create(name=value.strip())
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
        
        if self.stats['blocked'] > 0:
            self.stdout.write(self.style.ERROR(f"🚫 Обнаружено блокировок: {self.stats['blocked']}"))
        
        self.stdout.write(f"❌ Неудачно: {self.stats['failed']}")
        self.stdout.write(f"⏭️  Пропущено: {self.stats['skipped']}")
        
        if self.stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"💥 Ошибок: {self.stats['errors']}"))
        
        self.stdout.write(f"📡 Выполнено запросов: {self.request_count}")
        
        if self.start_id:
            self.stdout.write(f"🎯 Стартовая позиция: ID {self.start_id}")
        
        # Статистика по типам
        if any(stats['total'] > 0 for stats in self.stats['by_type'].values()):
            self.stdout.write(self.style.SUCCESS("\n📊 ПО ТИПАМ РИД:"))
            for type_slug, stats in self.stats['by_type'].items():
                if stats['total'] > 0:
                    success_rate = (stats['success'] / stats['total']) * 100 if stats['total'] > 0 else 0
                    actual_info = f", actual={stats['actual_updated']}" if stats['actual_updated'] > 0 else ""
                    blocked_info = f", блок={stats['blocked']}" if stats['blocked'] > 0 else ""
                    self.stdout.write(
                        f"   {type_slug}: всего={stats['total']}, "
                        f"✅={stats['success']}, ❌={stats['failed']}{actual_info}{blocked_info}, "
                        f"({success_rate:.1f}%)"
                    )
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены в БД"))
        
        if self.block_detected:
            self.stdout.write(self.style.ERROR("\n🚫 РАБОТА ПРЕРВАНА ИЗ-ЗА БЛОКИРОВКИ"))
            if self.block_info:
                self.stdout.write(self.style.ERROR(self.format_block_message(self.block_info)))
        
        self.stdout.write(self.style.SUCCESS("="*80))