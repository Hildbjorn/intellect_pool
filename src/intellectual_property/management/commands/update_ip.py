"""
Команда для обновления данных РИД путем парсинга страниц ФИПС по publication_url.
Поддерживает все типы РИД с соответствующими полями для каждого типа.
"""

import logging
import re
import time
import random
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.db.models import Q, F
from tqdm import tqdm

from intellectual_property.models import IPObject, IPType, ProgrammingLanguage, DBMS
from django.conf import settings

logger = logging.getLogger(__name__)


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
            default=1.0,
            help='Задержка между запросами в секундах (по умолчанию 1.0)'
        )
        
        parser.add_argument(
            '--random-delay',
            action='store_true',
            help='Использовать случайную задержку (0.5-1.5 от указанной)'
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
            help='Принудительное обновление даже если поле уже заполнено'
        )
        
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Пропускать записи, у которых уже заполнены целевые поля'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Таймаут запроса в секундах (по умолчанию 30)'
        )
        
        parser.add_argument(
            '--user-agent',
            type=str,
            default='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            help='User-Agent для запросов'
        )
        
        parser.add_argument(
            '--only-actual',
            action='store_true',
            help='Обновлять только поле actual (статус), пропуская все остальные поля'
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
                'abstract': {'source': 'parse_abstract', 'target': 'abstract'},
                'claims': {'source': 'parse_claims', 'target': 'claims'},
                'actual': {'source': 'parse_status', 'target': 'actual'},
            },
            'utility-model': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract'},
                'claims': {'source': 'parse_claims', 'target': 'claims'},
                'actual': {'source': 'parse_status', 'target': 'actual'},
            },
            'industrial-design': {
                'actual': {'source': 'parse_status', 'target': 'actual'},
            },
            'integrated-circuit-topology': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract'},
            },
            'computer-program': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract'},
                'programming_languages': {'source': 'parse_programming_languages', 'target': 'programming_languages', 'is_m2m': True},
            },
            'database': {
                'abstract': {'source': 'parse_abstract', 'target': 'abstract'},
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
            'by_type': {},
        }
        
        self.session = None
        self.request_count = 0

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        self.batch_size = options['batch_size']
        self.delay = options['delay']
        self.random_delay = options['random_delay']
        self.max_requests = options['max_requests']
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.skip_existing = options['skip_existing']
        self.timeout = options['timeout']
        self.user_agent = options['user_agent']
        self.only_actual = options['only_actual']
        
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
        
        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("🚀 ЗАПУСК ОБНОВЛЕНИЯ ДАННЫХ РИД"))
        self.stdout.write(self.style.SUCCESS("="*80))
        
        if self.only_actual:
            self.stdout.write(self.style.WARNING("\n📌 РЕЖИМ: обновление только поля actual (статус)\n"))
        
        self.stdout.write(f"📌 Порядок обработки: {order_text}")
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ будут сохранены в БД\n"))
        
        # Инициализируем сессию
        self.init_session()
        
        # Получаем список типов для обработки
        if ip_type_param == 'all':
            type_slugs_to_process = list(self.type_slugs.values())
            self.stdout.write(f"📋 Обработка всех типов РИД: {', '.join(type_slugs_to_process)}")
        else:
            type_slugs_to_process = [self.type_slugs[ip_type_param]]
            self.stdout.write(f"📋 Обработка типа РИД: {ip_type_param}")
        
        # Инициализируем статистику по типам
        for slug in type_slugs_to_process:
            self.stats['by_type'][slug] = {'total': 0, 'success': 0, 'failed': 0, 'actual_updated': 0}
        
        # Получаем queryset для обработки
        queryset = self.get_queryset(type_slugs_to_process)
        self.stats['total'] = queryset.count()
        
        self.stdout.write(f"\n📊 Найдено записей для обработки: {self.stats['total']}")
        
        if self.stats['total'] == 0:
            self.stdout.write(self.style.WARNING("⚠️ Нет записей для обработки"))
            return
        
        # Обрабатываем по батчам
        self.process_in_batches(queryset)
        
        # Выводим итоговую статистику
        self.print_final_stats()

    def init_session(self):
        """Инициализация HTTP-сессии"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def get_queryset(self, type_slugs):
        """Получение queryset для обработки"""
        # Получаем типы по слагам
        ip_types = IPType.objects.filter(slug__in=type_slugs)
        
        # Базовый queryset
        queryset = IPObject.objects.filter(
            ip_type__in=ip_types,
            publication_url__isnull=False
        ).exclude(
            publication_url=''
        ).select_related('ip_type')
        
        # Фильтруем по заполненности полей, если нужно
        if self.skip_existing and not self.force and not self.only_actual:
            # Строим условия для пропуска уже заполненных полей
            skip_conditions = Q()
            
            for ip_type in ip_types:
                fields_map = self.type_fields_map.get(ip_type.slug, {})
                
                for field_info in fields_map.values():
                    target_field = field_info['target']
                    if not field_info.get('is_m2m', False):
                        # Для обычных полей проверяем, что они пустые
                        condition = Q(**{f"{target_field}__isnull": True}) | Q(**{f"{target_field}": ''})
                        skip_conditions &= condition
            
            queryset = queryset.filter(skip_conditions)
        
        # Применяем сортировку - ИСПРАВЛЕНО: убираем сложную логику с nulls_last
        if self.order_by:
            order_field = self.order_by
            if self.order_desc:
                order_field = f'-{order_field}'
            
            # Простая сортировка без обработки NULL
            queryset = queryset.order_by(order_field)
        
        return queryset

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
                
                # Обрабатываем запись
                self.process_single_object(ip_object)
                
                # Обновляем прогресс
                pbar.update(1)
                pbar.set_postfix({
                    'OK': self.stats['success'],
                    'ACT': self.stats['actual_updated'],
                    'ERR': self.stats['failed'],
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
        """Загрузка страницы по URL"""
        try:
            self.request_count += 1
            
            response = self.session.get(url, timeout=self.timeout)
            response.encoding = 'windows-1251'  # ФИПС использует windows-1251
            
            if response.status_code == 200:
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
        except Exception as e:
            if self.verbosity >= 2:
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка: {e}"))
            return None

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
                    status_text = status_value.get_text(strip=True).lower()
                    
                    # Проверяем наличие слова "действует" в любом контексте
                    # "Действует", "действует", "действует с", "действует до" и т.д.
                    if re.search(r'действует', status_text):
                        return True
                    else:
                        return False
        
        return None

    def parse_programming_languages(self, soup, type_slug):
        """Парсинг языков программирования для программ ЭВМ"""
        # Ищем строку с языком программирования
        b_tag = soup.find('b', string=re.compile(r'Язык программирования:', re.IGNORECASE))
        
        if b_tag:
            # Ищем текст в кавычках после тега <b>
            parent = b_tag.parent
            if parent:
                full_text = parent.get_text()
                # Ищем текст в кавычках
                quoted = re.findall(r'"([^"]*)"', full_text)
                if quoted:
                    # Берем первое вхождение в кавычках
                    languages_str = quoted[0]
                    # Разделяем по запятым, если несколько языков
                    languages = [lang.strip() for lang in languages_str.split(',')]
                    return languages
        
        return None

    def parse_dbms(self, soup, type_slug):
        """Парсинг СУБД для баз данных"""
        # Ищем строку с СУБД
        b_tag = soup.find('b', string=re.compile(r'Вид и версия системы управления базой данных:', re.IGNORECASE))
        
        if b_tag:
            parent = b_tag.parent
            if parent:
                full_text = parent.get_text()
                # Ищем текст в кавычках
                quoted = re.findall(r'"([^"]*)"', full_text)
                if quoted:
                    # Берем первое вхождение в кавычках
                    dbms_str = quoted[0]
                    # Разделяем по запятым, если несколько СУБД
                    dbms_list = [db.strip() for db in dbms_str.split(',')]
                    return dbms_list
        
        return None

    def update_object(self, ip_object, parsed_data, fields_map):
        """Обновление объекта РИД"""
        if self.dry_run:
            # В режиме dry-run просто показываем, что бы обновилось
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
                    # Для ManyToMany полей
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
                    # Для обычных полей
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
        
        # Получаем текущий менеджер
        manager = getattr(ip_object, field_name)
        
        # Находим или создаем объекты
        objects_to_add = []
        for value in values:
            if isinstance(value, str) and value.strip():
                obj, created = model_class.objects.get_or_create(name=value.strip())
                objects_to_add.append(obj)
        
        if objects_to_add:
            # Если force, очищаем и добавляем новые
            if self.force:
                manager.clear()
                manager.add(*objects_to_add)
                return True
            else:
                # Иначе добавляем только новые
                existing = set(manager.all())
                new_objects = [obj for obj in objects_to_add if obj not in existing]
                if new_objects:
                    manager.add(*new_objects)
                    return True
        
        return False

    def apply_delay(self):
        """Применение задержки между запросами"""
        if self.delay > 0:
            if self.random_delay:
                # Случайная задержка от 0.5 до 1.5 от указанной
                delay = random.uniform(self.delay * 0.5, self.delay * 1.5)
            else:
                delay = self.delay
            
            time.sleep(delay)

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
        self.stdout.write(f"❌ Неудачно: {self.stats['failed']}")
        self.stdout.write(f"⏭️  Пропущено: {self.stats['skipped']}")
        
        if self.stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"💥 Ошибок: {self.stats['errors']}"))
        
        self.stdout.write(f"📡 Выполнено запросов: {self.request_count}")
        
        # Статистика по типам
        self.stdout.write(self.style.SUCCESS("\n📊 ПО ТИПАМ РИД:"))
        for type_slug, stats in self.stats['by_type'].items():
            if stats['total'] > 0:
                success_rate = (stats['success'] / stats['total']) * 100 if stats['total'] > 0 else 0
                actual_info = f", actual={stats['actual_updated']}" if stats['actual_updated'] > 0 else ""
                self.stdout.write(
                    f"   {type_slug}: всего={stats['total']}, "
                    f"✅={stats['success']}, ❌={stats['failed']}{actual_info}, "
                    f"({success_rate:.1f}%)"
                )
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 РЕЖИМ DRY-RUN: изменения НЕ сохранены в БД"))
        
        self.stdout.write(self.style.SUCCESS("="*80))