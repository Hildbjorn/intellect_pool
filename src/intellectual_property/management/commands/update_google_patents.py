"""
Команда для обновления данных РИД путём прямого парсинга Google Patents.
Поддерживает все типы РИД с соответствующими полями для каждого типа.

Использует requests для получения HTML страниц и BeautifulSoup для парсинга.

Логика работы:
1. Определяет, какие записи нужно обновить (пустые поля или --force)
2. Делает запросы к Google Patents с ротацией User-Agent
3. Парсит HTML и извлекает abstract, description, claims
4. Сохраняет результаты пакетами (bulk_update) для оптимизации производительности

Архитектура:
- Отдельные методы для каждого этапа обработки
- Пакетное накопление и сохранение результатов
- Детальная статистика по типам РИД
- Обработка rate limiting и ошибок
"""

import logging
import re
import time
import random
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Set

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models
from django.db.models import Q
from tqdm import tqdm
from bs4 import BeautifulSoup

from intellectual_property.models import IPObject, IPType, ProgrammingLanguage, DBMS

logger = logging.getLogger(__name__)


class RateLimitException(Exception):
    """Исключение, возникающее при превышении лимита запросов (HTTP 429)"""
    pass


class Command(BaseCommand):
    help = 'Обновление данных РИД прямым парсингом Google Patents'

    # =========================================================================
    # НАСТРОЙКИ ПО УМОЛЧАНИЮ
    # =========================================================================
    DEFAULT_BATCH_SIZE = 100      # Размер пачки для записи в БД
    DEFAULT_DELAY = 2.0            # Базовая задержка между запросами (сек)
    DEFAULT_TIMEOUT = 30           # Таймаут HTTP запроса (сек)
    DEFAULT_MAX_RETRIES = 3        # Максимальное количество повторов при ошибке

    # Типы РИД, по которым заведомо нет данных в Google Patents
    # (программы, базы данных, топологии не индексируются)
    SKIP_TYPES = {
        'integrated-circuit-topology',
        'computer-program',
        'database'
    }

    def add_arguments(self, parser):
        """Добавление аргументов командной строки"""
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
            default=self.DEFAULT_BATCH_SIZE,
            help=f'Размер пакета для записи в БД (по умолчанию {self.DEFAULT_BATCH_SIZE})'
        )

        parser.add_argument(
            '--delay',
            type=float,
            default=self.DEFAULT_DELAY,
            help=f'Базовая задержка между запросами в секундах (по умолчанию {self.DEFAULT_DELAY})'
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
            help='Принудительное обновление (обрабатывает все записи, даже если поля заполнены)'
        )

        parser.add_argument(
            '--timeout',
            type=int,
            default=self.DEFAULT_TIMEOUT,
            help=f'Таймаут запроса в секундах (по умолчанию {self.DEFAULT_TIMEOUT})'
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
        """Инициализация команды: карты полей, статистика, HTTP сессия"""
        super().__init__(*args, **kwargs)

        # Соответствие типов РИД и их слагов для удобства
        self.type_slugs = {
            'invention': 'invention',
            'utility-model': 'utility-model',
            'industrial-design': 'industrial-design',
            'integrated-circuit-topology': 'integrated-circuit-topology',
            'computer-program': 'computer-program',
            'database': 'database',
        }

        # Карта полей для каждого типа РИД
        # Каждый тип знает, какие поля ему нужно парсить
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

        # Статистика для отслеживания прогресса
        self.stats = {
            'total': 0,                 # Всего записей для обработки
            'processed': 0,              # Обработано (включая ошибки)
            'success': 0,                # Успешно обновлено
            'failed': 0,                 # Не удалось обработать
            'skipped': 0,                # Пропущено (уже заполнены) - только когда !force
            'errors': 0,                 # Критические ошибки
            'rate_limited': 0,            # Срабатываний rate limit
            'special_messages': 0,        # Специальные сообщения (нет документа)
            'by_type': {},                 # Детальная статистика по типам
        }

        # HTTP сессия для поддержки keep-alive и кук
        self.session = None
        self.request_count = 0            # Счётчик запросов
        self.start_id = None              # ID записи, с которой начали

        # Пул современных User-Agent'ов для мимикрии под реального пользователя
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]

        # Варианты Accept-Language для разнообразия
        self.accept_languages = [
            'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'ru,en-US;q=0.9,en;q=0.8,uk;q=0.7',
            'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
            'en-US,en;q=0.9,ru;q=0.8',
        ]

    # =========================================================================
    # ОСНОВНОЙ ПОТОК ВЫПОЛНЕНИЯ
    # =========================================================================

    def handle(self, *args, **options):
        """
        Главный метод команды.
        Инициализирует параметры, запускает обработку, обрабатывает ошибки.
        """
        # Сохраняем параметры в self для доступа из других методов
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

        # Определяем порядок сортировки записей
        if options['start_from_oldest']:
            self.order_by = 'registration_date'
            self.order_desc = False
            order_text = "от старых к новым"
        else:
            self.order_by = 'registration_date'
            self.order_desc = True
            order_text = "от новых к старым"

        ip_type_param = options['ip_type']

        # Выводим приветствие с параметрами
        self._print_header(order_text)

        # Инициализируем HTTP сессию
        self._init_session()

        # Получаем список слагов типов для обработки
        type_slugs_to_process = self._get_type_slugs(ip_type_param)

        # Инициализируем статистику по типам
        for slug in type_slugs_to_process:
            self.stats['by_type'][slug] = {
                'total': 0,
                'success': 0,
                'failed': 0,
                'rate_limited': 0,
                'special': 0
            }

        # Запускаем основной цикл обработки с обработкой исключений
        try:
            self._run_processing(type_slugs_to_process)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n\n⏹️ Обработка прервана пользователем"))
            self._print_final_stats()
            sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n💥 Критическая ошибка: {e}"))
            logger.error(f"Critical error: {e}", exc_info=True)
            self._print_final_stats()
            sys.exit(1)

    # =========================================================================
    # МЕТОДЫ ИНИЦИАЛИЗАЦИИ И НАСТРОЙКИ
    # =========================================================================

    def _print_header(self, order_text: str):
        """Выводит красивый заголовок с параметрами запуска"""
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("🚀 ЗАПУСК ОБНОВЛЕНИЯ ДАННЫХ РИД ИЗ GOOGLE PATENTS"))
        self.stdout.write(self.style.SUCCESS("="*80))

        if self.force:
            self.stdout.write(self.style.WARNING("\n📌 РЕЖИМ: принудительное обновление (--force)"))

        self.stdout.write(f"\n📌 Порядок обработки: {order_text}")
        self.stdout.write(f"📌 Пакетная запись: {self.batch_size} записей")
        self.stdout.write(f"📌 Предпочитать русские тексты: {'ДА' if self.prefer_russian else 'НЕТ'}")

        if self.human_mode:
            self.stdout.write(f"📌 Мимикрия под человека: ВКЛЮЧЕНА")
            self.stdout.write(f"   • Ротация User-Agent: {len(self.user_agents)} вариантов")
            self.stdout.write(f"   • Умные задержки с длинными паузами")
        else:
            self.stdout.write(f"📌 Мимикрия под человека: ОТКЛЮЧЕНА")

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены\n"))

    def _get_type_slugs(self, ip_type_param: str) -> List[str]:
        """
        Преобразует параметр --ip-type в список слагов для обработки.

        Args:
            ip_type_param: Значение параметра (invention, all и т.д.)

        Returns:
            Список слагов типов РИД для обработки
        """
        if ip_type_param == 'all':
            type_slugs = list(self.type_slugs.values())
            self.stdout.write(f"📋 Обработка всех типов РИД: {', '.join(type_slugs)}")
            return type_slugs
        else:
            type_slugs = [self.type_slugs[ip_type_param]]
            self.stdout.write(f"📋 Обработка типа РИД: {ip_type_param}")
            return type_slugs

    def _init_session(self):
        """Инициализирует HTTP сессию с базовыми заголовками"""
        self.session = requests.Session()

        # Базовые заголовки, имитирующие браузер
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': random.choice(self.accept_languages),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def _rotate_headers(self):
        """
        Ротирует заголовки для каждого запроса.
        Это помогает избежать блокировки при большом количестве запросов.
        """
        if not self.human_mode:
            return

        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept-Language': random.choice(self.accept_languages),
        })

    def _apply_delay(self):
        """
        Умная задержка между запросами.
        Имитирует поведение человека: периодические длинные паузы,
        случайные вариации времени чтения страницы.
        """
        if self.delay <= 0:
            return

        if not self.human_mode:
            time.sleep(self.delay)
            return

        # Длинная пауза каждые 30-70 запросов (как будто человек отошёл)
        if self.request_count % random.randint(30, 70) == 0 and self.request_count > 0:
            long_delay = random.uniform(10, 40)
            if self.verbosity >= 1:
                self.stdout.write(f"\n   💤 ДЛИННАЯ ПАУЗА {long_delay:.1f} сек...")
            time.sleep(long_delay)
            return

        # Средняя пауза каждые 10-20 запросов (изучение страницы)
        if self.request_count % random.randint(10, 20) == 0 and self.request_count > 0:
            medium_delay = random.uniform(5, 20)
            if self.verbosity >= 2:
                self.stdout.write(f"\n   ⏱️ ПАУЗА {medium_delay:.1f} сек (изучение)...")
            time.sleep(medium_delay)
            return

        # Базовая случайная задержка
        base_delay = self.delay * random.uniform(0.7, 2.5)
        time.sleep(base_delay)

    # =========================================================================
    # МЕТОДЫ РАБОТЫ С БАЗОЙ ДАННЫХ (QUERYSET)
    # =========================================================================

    def _get_queryset(self, type_slugs: List[str]) -> models.QuerySet:
        """
        Формирует queryset записей для обработки с учётом параметров.

        Args:
            type_slugs: Список слагов типов для обработки

        Returns:
            QuerySet объектов IPObject для обработки
        """
        ip_types = IPType.objects.filter(slug__in=type_slugs)

        # Базовый queryset: только записи с регистрационным номером
        queryset = IPObject.objects.filter(
            ip_type__in=ip_types,
            registration_number__isnull=False
        ).exclude(
            registration_number=''
        ).select_related('ip_type')

        # Определяем стартовую позицию
        if self.start_from_id:
            # Явно указанный ID
            self.start_id = self.start_from_id
            self.stdout.write(self.style.WARNING(f"🎯 Старт с ID: {self.start_id}"))
            queryset = queryset.filter(id__gte=self.start_id)

        elif self.force:
            # Принудительно с начала (обрабатываем все записи, независимо от заполненности)
            self.stdout.write(self.style.WARNING("🎯 Режим --force: обрабатываем все записи"))

        else:
            # Автоматически находим первую запись с пустыми полями
            self.start_id = self._find_first_empty_record(queryset, ip_types)

            if self.start_id:
                self.stdout.write(self.style.WARNING(
                    f"🎯 Начинаем с ID {self.start_id} (первая запись с пустыми полями)"
                ))
                queryset = queryset.filter(id__gte=self.start_id)
            else:
                self.stdout.write(self.style.SUCCESS(
                    "✅ Все записи имеют заполненные поля! Обновлять нечего."
                ))
                return IPObject.objects.none()

        # Применяем сортировку
        if self.order_by:
            order_field = self.order_by
            if self.order_desc:
                order_field = f'-{order_field}'
            queryset = queryset.order_by(order_field)

        return queryset

    def _find_first_empty_record(self, queryset: models.QuerySet,
                                  ip_types: models.QuerySet) -> Optional[int]:
        """
        Находит ID первой записи, у которой хотя бы одно поле пустое.
        Используется только когда не включён режим --force.

        Args:
            queryset: Базовый queryset для поиска
            ip_types: Типы РИД для проверки

        Returns:
            ID первой пустой записи или None
        """
        # Собираем типы, у которых есть поля для парсинга
        types_with_fields = []
        for ip_type in ip_types:
            fields_map = self.type_fields_map.get(ip_type.slug, {})
            if fields_map:
                types_with_fields.append(ip_type)

        if not types_with_fields:
            self.stdout.write(self.style.WARNING("⚠️ Нет типов РИД с полями для парсинга"))
            return None

        # Определяем порядок сортировки
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

        # Ищем первую запись, удовлетворяющую условиям
        empty_qs = IPObject.objects.filter(
            registration_number__isnull=False
        ).exclude(
            registration_number=''
        ).filter(empty_conditions).order_by(order_by, 'id')

        first_empty = empty_qs.first()
        return first_empty.id if first_empty else None

    # =========================================================================
    # ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ С ПАКЕТНОЙ ЗАПИСЬЮ
    # =========================================================================

    def _run_processing(self, type_slugs_to_process: List[str]):
        """
        Запускает основной цикл обработки с пакетным сохранением.

        Args:
            type_slugs_to_process: Список типов для обработки
        """
        # Получаем queryset записей для обработки
        queryset = self._get_queryset(type_slugs_to_process)
        self.stats['total'] = queryset.count()

        self.stdout.write(f"\n📊 Найдено записей для обработки: {self.stats['total']}")

        if self.stats['total'] == 0:
            self.stdout.write(self.style.WARNING("⚠️ Нет записей для обработки"))
            return

        # Обрабатываем с пакетным накоплением
        self._process_with_batch_updates(queryset)

        # Выводим итоговую статистику
        self._print_final_stats()

    def _process_with_batch_updates(self, queryset: models.QuerySet):
        """
        Обрабатывает записи с накоплением изменений и пакетной записью.

        Args:
            queryset: QuerySet записей для обработки
        """
        total = queryset.count()

        # Применяем лимит запросов, если задан
        if self.max_requests and self.max_requests < total:
            self.stdout.write(self.style.WARNING(
                f"\n⏹️ Будет обработано только {self.max_requests} записей из {total} (лимит запросов)"
            ))
            queryset = queryset[:self.max_requests]
            total = self.max_requests

        # Буфер для накопления обновлений перед пакетной записью
        update_batch = []

        # Прогресс-бар для визуализации процесса
        with tqdm(total=total, desc="Обработка записей", unit="зап") as pbar:
            for ip_object in queryset.iterator(chunk_size=self.batch_size):
                # Проверка лимита запросов
                if self.max_requests and self.request_count >= self.max_requests:
                    self.stdout.write(self.style.WARNING(
                        f"\n⏹️ Достигнут лимит запросов ({self.max_requests})"
                    ))
                    # Сохраняем остаток перед выходом
                    if update_batch:
                        self._bulk_update_objects(update_batch)
                    return

                try:
                    # Обрабатываем одну запись
                    update_item = self._process_single_object(ip_object)

                    # Если есть данные для обновления, добавляем в буфер
                    if update_item:
                        update_batch.append(update_item)

                    # Если буфер заполнен, выполняем пакетную запись
                    if len(update_batch) >= self.batch_size:
                        self._bulk_update_objects(update_batch)
                        update_batch = []

                except RateLimitException:
                    # При rate limit сначала сохраняем накопленное
                    self.stats['rate_limited'] += 1
                    if update_batch:
                        self._bulk_update_objects(update_batch)
                        update_batch = []

                    if self.verbosity >= 1:
                        self.stdout.write(self.style.WARNING("\n   ⏳ Rate limit. Пауза 60 сек..."))
                    time.sleep(60)

                except Exception as e:
                    # Логируем неожиданные ошибки, но продолжаем работу
                    self.stats['errors'] += 1
                    if self.verbosity >= 1:
                        self.stdout.write(self.style.ERROR(f"\n❌ Неожиданная ошибка: {e}"))
                    logger.error(f"Unexpected error processing IPObject {ip_object.id}: {e}", exc_info=True)

                # Обновляем прогресс-бар
                pbar.update(1)
                pbar.set_postfix({
                    'OK': self.stats['success'],
                    'ERR': self.stats['failed'],
                    'BUF': len(update_batch),
                    'RTL': self.stats['rate_limited'],
                    'REQ': self.request_count
                })

                # Делаем паузу перед следующим запросом
                self._apply_delay()

            # Сохраняем остаток после завершения цикла
            if update_batch:
                self._bulk_update_objects(update_batch)

    # =========================================================================
    # ОБРАБОТКА ОДНОГО ОБЪЕКТА
    # =========================================================================

    def _process_single_object(self, ip_object: IPObject) -> Optional[Dict]:
        """
        Обрабатывает один объект РИД: запрос, парсинг, подготовка данных.

        Args:
            ip_object: Объект IPObject для обработки

        Returns:
            Словарь с данными для пакетного обновления или None
        """
        type_slug = ip_object.ip_type.slug
        self.stats['by_type'][type_slug]['total'] += 1
        self.stats['processed'] += 1

        # Пропускаем типы, по которым заведомо нет данных
        if type_slug in self.SKIP_TYPES:
            if self.verbosity >= 2:
                self.stdout.write(self.style.WARNING(
                    f"\n⏭️ Пропуск ID={ip_object.id}: тип {type_slug} не индексируется в Google Patents"
                ))
            self.stats['skipped'] += 1
            return None

        if self.verbosity >= 2:
            reg_date = ip_object.registration_date.strftime('%d.%m.%Y') if ip_object.registration_date else 'нет даты'
            self.stdout.write(f"\n🔍 Обработка ID={ip_object.id}, тип={type_slug}, дата={reg_date}")
            self.stdout.write(f"   Рег. номер: {ip_object.registration_number}")

        # Проверка наличия регистрационного номера
        if not ip_object.registration_number:
            self.stats['skipped'] += 1
            return None

        # Форматируем номер патента (всегда с префиксом RU)
        patent_number = self._format_patent_number(ip_object.registration_number)
        url = f"https://patents.google.com/patent/{patent_number}"

        # Получаем карту полей для данного типа
        fields_map = self.type_fields_map.get(type_slug, {})
        if not fields_map:
            self.stats['skipped'] += 1
            return None

        # В режиме --force мы не пропускаем записи, даже если поля заполнены
        # Но для статистики нам нужно знать, были ли поля заполнены до обновления
        if not self.force:
            # Проверяем, нужно ли обновлять запись (есть ли пустые поля)
            if not self._needs_update(ip_object, fields_map):
                if self.verbosity >= 2:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Все поля уже заполнены, пропуск"))
                self.stats['skipped'] += 1
                return None

        # Ротируем заголовки для мимикрии
        self._rotate_headers()
        self.request_count += 1

        try:
            # Запрашиваем страницу
            html_content = self._fetch_patent_page(url)

            if not html_content:
                self.stats['failed'] += 1
                self.stats['by_type'][type_slug]['failed'] += 1
                return None

            # Проверяем на специальные сообщения (нет документа)
            special_message = self._check_special_message(html_content)
            if special_message:
                return self._handle_special_message(ip_object, special_message, type_slug)

            # Парсим HTML и извлекаем данные
            soup = BeautifulSoup(html_content, 'html.parser')
            parsed_data = self._parse_all_fields(soup, fields_map)

            if parsed_data:
                return self._prepare_update_data(ip_object, parsed_data, type_slug)
            else:
                self.stats['failed'] += 1
                self.stats['by_type'][type_slug]['failed'] += 1
                return None

        except Exception as e:
            self.stats['errors'] += 1
            self.stats['failed'] += 1
            self.stats['by_type'][type_slug]['failed'] += 1

            if self.verbosity >= 1:
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка: {e}"))
            logger.error(f"Error processing IPObject {ip_object.id}: {e}", exc_info=True)
            return None

    def _needs_update(self, ip_object: IPObject, fields_map: Dict) -> bool:
        """
        Проверяет, нужно ли обновлять запись (есть ли пустые поля).

        Args:
            ip_object: Объект для проверки
            fields_map: Карта полей для данного типа

        Returns:
            True если нужно обновить, False если все поля заполнены
        """
        for target_field in fields_map.keys():
            if target_field in ['programming_languages', 'dbms']:
                # Для ManyToMany полей проверяем наличие связанных объектов
                if not getattr(ip_object, target_field).exists():
                    return True
            else:
                # Для текстовых полей проверяем наличие непустого значения
                current_value = getattr(ip_object, target_field)
                if not current_value or not current_value.strip():
                    return True
        return False

    def _format_patent_number(self, registration_number: str) -> str:
        """
        Форматирует номер патента для Google Patents.
        Всегда добавляет префикс RU, если его нет.

        Args:
            registration_number: Исходный номер из базы

        Returns:
            Отформатированный номер для URL
        """
        # Очищаем номер от лишних символов
        clean_number = re.sub(r'[^\w]', '', registration_number)

        # Убираем возможный префикс RU для унификации
        clean_number = re.sub(r'^RU', '', clean_number, flags=re.IGNORECASE)

        # Всегда добавляем RU
        return f"RU{clean_number}"

    def _fetch_patent_page(self, url: str) -> Optional[str]:
        """
        Выполняет HTTP запрос к Google Patents.

        Args:
            url: URL страницы патента

        Returns:
            HTML страницы или None в случае ошибки
        """
        try:
            if self.verbosity >= 2:
                self.stdout.write(f"   📡 Запрос к {url}")

            response = self.session.get(url, timeout=self.timeout)

            # Проверка на rate limiting
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

    def _check_special_message(self, html_content: str) -> Optional[str]:
        """
        Проверяет, не вернулась ли страница со специальным сообщением.

        Args:
            html_content: HTML страницы

        Returns:
            Текст сообщения или None
        """
        if len(html_content) < 1000 and "Документ с данным номером отсутствует" in html_content:
            return "Документ с данным номером отсутствует"
        return None

    def _handle_special_message(self, ip_object: IPObject,
                                 message: str, type_slug: str) -> Dict:
        """
        Обрабатывает случай со специальным сообщением (нет документа).

        Args:
            ip_object: Объект РИД
            message: Текст сообщения
            type_slug: Слаг типа

        Returns:
            Данные для обновления
        """
        self.stats['special_messages'] += 1
        self.stats['by_type'][type_slug]['special'] += 1

        return {
            'id': ip_object.id,
            'type_slug': type_slug,
            'data': {
                'abstract': f"[ОТВЕТ СЕРВЕРА] {message}"
            }
        }

    # =========================================================================
    # МЕТОДЫ ПАРСИНГА HTML
    # =========================================================================

    def _parse_all_fields(self, soup: BeautifulSoup,
                      fields_map: Dict) -> Optional[Dict]:
        """
        Парсит все поля из HTML в соответствии с картой полей.
        
        Args:
            soup: BeautifulSoup объект
            fields_map: Карта полей для данного типа
            
        Returns:
            Словарь с распарсенными данными или None
        """
        result = {}

        if self.verbosity >= 2:
            self.stdout.write(f"      🔍 Парсинг полей: {list(fields_map.keys())}")

        for target_field in fields_map.keys():
            if self.verbosity >= 2:
                self.stdout.write(f"      🔍 Обработка поля: {target_field}")

            value = None
            
            if target_field == 'abstract':
                # Поиск abstract
                if self.verbosity >= 2:
                    self.stdout.write("      🔍 _parse_abstract: начинаем поиск")
                
                # Способ 1: Ищем секцию abstract
                abstract_section = soup.find('section', id='abstract')
                if abstract_section:
                    if self.verbosity >= 2:
                        self.stdout.write("      ✅ Найдена секция abstract")
                    
                    patent_text = abstract_section.find('patent-text', {'name': 'abstract'})
                    if patent_text:
                        if self.verbosity >= 2:
                            self.stdout.write("      ✅ Найден patent-text с name='abstract'")
                        
                        # Ищем секцию с id='text' внутри
                        text_section = patent_text.find('section', id='text')
                        if text_section:
                            if self.verbosity >= 2:
                                self.stdout.write("      ✅ Найдена внутренняя секция с id='text'")
                            
                            # Ищем abstract с lang='RU'
                            abstract_elem = text_section.find('abstract', {'lang': 'RU'})
                            if abstract_elem:
                                if self.verbosity >= 2:
                                    self.stdout.write("      ✅ Найден abstract с lang='RU'")
                                
                                texts = []
                                for div in abstract_elem.find_all('div', class_='abstract'):
                                    text = div.get_text(strip=True)
                                    if text and self._contains_cyrillic(text):
                                        texts.append(text)
                                
                                if texts:
                                    value = '\n\n'.join(texts)
                                    if self.verbosity >= 2:
                                        self.stdout.write(f"      ✅ Найдено {len(texts)} блоков текста")
                
                # Способ 2: Прямой поиск abstract с lang='RU'
                if not value:
                    abstract_elem = soup.find('abstract', {'lang': 'RU'})
                    if abstract_elem:
                        texts = []
                        for div in abstract_elem.find_all('div', class_='abstract'):
                            text = div.get_text(strip=True)
                            if text and self._contains_cyrillic(text):
                                texts.append(text)
                        if texts:
                            value = '\n\n'.join(texts)
                            if self.verbosity >= 2:
                                self.stdout.write("      ✅ Найден abstract через прямой поиск")

            elif target_field == 'description':
                # Поиск description
                if self.verbosity >= 2:
                    self.stdout.write("      🔍 _parse_description: начинаем поиск")
                
                # Способ 1: Ищем секцию description
                desc_section = soup.find('section', id='description')
                if desc_section:
                    if self.verbosity >= 2:
                        self.stdout.write("      ✅ Найдена секция description")
                    
                    # Пробуем найти patent-text по id или name
                    patent_text = desc_section.find('patent-text', id='descriptionText')
                    if not patent_text:
                        patent_text = desc_section.find('patent-text', {'name': 'description'})
                    
                    if patent_text:
                        if self.verbosity >= 2:
                            self.stdout.write("      ✅ Найден patent-text")
                        
                        text_section = patent_text.find('section', id='text')
                        if text_section:
                            if self.verbosity >= 2:
                                self.stdout.write("      ✅ Найдена внутренняя секция с id='text'")
                            
                            desc_div = text_section.find('div', class_='description', attrs={'lang': 'RU'})
                            if desc_div:
                                if self.verbosity >= 2:
                                    self.stdout.write("      ✅ Найден div.description с lang='RU'")
                                
                                texts = []
                                for p in desc_div.find_all('div', class_='description-paragraph'):
                                    text = p.get_text(strip=True)
                                    if text and self._contains_cyrillic(text):
                                        text = re.sub(r'^\s*\d+\s+', '', text)
                                        texts.append(text)
                                
                                if texts:
                                    value = '\n\n'.join(texts)
                                    if self.verbosity >= 2:
                                        self.stdout.write(f"      ✅ Найдено {len(texts)} параграфов")
                
                # Способ 2: Прямой поиск div.description с lang='RU'
                if not value:
                    desc_div = soup.find('div', class_='description', attrs={'lang': 'RU'})
                    if desc_div:
                        texts = []
                        for p in desc_div.find_all('div', class_='description-paragraph'):
                            text = p.get_text(strip=True)
                            if text and self._contains_cyrillic(text):
                                text = re.sub(r'^\s*\d+\s+', '', text)
                                texts.append(text)
                        if texts:
                            value = '\n\n'.join(texts)
                            if self.verbosity >= 2:
                                self.stdout.write("      ✅ Найден description через прямой поиск")

            elif target_field == 'claims':
                # Поиск claims
                if self.verbosity >= 2:
                    self.stdout.write("      🔍 _parse_claims: начинаем поиск")
                
                # Способ 1: Ищем секцию claims
                claims_section = soup.find('section', id='claims')
                if claims_section:
                    if self.verbosity >= 2:
                        self.stdout.write("      ✅ Найдена секция claims")
                    
                    patent_text = claims_section.find('patent-text', {'name': 'claims'})
                    if patent_text:
                        if self.verbosity >= 2:
                            self.stdout.write("      ✅ Найден patent-text с name='claims'")
                        
                        text_section = patent_text.find('section', id='text')
                        if text_section:
                            if self.verbosity >= 2:
                                self.stdout.write("      ✅ Найдена внутренняя секция с id='text'")
                            
                            # Ищем ol или div с классом 'claims' и lang='RU'
                            claims_list = text_section.find('ol', class_='claims', attrs={'lang': 'RU'})
                            if not claims_list:
                                claims_list = text_section.find('div', class_='claims', attrs={'lang': 'RU'})
                            
                            if claims_list:
                                if self.verbosity >= 2:
                                    self.stdout.write(f"      ✅ Найден список claims, тег: {claims_list.name}")
                                
                                texts = []
                                # Ищем пункты в li с классом 'claim'
                                for li in claims_list.find_all('li', class_='claim'):
                                    claim_div = li.find('div', class_='claim')
                                    if claim_div:
                                        claim_text = claim_div.find('div', class_='claim-text')
                                        if claim_text:
                                            text = claim_text.get_text(strip=True)
                                            if text and self._contains_cyrillic(text):
                                                texts.append(text)
                                
                                # Если не нашли через li, ищем div с классом 'claim'
                                if not texts:
                                    for claim_div in claims_list.find_all('div', class_='claim'):
                                        claim_text = claim_div.find('div', class_='claim-text')
                                        if claim_text:
                                            text = claim_text.get_text(strip=True)
                                            if text and self._contains_cyrillic(text):
                                                texts.append(text)
                                
                                if texts:
                                    value = '\n\n'.join(texts)
                                    if self.verbosity >= 2:
                                        self.stdout.write(f"      ✅ Найдено {len(texts)} пунктов формулы")
                
                # Способ 2: Прямой поиск ol.claims с lang='RU'
                if not value:
                    claims_list = soup.find('ol', class_='claims', attrs={'lang': 'RU'})
                    if claims_list:
                        texts = []
                        for li in claims_list.find_all('li', class_='claim'):
                            claim_div = li.find('div', class_='claim')
                            if claim_div:
                                claim_text = claim_div.find('div', class_='claim-text')
                                if claim_text:
                                    text = claim_text.get_text(strip=True)
                                    if text and self._contains_cyrillic(text):
                                        texts.append(text)
                        if texts:
                            value = '\n\n'.join(texts)
                            if self.verbosity >= 2:
                                self.stdout.write("      ✅ Найдены claims через прямой поиск")
                
                # Специальная отладка для claims
                if self.verbosity >= 2:
                    if value:
                        preview = value[:200] + '...' if len(value) > 200 else value
                        self.stdout.write(self.style.SUCCESS(f"      ✅ claims НАЙДЕНЫ: {preview}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"      ❌ claims НЕ НАЙДЕНЫ"))

            elif target_field == 'programming_languages':
                value = self._parse_programming_languages(soup)
            elif target_field == 'dbms':
                value = self._parse_dbms(soup)
            else:
                continue

            if value:
                result[target_field] = value
                if self.verbosity >= 2 and target_field != 'claims':
                    preview = str(value)[:100] + '...' if len(str(value)) > 100 else str(value)
                    self.stdout.write(f"      ✅ Найдено {target_field}: {preview}")
            else:
                if self.verbosity >= 2 and target_field != 'claims':
                    self.stdout.write(f"      ❌ {target_field} не найден")

        return result if result else None

    def _parse_abstract(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Извлекает реферат (abstract) из HTML на основе реальной структуры.
        """
        if not soup:
            return None

        if self.verbosity >= 2:
            self.stdout.write("      🔍 _parse_abstract: начинаем поиск")

        # Ищем секцию abstract
        abstract_section = soup.find('section', id='abstract')
        if not abstract_section:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ Секция с id='abstract' не найдена")
            return None

        if self.verbosity >= 2:
            self.stdout.write("      ✅ Найдена секция с id='abstract'")

        # Ищем patent-text
        patent_text = abstract_section.find('patent-text', {'name': 'abstract'})
        if not patent_text:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ patent-text с name='abstract' не найден")
            return None

        # Ищем секцию с id='text'
        text_section = patent_text.find('section', id='text')
        if not text_section:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ Секция с id='text' не найдена внутри patent-text")
            return None

        # Ищем abstract с lang='RU'
        abstract_elem = text_section.find('abstract', {'lang': 'RU'})
        if not abstract_elem:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ abstract с lang='RU' не найден")
            return None

        # Собираем текст
        texts = []
        for div in abstract_elem.find_all('div', class_='abstract'):
            text = div.get_text(strip=True)
            if text and self._contains_cyrillic(text):
                texts.append(text)
                if self.verbosity >= 3:
                    preview = text[:100] + '...' if len(text) > 100 else text
                    self.stdout.write(f"        Найден текст: {preview}")

        if not texts:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ Нет текста в abstract")
            return None

        full_text = '\n\n'.join(texts)
        return self._clean_text(full_text)

    def _parse_description(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Извлекает описание (description) из HTML на основе реальной структуры.
        """
        if not soup:
            return None

        if self.verbosity >= 2:
            self.stdout.write("      🔍 _parse_description: начинаем поиск")

        # Ищем секцию description
        desc_section = soup.find('section', id='description')
        if not desc_section:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ Секция с id='description' не найдена")
            return None

        if self.verbosity >= 2:
            self.stdout.write("      ✅ Найдена секция с id='description'")

        # Ищем patent-text с id='descriptionText' или name='description'
        patent_text = desc_section.find('patent-text', id='descriptionText')
        if not patent_text:
            patent_text = desc_section.find('patent-text', {'name': 'description'})
            if not patent_text:
                if self.verbosity >= 2:
                    self.stdout.write("      ❌ patent-text не найден")
                return None

        # Ищем секцию с id='text'
        text_section = patent_text.find('section', id='text')
        if not text_section:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ Секция с id='text' не найдена внутри patent-text")
            return None

        # Ищем div с классом 'description' и lang='RU'
        desc_div = text_section.find('div', class_='description', attrs={'lang': 'RU'})
        if not desc_div:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ description с lang='RU' не найден")
            return None

        # Собираем все параграфы
        texts = []
        for p in desc_div.find_all('div', class_='description-paragraph'):
            text = p.get_text(strip=True)
            if text and self._contains_cyrillic(text):
                # Убираем номер параграфа
                text = re.sub(r'^\s*\d+\s+', '', text)
                texts.append(text)
                if self.verbosity >= 3:
                    preview = text[:100] + '...' if len(text) > 100 else text
                    self.stdout.write(f"        Найден параграф: {preview}")

        if not texts:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ Нет текста в description")
            return None

        full_text = '\n\n'.join(texts)
        return self._clean_text(full_text)

    def _parse_claims(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Извлекает формулу изобретения (claims) из HTML на основе реальной структуры.
        """
        if not soup:
            return None

        if self.verbosity >= 2:
            self.stdout.write("      🔍 _parse_claims: начинаем поиск")

        # Ищем секцию claims
        claims_section = soup.find('section', id='claims')
        if not claims_section:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ Секция с id='claims' не найдена")
            return None

        if self.verbosity >= 2:
            self.stdout.write("      ✅ Найдена секция с id='claims'")

        # Ищем patent-text с name='claims'
        patent_text = claims_section.find('patent-text', {'name': 'claims'})
        if not patent_text:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ patent-text с name='claims' не найден")
            return None

        # Ищем секцию с id='text'
        text_section = patent_text.find('section', id='text')
        if not text_section:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ Секция с id='text' не найдена внутри patent-text")
            return None

        # Ищем ol с классом 'claims' и lang='RU'
        claims_list = text_section.find('ol', class_='claims', attrs={'lang': 'RU'})
        if not claims_list:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ Список claims с lang='RU' не найден")
            return None

        # Собираем все пункты формулы
        texts = []
        for li in claims_list.find_all('li', class_='claim'):
            claim_div = li.find('div', class_='claim')
            if claim_div:
                claim_text = claim_div.find('div', class_='claim-text')
                if claim_text:
                    text = claim_text.get_text(strip=True)
                    if text and self._contains_cyrillic(text):
                        texts.append(self._clean_text(text))
                        if self.verbosity >= 3:
                            preview = text[:100] + '...' if len(text) > 100 else text
                            self.stdout.write(f"        Найден пункт: {preview}")

        if not texts:
            if self.verbosity >= 2:
                self.stdout.write("      ❌ Нет пунктов формулы")
            return None

        full_text = '\n\n'.join(texts)
        return self._clean_text(full_text)

    def _clean_text(self, text: str) -> str:
        """
        Очищает текст от HTML тегов и лишних пробелов.
        Сохраняет переносы строк как есть.
        
        Args:
            text: Исходный текст
            
        Returns:
            Очищенный текст
        """
        if not text or not isinstance(text, str):
            return text

        # Удаляем HTML теги (но сохраняем текст внутри них)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Убираем лишние пробелы в начале и конце строк
        text = text.strip()
        
        return text

    def _parse_programming_languages(self, soup: BeautifulSoup) -> Optional[List[str]]:
        """
        Извлекает упоминания языков программирования из текста.

        Args:
            soup: BeautifulSoup объект

        Returns:
            Список найденных языков или None
        """
        if not soup:
            return None

        text = soup.get_text()

        # Список популярных языков программирования
        prog_langs = [
            'Python', 'Java', 'C++', 'JavaScript', 'C#', 'PHP', 'Ruby',
            'Swift', 'Kotlin', 'Go', 'Rust', 'TypeScript', 'Perl', 'Scala',
        ]

        found_langs = []
        for lang in prog_langs:
            if re.search(rf'\b{re.escape(lang)}\b', text, re.I):
                found_langs.append(lang)

        return found_langs if found_langs else None

    def _parse_dbms(self, soup: BeautifulSoup) -> Optional[List[str]]:
        """
        Извлекает упоминания СУБД из текста.

        Args:
            soup: BeautifulSoup объект

        Returns:
            Список найденных СУБД или None
        """
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

    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ ОБРАБОТКИ ТЕКСТА
    # =========================================================================

    def _contains_cyrillic(self, text: str) -> bool:
        """
        Проверяет, содержит ли текст кириллические символы.

        Args:
            text: Проверяемый текст

        Returns:
            True если есть кириллица, иначе False
        """
        if not text or not isinstance(text, str):
            return False
        return bool(re.search('[а-яА-Я]', text))

    def _clean_text(self, text: str) -> str:
        """
        Очищает текст от HTML тегов и лишних пробелов.

        Args:
            text: Исходный текст

        Returns:
            Очищенный текст
        """
        if not text or not isinstance(text, str):
            return text

        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        # Заменяем множественные пробелы и переносы на один пробел
        text = re.sub(r'\s+', ' ', text)
        # Убираем пробелы в начале и конце
        text = text.strip()

        return text

    def _remove_header(self, text: str, header: str) -> str:
        """
        Удаляет заголовок из начала текста, если он там есть.

        Args:
            text: Исходный текст
            header: Заголовок для удаления

        Returns:
            Текст без заголовка
        """
        if not text or not header:
            return text

        # Различные варианты написания заголовка
        patterns = [
            rf'^{header}\s*',                    # "Description"
            rf'^{header}:\s*',                    # "Description:"
            rf'^{header}\s+translated\s+from\s*',  # "Description translated from"
            rf'^{header}\s+translated\s+from:?\s*', # "Description translated from:"
        ]

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                break

        return text.strip()

    # =========================================================================
    # ПОДГОТОВКА ДАННЫХ ДЛЯ ОБНОВЛЕНИЯ
    # =========================================================================

    def _prepare_update_data(self, ip_object: IPObject,
                              parsed_data: Dict,
                              type_slug: str) -> Optional[Dict]:
        """
        Подготавливает данные для пакетного обновления.

        Args:
            ip_object: Объект РИД
            parsed_data: Распарсенные данные
            type_slug: Слаг типа

        Returns:
            Словарь с данными для пакетного обновления или None
        """
        update_data = {
            'id': ip_object.id,
            'type_slug': type_slug,
            'data': {}
        }

        # Разделяем обычные поля и ManyToMany
        for field, value in parsed_data.items():
            if field in ['programming_languages', 'dbms']:
                # ManyToMany поля обновляем сразу (их нельзя в bulk_update)
                self._update_m2m_field(ip_object,
                                      ProgrammingLanguage if field == 'programming_languages' else DBMS,
                                      field, value)
                # Увеличиваем счётчик успешных обновлений для m2m
                self.stats['success'] += 1
                self.stats['by_type'][type_slug]['success'] += 1
            else:
                # Обычные поля копим для пакетного обновления
                update_data['data'][field] = value

        # Возвращаем данные, если есть обычные поля для обновления
        return update_data if update_data['data'] else None

    # =========================================================================
    # МЕТОДЫ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ
    # =========================================================================

    def _bulk_update_objects(self, update_batch: List[Dict]):
        """
        Выполняет пакетное обновление объектов в БД.

        Args:
            update_batch: Список словарей с данными для обновления
        """
        if not update_batch:
            return

        if self.dry_run:
            self.stdout.write(self.style.WARNING(
                f"\n📝 DRY-RUN: пропускаем пакетное обновление {len(update_batch)} записей"
            ))
            return

        # Собираем объекты для обновления и определяем поля
        objects_to_update = []
        fields_to_update: Set[str] = set()

        for item in update_batch:
            try:
                ip_object = IPObject.objects.get(id=item['id'])
                for field, value in item['data'].items():
                    setattr(ip_object, field, value)
                    fields_to_update.add(field)
                objects_to_update.append(ip_object)

                # Обновляем статистику
                self.stats['success'] += 1
                self.stats['by_type'][item['type_slug']]['success'] += 1

            except IPObject.DoesNotExist:
                # Запись могла быть удалена во время обработки
                self.stats['errors'] += 1
                logger.warning(f"IPObject with id {item['id']} not found during bulk update")

        # Выполняем один SQL запрос на все объекты
        if objects_to_update:
            IPObject.objects.bulk_update(objects_to_update, fields_to_update)

            if self.verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(
                    f"\n   💾 Пакетно обновлено {len(objects_to_update)} записей "
                    f"(поля: {', '.join(fields_to_update)})"
                ))

    def _update_m2m_field(self, ip_object: IPObject,
                          model_class, field_name: str, values: List[str]) -> bool:
        """
        Обновляет ManyToMany поле (языки программирования или СУБД).

        Args:
            ip_object: Объект РИД
            model_class: Класс модели (ProgrammingLanguage или DBMS)
            field_name: Имя поля
            values: Список значений для добавления

        Returns:
            True если были изменения, иначе False
        """
        if not values:
            return False

        manager = getattr(ip_object, field_name)
        objects_to_add = []

        # Создаём или получаем объекты
        for value in values:
            if isinstance(value, str) and value.strip():
                obj, _ = model_class.objects.get_or_create(name=value.strip())
                objects_to_add.append(obj)

        if objects_to_add:
            if self.force:
                # В принудительном режиме заменяем всё
                manager.clear()
                manager.add(*objects_to_add)
                return True
            else:
                # В обычном режиме только добавляем новые
                existing = set(manager.all())
                new_objects = [obj for obj in objects_to_add if obj not in existing]
                if new_objects:
                    manager.add(*new_objects)
                    return True

        return False

    # =========================================================================
    # СТАТИСТИКА И ЗАВЕРШЕНИЕ
    # =========================================================================

    def _print_final_stats(self):
        """Выводит итоговую статистику выполнения"""
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

        # Детальная статистика по типам
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
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены"))

        self.stdout.write(self.style.SUCCESS("="*80))