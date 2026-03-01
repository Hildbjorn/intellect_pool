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