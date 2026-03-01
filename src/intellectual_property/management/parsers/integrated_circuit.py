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