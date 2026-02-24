"""
Парсер для изобретений с пакетной обработкой
"""

import logging
from collections import defaultdict
import gc
import re

from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.db import transaction
from tqdm import tqdm
import pandas as pd

from intellectual_property.models import IPObject, IPType, Person
from core.models import Organization
from .base import BaseFIPSParser

logger = logging.getLogger(__name__)


class InventionParser(BaseFIPSParser):
    """Парсер для изобретений с пакетной обработкой"""

    def get_ip_type(self):
        return IPType.objects.filter(slug='invention').first()

    def get_required_columns(self):
        return ['registration number', 'invention name']

    def _has_data_changed(self, obj, new_data):
        """Проверяет, изменились ли данные"""
        fields_to_check = [
            ('name', obj.name, new_data['name']),
            ('application_date', obj.application_date, new_data['application_date']),
            ('registration_date', obj.registration_date, new_data['registration_date']),
            ('patent_starting_date', obj.patent_starting_date, new_data['patent_starting_date']),
            ('expiration_date', obj.expiration_date, new_data['expiration_date']),
            ('actual', obj.actual, new_data['actual']),
            ('publication_url', obj.publication_url, new_data['publication_url']),
            ('abstract', obj.abstract, new_data['abstract']),
            ('claims', obj.claims, new_data['claims']),
            ('creation_year', obj.creation_year, new_data['creation_year']),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue):
        self.stdout.write(self.style.SUCCESS("  🔄 Начинаем парсинг изобретений..."))

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'skipped': 0,
            'skipped_by_date': 0,
            'errors': 0
        }

        ip_type = self.get_ip_type()
        if not ip_type:
            self.stdout.write(self.style.ERROR("  ❌ Тип РИД 'invention' не найден в БД"))
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # ШАГ 1: Собираем регистрационные номера
        self.stdout.write("  📥 Чтение CSV...")
        all_reg_numbers = []
        reg_num_to_row = {}

        with tqdm(total=len(df), desc="     Прогресс", unit=" зап", leave=False) as pbar:
            for idx, row in df.iterrows():
                reg_num = self.clean_string(row.get('registration number'))
                if reg_num:
                    all_reg_numbers.append(reg_num)
                    reg_num_to_row[reg_num] = row
                pbar.update(1)

        self.stdout.write(f"  📊 Всего записей в CSV: {len(all_reg_numbers)}")

        # ШАГ 2: Загружаем существующие записи
        self.stdout.write("  🔍 Загрузка существующих записей из БД...")
        existing_objects = {}
        batch_size = 500

        with tqdm(total=len(all_reg_numbers), desc="     Загрузка пачками", unit=" зап") as pbar:
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_numbers = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                pbar.update(len(batch_numbers))

        self.stdout.write(f"  📊 Найдено в БД: {len(existing_objects)}")

        # ШАГ 3: Подготовка данных с оптимизацией памяти
        self.stdout.write("  🔄 Подготовка данных...")
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        # Используем списки для связей
        authors_data = []
        holders_data = []
        
        # Прогресс-бар для подготовки данных
        with tqdm(total=len(reg_num_to_row), desc="     Обработка записей", unit=" зап") as pbar:
            for reg_num, row in reg_num_to_row.items():
                try:
                    # Проверка по дате
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            continue

                    # Форматируем название
                    name = self.clean_string(row.get('invention name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Изобретение №{reg_num}"

                    # Парсим даты
                    application_date = self.parse_date(row.get('application date'))
                    registration_date = self.parse_date(row.get('registration date'))
                    patent_starting_date = self.parse_date(row.get('patent starting date'))
                    expiration_date = self.parse_date(row.get('expiration date'))
                    actual = self.parse_bool(row.get('actual'))
                    publication_url = self.clean_string(row.get('publication URL'))
                    abstract = self.clean_string(row.get('abstract'))
                    claims = self.clean_string(row.get('claims'))

                    creation_year = None
                    if application_date:
                        creation_year = application_date.year
                    elif registration_date:
                        creation_year = registration_date.year

                    obj_data = {
                        'registration_number': reg_num,
                        'ip_type': ip_type,
                        'name': name,
                        'application_date': application_date,
                        'registration_date': registration_date,
                        'patent_starting_date': patent_starting_date,
                        'expiration_date': expiration_date,
                        'actual': actual,
                        'publication_url': publication_url,
                        'abstract': abstract,
                        'claims': claims,
                        'creation_year': creation_year,
                    }

                    if reg_num in existing_objects:
                        if self._has_data_changed(existing_objects[reg_num], obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Сохраняем связи отдельно
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors = self.parse_authors(authors_str)
                        for author in authors:
                            authors_data.append((reg_num, author))

                    holders_str = row.get('patent holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders = self.parse_patent_holders(holders_str)
                        for holder in holders:
                            holders_data.append((reg_num, holder))

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    self.stdout.write(self.style.ERROR(f"\n  ❌ Ошибка подготовки записи {reg_num}: {e}"))
                    logger.error(f"Error preparing invention {reg_num}: {e}", exc_info=True)

                pbar.update(1)
                
                # Периодическая очистка памяти (каждые 10000 записей)
                if pbar.n % 10000 == 0:
                    gc.collect()

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        self.stdout.write(f"     Итого: новых={len(to_create)}, обновление={len(to_update)}, без изменений={unchanged_count}")

        # ШАГ 4: Пакетное создание новых записей
        if to_create and not self.command.dry_run:
            self.stdout.write(f"  📦 Создание {len(to_create)} записей...")
            created_count = self._bulk_create_objects(to_create)
            stats['created'] = created_count

        # ШАГ 5: Пакетное обновление
        if to_update and not self.command.dry_run:
            self.stdout.write(f"  📦 Обновление {len(to_update)} записей...")
            updated_count = self._bulk_update_objects(to_update, existing_objects)
            stats['updated'] = updated_count

        # ШАГ 6: Обработка авторов
        if authors_data and not self.command.dry_run:
            self.stdout.write(f"  📦 Обработка авторов ({len(set(r for r, _ in authors_data))} записей)...")
            self._process_authors_optimized(existing_objects, authors_data)

        # ШАГ 7: Обработка правообладателей
        if holders_data and not self.command.dry_run:
            self.stdout.write(f"  📦 Обработка патентообладателей ({len(set(r for r, _ in holders_data))} записей)...")
            self._process_holders_optimized(existing_objects, holders_data)

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']
        
        # Очистка памяти в конце
        gc.collect()

        self.stdout.write(self.style.SUCCESS(f"  ✅ Парсинг изобретений завершен"))
        self.stdout.write(f"     Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}, "
                         f"Пропущено всего: {stats['skipped']} (из них по дате: {stats['skipped_by_date']}), "
                         f"Ошибок: {stats['errors']}")

        return stats

    def _bulk_create_objects(self, to_create):
        """Пакетное создание объектов с контролем памяти"""
        created_count = 0
        batch_size = 1000
        
        with tqdm(total=len(to_create), desc="     Создание", unit=" зап") as pbar:
            for i in range(0, len(to_create), batch_size):
                batch_data = to_create[i:i+batch_size]
                create_objects = [IPObject(**data) for data in batch_data]
                IPObject.objects.bulk_create(create_objects, batch_size=batch_size)
                created_count += len(batch_data)
                pbar.update(len(batch_data))
                
                # Очистка памяти после каждого батча
                if i % 10000 == 0:
                    gc.collect()
        
        return created_count

    def _bulk_update_objects(self, to_update, existing_objects):
        """Пакетное обновление объектов"""
        updated_count = 0
        BATCH_UPDATE_SIZE = 500
        
        with tqdm(total=len(to_update), desc="     Обновление", unit=" зап") as pbar:
            for i in range(0, len(to_update), BATCH_UPDATE_SIZE):
                batch_data = to_update[i:i+BATCH_UPDATE_SIZE]
                with transaction.atomic():
                    for data in batch_data:
                        obj = existing_objects[data['registration_number']]
                        update_fields = []
                        for field, value in data.items():
                            if field != 'registration_number' and getattr(obj, field) != value:
                                setattr(obj, field, value)
                                update_fields.append(field)
                        if update_fields:
                            obj.save(update_fields=update_fields)
                            updated_count += 1
                pbar.update(len(batch_data))
                
                # Очистка памяти
                if i % 5000 == 0:
                    gc.collect()
        
        return updated_count

    def _process_authors_optimized(self, existing_objects, authors_data):
        """Оптимизированная обработка авторов с сохранением Natasha"""
        self.stdout.write(f"     ⚡ Обработка авторов (оптимизировано)...")
        
        # ШАГ 1: Группировка по авторам с использованием словарей
        self.stdout.write("        Шаг 1/6: Сбор уникальных авторов...")
        
        # Используем обычные словари вместо defaultdict для экономии памяти
        author_to_ips = {}
        author_details = {}
        
        with tqdm(total=len(authors_data), desc="           Группировка", unit=" зап") as pbar:
            for reg_num, author in authors_data:
                ip_object = existing_objects.get(reg_num)
                if not ip_object:
                    pbar.update(1)
                    continue
                
                # Создаем ключ
                key = f"{author['last_name']}|{author['first_name']}|{author['middle_name']}"
                
                # Добавляем IP к автору
                if key not in author_to_ips:
                    author_to_ips[key] = set()
                    author_details[key] = author
                author_to_ips[key].add(ip_object.pk)
                
                pbar.update(1)
        
        all_keys = list(author_to_ips.keys())
        self.stdout.write(f"        Уникальных авторов: {len(all_keys)}")
        
        # ШАГ 2: Поиск в БД (пачками)
        self.stdout.write("        Шаг 2/6: Поиск в БД...")
        existing_people = {}
        BATCH_SIZE = 100
        
        with tqdm(total=len(all_keys), desc="           Поиск", unit=" ключ") as pbar:
            for i in range(0, len(all_keys), BATCH_SIZE):
                batch_keys = all_keys[i:i+BATCH_SIZE]
                
                # Строим условие для поиска
                name_conditions = Q()
                for key in batch_keys:
                    last, first, middle = key.split('|')
                    if middle:
                        name_conditions |= Q(
                            last_name=last,
                            first_name=first,
                            middle_name=middle
                        )
                    else:
                        name_conditions |= Q(
                            last_name=last,
                            first_name=first,
                            middle_name__isnull=True
                        ) | Q(
                            last_name=last,
                            first_name=first,
                            middle_name=''
                        )
                
                # Выполняем поиск
                for person in Person.objects.filter(name_conditions).only(
                    'id', 'last_name', 'first_name', 'middle_name'
                ):
                    key = f"{person.last_name}|{person.first_name}|{person.middle_name or ''}"
                    existing_people[key] = person
                    self.person_cache[key] = person
                
                pbar.update(len(batch_keys))
                
                # Периодическая очистка
                if i % 1000 == 0:
                    gc.collect()
        
        self.stdout.write(f"        Найдено существующих: {len(existing_people)}")
        
        # ШАГ 3: Подготовка новых авторов
        self.stdout.write("        Шаг 3/6: Подготовка новых авторов...")
        
        # Определяем новых авторов
        new_keys = [key for key in all_keys if key not in existing_people]
        
        if new_keys:
            # Получаем максимальный ID и существующие slugs
            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
            existing_slugs = set(Person.objects.values_list('slug', flat=True)[:100000])
            
            people_to_create = []
            key_to_new_person = {}
            
            with tqdm(total=len(new_keys), desc="           Подготовка", unit=" ключ") as pbar:
                for key in new_keys:
                    author = author_details[key]
                    
                    # Формируем имя для slug
                    name_parts = [author['last_name'], author['first_name']]
                    if author['middle_name']:
                        name_parts.append(author['middle_name'])
                    
                    # Генерируем уникальный slug
                    base_slug = slugify(' '.join(name_parts).strip())
                    if not base_slug:
                        base_slug = 'person'
                    
                    unique_slug = base_slug
                    counter = 1
                    while unique_slug in existing_slugs:
                        unique_slug = f"{base_slug}-{counter}"
                        counter += 1
                    existing_slugs.add(unique_slug)
                    
                    # Создаем объект Person
                    person = Person(
                        ceo_id=max_id + len(people_to_create) + 1,
                        ceo=author['full_name'],
                        last_name=author['last_name'],
                        first_name=author['first_name'],
                        middle_name=author['middle_name'] or '',
                        slug=unique_slug
                    )
                    people_to_create.append(person)
                    key_to_new_person[key] = person
                    
                    pbar.update(1)
                    
                    # Периодическое создание для экономии памяти
                    if len(people_to_create) >= 500:
                        Person.objects.bulk_create(people_to_create, batch_size=500)
                        people_to_create = []
                        gc.collect()
            
            # Создаем оставшихся
            if people_to_create:
                Person.objects.bulk_create(people_to_create, batch_size=500)
            
            self.stdout.write(f"        Создано новых авторов: {len(new_keys)}")
            
            # Обновляем кэш
            for person in Person.objects.filter(ceo__in=[author_details[key]['full_name'] for key in new_keys]):
                key = f"{person.last_name}|{person.first_name}|{person.middle_name or ''}"
                existing_people[key] = person
                self.person_cache[key] = person
        
        # ШАГ 4: Подготовка связей
        self.stdout.write("        Шаг 4/6: Подготовка связей...")
        
        through_objs = []
        
        with tqdm(total=len(all_keys), desc="           Сбор связей", unit=" автор") as pbar:
            for key in all_keys:
                person = existing_people.get(key)
                if not person:
                    pbar.update(1)
                    continue
                
                for ip_id in author_to_ips[key]:
                    through_objs.append(
                        IPObject.authors.through(
                            ipobject_id=ip_id,
                            person_id=person.pk
                        )
                    )
                pbar.update(1)
        
        self.stdout.write(f"        Уникальных связей для создания: {len(through_objs)}")
        
        # ШАГ 5: Создание связей с прогресс-баром
        if through_objs:
            self.stdout.write("        Шаг 5/6: Создание связей...")
            
            # Получаем все уникальные ID IP-объектов
            ip_ids = list(set(obj.ipobject_id for obj in through_objs))
            
            # Удаляем старые связи с ПРОГРЕСС-БАРОМ
            self.stdout.write(f"           Удаление старых связей для {len(ip_ids)} IP-объектов...")
            delete_batch_size = 500
            deleted_total = 0
            
            with tqdm(total=len(ip_ids), desc="           Удаление", unit=" ip") as pbar:
                for i in range(0, len(ip_ids), delete_batch_size):
                    batch_ip_ids = ip_ids[i:i+delete_batch_size]
                    deleted, _ = IPObject.authors.through.objects.filter(
                        ipobject_id__in=batch_ip_ids
                    ).delete()
                    deleted_total += deleted
                    pbar.update(len(batch_ip_ids))
            
            self.stdout.write(f"           Удалено старых связей: {deleted_total}")
            
            # Создаем новые связи пачками
            create_batch_size = 2000
            created_count = 0
            
            with tqdm(total=len(through_objs), desc="           Добавление", unit=" связь") as pbar:
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.authors.through.objects.bulk_create(
                        batch, 
                        batch_size=create_batch_size,
                        ignore_conflicts=True
                    )
                    created_count += len(batch)
                    pbar.update(len(batch))
            
            self.stdout.write(f"           Создано новых связей: {created_count}")
        
        # ШАГ 6: Очистка памяти
        self.stdout.write("        Шаг 6/6: Очистка памяти...")
        gc.collect()
        
        self.stdout.write(f"        ✅ Обработка авторов завершена")

    def _process_holders_optimized(self, existing_objects, holders_data):
        """Оптимизированная обработка правообладателей с сохранением Natasha"""
        self.stdout.write(f"     ⚡ Обработка правообладателей (оптимизировано)...")
        
        # ШАГ 1: Сбор уникальных правообладателей
        self.stdout.write("        Шаг 1/7: Сбор уникальных правообладателей...")
        
        # Используем словари для маппинга
        holder_to_ips = {}
        all_holders_set = set()
        
        with tqdm(total=len(holders_data), desc="           Группировка", unit=" зап") as pbar:
            for reg_num, holder in holders_data:
                ip_object = existing_objects.get(reg_num)
                if ip_object:
                    all_holders_set.add(holder)
                    if holder not in holder_to_ips:
                        holder_to_ips[holder] = set()
                    holder_to_ips[holder].add(ip_object.pk)
                pbar.update(1)
        
        all_holders = list(all_holders_set)
        self.stdout.write(f"        Уникальных правообладателей: {len(all_holders)}")
        
        # ШАГ 2: Определение типов с использованием Natasha (с кэшированием)
        self.stdout.write("        Шаг 2/7: Определение типов...")
        person_holders = []
        org_holders = []
        
        with tqdm(total=len(all_holders), desc="           Анализ", unit=" об") as pbar:
            for holder in all_holders:
                # Используем type_detector с Natasha
                if self.type_detector.detect_type(holder) == 'person':
                    person_holders.append(holder)
                else:
                    org_holders.append(holder)
                pbar.update(1)
                
                # Периодическая очистка
                if pbar.n % 1000 == 0:
                    gc.collect()
        
        self.stdout.write(f"        Люди: {len(person_holders)}, Организации: {len(org_holders)}")
        
        # ШАГ 3: Обработка организаций (пачками)
        self.stdout.write("        Шаг 3/7: Обработка организаций...")
        org_map = self._batch_process_organizations_with_progress(org_holders)
        
        # ШАГ 4: Обработка людей (пачками)
        self.stdout.write("        Шаг 4/7: Обработка людей...")
        person_map = self._batch_process_persons_with_progress(person_holders)
        
        # ШАГ 5: Подготовка связей
        self.stdout.write("        Шаг 5/7: Подготовка связей...")
        
        org_relations = []
        person_relations = []
        
        with tqdm(total=len(all_holders), desc="           Сбор связей", unit=" обл") as pbar:
            for holder in all_holders:
                ip_ids = holder_to_ips.get(holder, set())
                if holder in org_map:
                    org_id = org_map[holder].pk
                    for ip_id in ip_ids:
                        org_relations.append((ip_id, org_id))
                elif holder in person_map:
                    person_id = person_map[holder].pk
                    for ip_id in ip_ids:
                        person_relations.append((ip_id, person_id))
                pbar.update(1)
                
                # Периодическая очистка
                if len(org_relations) + len(person_relations) > 100000:
                    gc.collect()
        
        self.stdout.write(f"        Уникальных связей с организациями: {len(org_relations)}")
        self.stdout.write(f"        Уникальных связей с людьми: {len(person_relations)}")
        
        # ШАГ 6: Создание связей с организациями
        if org_relations:
            self.stdout.write("        Шаг 6/7: Создание связей с организациями...")
            self._create_org_relations_with_progress(org_relations)
        
        # ШАГ 7: Создание связей с людьми
        if person_relations:
            self.stdout.write("        Шаг 7/7: Создание связей с людьми...")
            self._create_person_relations_with_progress(person_relations)
        
        # Очистка памяти
        gc.collect()
        
        self.stdout.write(f"        ✅ Обработка правообладателей завершена")

    def _batch_process_organizations_with_progress(self, org_holders):
        """Пакетная обработка организаций с прогресс-баром"""
        if not org_holders:
            return {}
        
        org_map = {}
        CHUNK_SIZE = 1000
        total_orgs = len(org_holders)
        
        self.stdout.write(f"        Обработка {total_orgs} организаций частями по {CHUNK_SIZE}...")
        
        for chunk_start in range(0, total_orgs, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, total_orgs)
            chunk_holders = org_holders[chunk_start:chunk_end]
            
            # Поиск существующих в этой части
            existing_orgs = {}
            for org in Organization.objects.filter(name__in=chunk_holders).only('id', 'name'):
                existing_orgs[org.name] = org
                self.organization_cache[org.name] = org
            
            # Создание новых в этой части
            orgs_to_create = []
            for holder in chunk_holders:
                if holder not in existing_orgs and holder not in self.organization_cache:
                    max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
                    new_id = max_id + len(orgs_to_create) + 1
                    
                    base_slug = slugify(holder[:50])
                    if not base_slug:
                        base_slug = 'organization'
                    
                    unique_slug = base_slug
                    counter = 1
                    while Organization.objects.filter(slug=unique_slug).exists() or any(o.slug == unique_slug for o in orgs_to_create):
                        unique_slug = f"{base_slug}-{counter}"
                        counter += 1
                    
                    org = Organization(
                        organization_id=new_id,
                        name=holder,
                        full_name=holder,
                        short_name=holder[:500] if len(holder) > 500 else holder,
                        slug=unique_slug,
                        register_opk=False,
                        strategic=False,
                    )
                    orgs_to_create.append(org)
                    self.organization_cache[holder] = org
            
            # Создаем в БД
            if orgs_to_create:
                batch_size = 500
                for i in range(0, len(orgs_to_create), batch_size):
                    batch = orgs_to_create[i:i+batch_size]
                    Organization.objects.bulk_create(batch, batch_size=batch_size)
            
            # Обновляем маппинг
            for holder in chunk_holders:
                if holder in existing_orgs:
                    org_map[holder] = existing_orgs[holder]
                elif holder in self.organization_cache:
                    org_map[holder] = self.organization_cache[holder]
            
            # Прогресс
            progress = (chunk_end / total_orgs) * 100
            self.stdout.write(f"           Прогресс: {progress:.1f}%")
            
            # Очистка памяти
            del existing_orgs
            del orgs_to_create
            gc.collect()
        
        return org_map

    def _batch_process_persons_with_progress(self, person_holders):
        """Пакетная обработка людей с прогресс-баром"""
        if not person_holders:
            return {}
        
        person_map = {}
        CHUNK_SIZE = 500
        total_people = len(person_holders)
        
        self.stdout.write(f"        Обработка {total_people} людей частями по {CHUNK_SIZE}...")
        
        for chunk_start in range(0, total_people, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, total_people)
            chunk_holders = person_holders[chunk_start:chunk_end]
            
            # Поиск существующих
            existing_people = {}
            for holder in chunk_holders:
                parts = holder.split()
                if len(parts) >= 2:
                    last_name = parts[0]
                    first_name = parts[1]
                    middle_name = parts[2] if len(parts) > 2 else ''
                    
                    persons = Person.objects.filter(
                        last_name=last_name,
                        first_name=first_name
                    )
                    if middle_name:
                        persons = persons.filter(middle_name=middle_name)
                    
                    person = persons.first()
                    if person:
                        existing_people[holder] = person
                        self.person_cache[holder] = person
            
            # Создание новых
            people_to_create = []
            for holder in chunk_holders:
                if holder not in existing_people and holder not in self.person_cache:
                    parts = holder.split()
                    if len(parts) >= 2:
                        last_name = parts[0]
                        first_name = parts[1]
                        middle_name = parts[2] if len(parts) > 2 else ''
                        
                        name_parts = [last_name, first_name]
                        if middle_name:
                            name_parts.append(middle_name)
                        
                        base_slug = slugify(' '.join(name_parts))
                        if not base_slug:
                            base_slug = 'person'
                        
                        unique_slug = base_slug
                        counter = 1
                        while Person.objects.filter(slug=unique_slug).exists() or any(p.slug == unique_slug for p in people_to_create):
                            unique_slug = f"{base_slug}-{counter}"
                            counter += 1
                        
                        max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
                        new_id = max_id + len(people_to_create) + 1
                        
                        person = Person(
                            ceo_id=new_id,
                            ceo=holder,
                            last_name=last_name,
                            first_name=first_name,
                            middle_name=middle_name or '',
                            slug=unique_slug
                        )
                        people_to_create.append(person)
                        self.person_cache[holder] = person
            
            # Создаем в БД
            if people_to_create:
                batch_size = 500
                for i in range(0, len(people_to_create), batch_size):
                    batch = people_to_create[i:i+batch_size]
                    Person.objects.bulk_create(batch, batch_size=batch_size)
            
            # Обновляем маппинг
            for holder in chunk_holders:
                if holder in existing_people:
                    person_map[holder] = existing_people[holder]
                elif holder in self.person_cache:
                    person_map[holder] = self.person_cache[holder]
            
            # Прогресс
            progress = (chunk_end / total_people) * 100
            self.stdout.write(f"           Прогресс: {progress:.1f}%")
            
            # Очистка памяти
            del existing_people
            del people_to_create
            gc.collect()
        
        return person_map

    def _create_org_relations_with_progress(self, org_relations):
        """Создание связей с организациями с прогресс-баром"""
        if not org_relations:
            return
        
        # Получаем уникальные IP ID
        ip_ids = list(set(ip_id for ip_id, _ in org_relations))
        
        # Удаляем старые связи с прогресс-баром
        delete_batch_size = 500
        deleted_total = 0
        
        with tqdm(total=len(ip_ids), desc="           Удаление старых связей", unit=" ip") as pbar:
            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.owner_organizations.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted
                pbar.update(len(batch_ip_ids))
        
        self.stdout.write(f"           Удалено старых связей: {deleted_total}")
        
        # Создаем новые связи
        through_objs = [
            IPObject.owner_organizations.through(
                ipobject_id=ip_id,
                organization_id=org_id
            )
            for ip_id, org_id in org_relations
        ]
        
        create_batch_size = 2000
        with tqdm(total=len(through_objs), desc="           Добавление новых связей", unit=" св") as pbar:
            for i in range(0, len(through_objs), create_batch_size):
                batch = through_objs[i:i+create_batch_size]
                IPObject.owner_organizations.through.objects.bulk_create(
                    batch, 
                    batch_size=create_batch_size,
                    ignore_conflicts=True
                )
                pbar.update(len(batch))

    def _create_person_relations_with_progress(self, person_relations):
        """Создание связей с людьми с прогресс-баром"""
        if not person_relations:
            return
        
        # Получаем уникальные IP ID
        ip_ids = list(set(ip_id for ip_id, _ in person_relations))
        
        # Удаляем старые связи с прогресс-баром
        delete_batch_size = 500
        deleted_total = 0
        
        with tqdm(total=len(ip_ids), desc="           Удаление старых связей", unit=" ip") as pbar:
            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.owner_persons.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted
                pbar.update(len(batch_ip_ids))
        
        self.stdout.write(f"           Удалено старых связей: {deleted_total}")
        
        # Создаем новые связи
        through_objs = [
            IPObject.owner_persons.through(
                ipobject_id=ip_id,
                person_id=person_id
            )
            for ip_id, person_id in person_relations
        ]
        
        create_batch_size = 2000
        with tqdm(total=len(through_objs), desc="           Добавление новых связей", unit=" св") as pbar:
            for i in range(0, len(through_objs), create_batch_size):
                batch = through_objs[i:i+create_batch_size]
                IPObject.owner_persons.through.objects.bulk_create(
                    batch, 
                    batch_size=create_batch_size,
                    ignore_conflicts=True
                )
                pbar.update(len(batch))