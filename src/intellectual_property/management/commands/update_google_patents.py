"""
Команда для обновления данных РИД путём прямого парсинга Google Patents.
Поддерживает все типы РИД с соответствующими полями для каждого типа.

Использует requests для получения HTML страниц и BeautifulSoup для парсинга.

Логика работы в два этапа:
1. СБОР: формирует список ID записей, которые нужно обработать (пустые поля или --force)
2. ОБРАБОТКА: проходит по собранному списку, парсит страницы и сохраняет результаты

Преимущества:
- Чёткое разделение этапов
- Возможность прервать и продолжить обработку
- Лучший контроль над процессом
- Возможность сохранять список для отладки
"""

import logging
import re
import time
import random
import sys
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Set
from pathlib import Path

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
    help = 'Обновление данных РИД прямым парсингом Google Patents (двухэтапный режим)'

    # =========================================================================
    # НАСТРОЙКИ ПО УМОЛЧАНИЮ
    # =========================================================================
    DEFAULT_BATCH_SIZE = 100      # Размер пачки для записи в БД
    DEFAULT_DELAY = 2.0            # Базовая задержка между запросами (сек)
    DEFAULT_TIMEOUT = 30           # Таймаут HTTP запроса (сек)
    DEFAULT_MAX_REQUESTS = None    # Максимальное количество запросов (без лимита)
    DEFAULT_LIST_FILE = 'patent_ids_to_process.json'  # Файл для сохранения списка ID

    # Типы РИД, по которым заведомо нет данных в Google Patents
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
            default=self.DEFAULT_MAX_REQUESTS,
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

        # НОВЫЕ АРГУМЕНТЫ ДЛЯ ДВУХЭТАПНОГО РЕЖИМА
        parser.add_argument(
            '--stage',
            type=str,
            choices=['collect', 'process', 'both'],
            default='both',
            help='Этап выполнения: collect (только сбор ID), process (только обработка), both (оба этапа)'
        )

        parser.add_argument(
            '--list-file',
            type=str,
            default=self.DEFAULT_LIST_FILE,
            help=f'Файл для сохранения/загрузки списка ID патентов (по умолчанию {self.DEFAULT_LIST_FILE})'
        )

        parser.add_argument(
            '--resume',
            action='store_true',
            help='Продолжить обработку с последнего сохранённого прогресса'
        )

        parser.add_argument(
            '--keep-list',
            action='store_true',
            help='Не удалять файл со списком после успешной обработки'
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
            'collection': {                # Статистика этапа сбора
                'total_candidates': 0,
                'collected_ids': 0,
                'skipped_types': 0,
            }
        }

        # HTTP сессия для поддержки keep-alive и кук
        self.session = None
        self.request_count = 0            # Счётчик запросов
        self.start_id = None              # ID записи, с которой начали

        # Для двухэтапного режима
        self.patent_ids_to_process = []   # Список ID для обработки
        self.processed_ids = set()         # Множество уже обработанных ID
        self.progress_file = None          # Файл для сохранения прогресса

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

    # =========================================================================
    # ОСНОВНОЙ ПОТОК ВЫПОЛНЕНИЯ
    # =========================================================================

    def handle(self, *args, **options):
        """
        Главный метод команды.
        Реализует двухэтапную обработку: сбор ID и обработку.
        """
        # Сохраняем параметры
        self._init_params(options)
        
        # Выводим приветствие
        self._print_header()

        # Определяем этапы выполнения
        stage = options['stage']
        self.list_file = options['list_file']
        self.resume = options['resume']
        self.keep_list = options['keep_list']

        # Инициализируем HTTP сессию
        self._init_session()

        # ЭТАП 1: Сбор ID (если нужно)
        if stage in ['collect', 'both']:
            self._collect_ids_to_process()
            
            # Если только сбор - завершаем
            if stage == 'collect':
                self.stdout.write(self.style.SUCCESS(
                    f"\n✅ Этап сбора завершён. Список сохранён в {self.list_file}"
                ))
                return

        # ЭТАП 2: Обработка (если нужно)
        if stage in ['process', 'both']:
            # Загружаем список ID для обработки
            if not self._load_ids_to_process():
                return

            # Инициализируем статистику по типам
            for slug in self.type_slugs.values():
                self.stats['by_type'][slug] = {
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'rate_limited': 0,
                    'special': 0
                }

            # Загружаем прогресс если нужно
            if self.resume:
                self._load_progress()

            # Запускаем обработку
            self._process_id_list()

        # Финальная статистика
        self._print_final_stats()

        # Очищаем временные файлы если нужно
        if not self.keep_list and os.path.exists(self.list_file):
            os.remove(self.list_file)
            self.stdout.write(self.style.SUCCESS(f"🧹 Временный файл {self.list_file} удалён"))

    def _init_params(self, options):
        """Инициализация параметров из командной строки"""
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
        self.ip_type_param = options['ip_type']

        # Определяем порядок сортировки
        if options['start_from_oldest']:
            self.order_by = 'registration_date'
            self.order_desc = False
            self.order_text = "от старых к новым"
        else:
            self.order_by = 'registration_date'
            self.order_desc = True
            self.order_text = "от новых к старым"

    def _print_header(self):
        """Выводит заголовок с параметрами запуска"""
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("🚀 ЗАПУСК ОБНОВЛЕНИЯ ДАННЫХ РИД ИЗ GOOGLE PATENTS"))
        self.stdout.write(self.style.SUCCESS("="*80))

        if self.force:
            self.stdout.write(self.style.WARNING("\n📌 РЕЖИМ: принудительное обновление (--force)"))

        self.stdout.write(f"\n📌 Тип РИД: {self.ip_type_param}")
        self.stdout.write(f"📌 Порядок обработки: {self.order_text}")
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
        """Получение списка слагов типов для обработки"""
        if ip_type_param == 'all':
            return list(self.type_slugs.values())
        else:
            return [self.type_slugs[ip_type_param]]

    def _init_session(self):
        """Инициализирует HTTP сессию с базовыми заголовками"""
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': random.choice(self.accept_languages),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def _rotate_headers(self):
        """Ротация заголовков для каждого запроса"""
        if not self.human_mode:
            return
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept-Language': random.choice(self.accept_languages),
        })

    def _apply_delay(self):
        """Умная задержка между запросами"""
        if self.delay <= 0:
            return
        if not self.human_mode:
            time.sleep(self.delay)
            return
        
        if self.request_count % random.randint(30, 70) == 0 and self.request_count > 0:
            long_delay = random.uniform(10, 40)
            if self.verbosity >= 1:
                self.stdout.write(f"\n   💤 ДЛИННАЯ ПАУЗА {long_delay:.1f} сек...")
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

    # =========================================================================
    # ЭТАП 1: СБОР ID ЗАПИСЕЙ ДЛЯ ОБРАБОТКИ
    # =========================================================================

    def _collect_ids_to_process(self):
        """
        Собирает ID записей, которые нужно обработать.
        Сохраняет их в файл для последующей обработки.
        """
        self.stdout.write(self.style.SUCCESS("\n📋 ЭТАП 1: СБОР ID ЗАПИСЕЙ ДЛЯ ОБРАБОТКИ"))
        
        # Получаем типы для обработки
        type_slugs = self._get_type_slugs(self.ip_type_param)
        ip_types = IPType.objects.filter(slug__in=type_slugs)

        # Формируем базовый queryset
        base_queryset = IPObject.objects.filter(
            ip_type__in=ip_types,
            registration_number__isnull=False
        ).exclude(
            registration_number=''
        ).select_related('ip_type')

        # Применяем стартовую позицию если указана
        if self.start_from_id:
            base_queryset = base_queryset.filter(id__gte=self.start_from_id)
            self.stdout.write(self.style.WARNING(f"🎯 Старт с ID: {self.start_from_id}"))

        # Применяем сортировку
        if self.order_by:
            order_field = self.order_by
            if self.order_desc:
                order_field = f'-{order_field}'
            base_queryset = base_queryset.order_by(order_field)

        # Получаем общее количество кандидатов
        total_candidates = base_queryset.count()
        self.stats['collection']['total_candidates'] = total_candidates
        self.stdout.write(f"\n📊 Всего кандидатов: {total_candidates}")

        if total_candidates == 0:
            self.stdout.write(self.style.WARNING("⚠️ Нет записей для обработки"))
            return

        # Формируем условия для поиска записей, которые нужно обработать
        if self.force:
            # В режиме --force берём все записи
            need_update_qs = base_queryset
            self.stdout.write(self.style.WARNING("🎯 Режим --force: обрабатываем ВСЕ записи"))
        else:
            # Ищем записи с пустыми полями
            need_update_conditions = Q()
            for slug in type_slugs:
                fields_map = self.type_fields_map.get(slug, {})
                if fields_map:
                    type_conditions = Q(ip_type__slug=slug) & (
                        Q(abstract__isnull=True) | Q(abstract='') |
                        Q(description__isnull=True) | Q(description='') |
                        Q(claims__isnull=True) | Q(claims='')
                    )
                    need_update_conditions |= type_conditions
            
            need_update_qs = base_queryset.filter(need_update_conditions)
            
            # Пропускаем типы, по которым заведомо нет данных
            need_update_qs = need_update_qs.exclude(ip_type__slug__in=self.SKIP_TYPES)
            skipped_count = base_queryset.filter(ip_type__slug__in=self.SKIP_TYPES).count()
            self.stats['collection']['skipped_types'] = skipped_count
            if skipped_count > 0:
                self.stdout.write(self.style.WARNING(
                    f"⏭️ Пропущено {skipped_count} записей типов {', '.join(self.SKIP_TYPES)}"
                ))

        # Получаем список ID для обработки
        id_list = list(need_update_qs.values_list('id', flat=True))
        self.stats['collection']['collected_ids'] = len(id_list)

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Собрано {len(id_list)} ID для обработки"
        ))

        # Сохраняем в файл
        with open(self.list_file, 'w', encoding='utf-8') as f:
            json.dump({
                'collected_at': datetime.now().isoformat(),
                'total_candidates': total_candidates,
                'collected_ids': len(id_list),
                'skipped_types': self.stats['collection']['skipped_types'],
                'ids': id_list
            }, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"💾 Список сохранён в {self.list_file}"))

    def _load_ids_to_process(self) -> bool:
        """
        Загружает список ID для обработки из файла.
        
        Returns:
            True если загрузка успешна, иначе False
        """
        if not os.path.exists(self.list_file):
            self.stdout.write(self.style.ERROR(
                f"❌ Файл со списком ID не найден: {self.list_file}\n"
                f"   Сначала выполните сбор: --stage=collect"
            ))
            return False

        try:
            with open(self.list_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.patent_ids_to_process = data['ids']
            self.stats['total'] = len(self.patent_ids_to_process)
            
            self.stdout.write(self.style.SUCCESS(
                f"\n📋 ЭТАП 2: ОБРАБОТКА {len(self.patent_ids_to_process)} ЗАПИСЕЙ"
            ))
            self.stdout.write(f"📊 Данные собраны: {data['collected_at']}")
            self.stdout.write(f"   • Всего кандидатов: {data['total_candidates']}")
            self.stdout.write(f"   • Пропущено типов: {data.get('skipped_types', 0)}")
            
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка загрузки файла: {e}"))
            return False

    # =========================================================================
    # ЭТАП 2: ОБРАБОТКА ЗАПИСЕЙ ПО ID
    # =========================================================================

    def _process_id_list(self):
        """
        Обрабатывает список ID с пакетным сохранением.
        """
        total = len(self.patent_ids_to_process)
        
        # Буфер для накопления обновлений
        update_batch = []

        # Прогресс-бар
        with tqdm(total=total, desc="Обработка записей", unit="зап") as pbar:
            for idx, obj_id in enumerate(self.patent_ids_to_process):
                
                # Пропускаем уже обработанные
                if obj_id in self.processed_ids:
                    pbar.update(1)
                    continue

                # Проверка лимита запросов
                if self.max_requests and self.request_count >= self.max_requests:
                    self.stdout.write(self.style.WARNING(
                        f"\n⏹️ Достигнут лимит запросов ({self.max_requests})"
                    ))
                    self._save_progress(idx)
                    if update_batch:
                        self._bulk_update_objects(update_batch)
                    return

                try:
                    # Получаем объект из БД
                    try:
                        ip_object = IPObject.objects.get(id=obj_id)
                    except IPObject.DoesNotExist:
                        self.stats['errors'] += 1
                        self.processed_ids.add(obj_id)
                        pbar.update(1)
                        continue

                    # Обрабатываем одну запись
                    update_item = self._process_single_object(ip_object)

                    # Если есть данные для обновления, добавляем в буфер
                    if update_item:
                        update_batch.append(update_item)

                    # Помечаем как обработанный
                    self.processed_ids.add(obj_id)

                    # Если буфер заполнен, выполняем пакетную запись
                    if len(update_batch) >= self.batch_size:
                        self._bulk_update_objects(update_batch)
                        update_batch = []
                        
                        # Сохраняем прогресс каждые 1000 записей
                        if len(self.processed_ids) % 1000 == 0:
                            self._save_progress(idx)

                except RateLimitException:
                    self.stats['rate_limited'] += 1
                    if update_batch:
                        self._bulk_update_objects(update_batch)
                        update_batch = []
                    self._save_progress(idx)
                    
                    if self.verbosity >= 1:
                        self.stdout.write(self.style.WARNING("\n   ⏳ Rate limit. Пауза 60 сек..."))
                    time.sleep(60)

                except Exception as e:
                    self.stats['errors'] += 1
                    if self.verbosity >= 1:
                        self.stdout.write(self.style.ERROR(f"\n❌ Неожиданная ошибка: {e}"))
                    logger.error(f"Unexpected error processing ID {obj_id}: {e}", exc_info=True)

                # Обновляем прогресс-бар
                pbar.update(1)
                pbar.set_postfix({
                    'OK': self.stats['success'],
                    'ERR': self.stats['failed'],
                    'BUF': len(update_batch),
                    'RTL': self.stats['rate_limited'],
                    'REQ': self.request_count
                })

                # Делаем паузу
                self._apply_delay()

            # Сохраняем остаток после завершения цикла
            if update_batch:
                self._bulk_update_objects(update_batch)
            
            # Удаляем файл прогресса если он был
            if self.progress_file and os.path.exists(self.progress_file):
                os.remove(self.progress_file)

    def _save_progress(self, last_index: int):
        """
        Сохраняет текущий прогресс для возможности возобновления.
        """
        if not self.progress_file:
            self.progress_file = f"{self.list_file}.progress.json"
        
        progress_data = {
            'last_index': last_index,
            'processed_ids': list(self.processed_ids),
            'request_count': self.request_count,
            'stats': self.stats,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        if self.verbosity >= 1:
            self.stdout.write(self.style.WARNING(
                f"\n💾 Прогресс сохранён (обработано {len(self.processed_ids)} записей)"
            ))

    def _load_progress(self):
        """
        Загружает прогресс из файла.
        """
        progress_file = f"{self.list_file}.progress.json"
        
        if not os.path.exists(progress_file):
            self.stdout.write(self.style.WARNING(
                "⚠️ Файл прогресса не найден, начинаем с начала"
            ))
            self.processed_ids = set()
            return
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.processed_ids = set(data['processed_ids'])
            self.request_count = data.get('request_count', 0)
            # Восстанавливаем статистику
            for key in ['success', 'failed', 'errors', 'rate_limited', 'special_messages']:
                if key in data['stats']:
                    self.stats[key] = data['stats'][key]
            
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Загружен прогресс: обработано {len(self.processed_ids)} записей"
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"❌ Ошибка загрузки прогресса: {e}\n   Начинаем с начала"
            ))
            self.processed_ids = set()

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

        patterns = [
            rf'^{header}\s*',
            rf'^{header}:\s*',
            rf'^{header}\s+translated\s+from\s*',
            rf'^{header}\s+translated\s+from:?\s*',
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
                # ManyToMany поля обновляем сразу
                self._update_m2m_field(ip_object,
                                      ProgrammingLanguage if field == 'programming_languages' else DBMS,
                                      field, value)
                self.stats['success'] += 1
                self.stats['by_type'][type_slug]['success'] += 1
            else:
                update_data['data'][field] = value

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

        objects_to_update = []
        fields_to_update: Set[str] = set()

        for item in update_batch:
            try:
                ip_object = IPObject.objects.get(id=item['id'])
                for field, value in item['data'].items():
                    setattr(ip_object, field, value)
                    fields_to_update.add(field)
                objects_to_update.append(ip_object)

                self.stats['success'] += 1
                self.stats['by_type'][item['type_slug']]['success'] += 1

            except IPObject.DoesNotExist:
                self.stats['errors'] += 1
                logger.warning(f"IPObject with id {item['id']} not found during bulk update")

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