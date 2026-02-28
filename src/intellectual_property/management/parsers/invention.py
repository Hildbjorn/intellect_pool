"""
Парсер для изобретений с использованием единого DataFrame для связей
"""

import logging
import gc
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

import pandas as pd
from django.db import models, transaction
from django.utils.text import slugify

from intellectual_property.models import IPObject, IPType, Person
from core.models import Organization

from .base import BaseFIPSParser
from ..utils.progress import ProgressManager, batch_iterator

logger = logging.getLogger(__name__)


class InventionParser(BaseFIPSParser):
    """
    Парсер для изобретений с оптимизированной обработкой связей
    Использует единый DataFrame для всех связей (авторы + правообладатели)
    """

    def get_ip_type(self):
        """Возвращает тип РИД 'invention'"""
        return IPType.objects.filter(slug='invention').first()

    def get_required_columns(self):
        """Возвращает список обязательных колонок для CSV"""
        return ['registration number', 'invention name']

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
            ('claims', obj.claims, new_data['claims']),
            ('creation_year', obj.creation_year, new_data['creation_year']),
        ]

        for field_name, old_val, new_val in fields_to_check:
            if old_val != new_val:
                return True
        return False

    def parse_dataframe(self, df, catalogue):
        """
        Основной метод парсинга DataFrame
        """
        self.progress.step("Начинаем парсинг изобретений")

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
            self.progress.error("Тип РИД 'invention' не найден в БД")
            stats['errors'] += 1
            return stats

        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # =====================================================================
        # ШАГ 1: Сбор регистрационных номеров
        # =====================================================================
        self.progress.step("Чтение CSV и сбор регистрационных номеров")
        
        reg_num_to_row = {}
        skipped_empty = 0
        
        for idx, row in df.iterrows():
            reg_num = self.clean_string(row.get('registration number'))
            if reg_num:
                reg_num_to_row[reg_num] = row
            else:
                skipped_empty += 1

        self.progress.step(f"Всего записей в CSV: {len(reg_num_to_row)} (пропущено пустых: {skipped_empty})")

        # =====================================================================
        # ШАГ 2: Загрузка существующих записей из БД
        # =====================================================================
        self.progress.step("Загрузка существующих записей из БД")
        
        existing_objects = {}
        batch_size = 500
        reg_numbers = list(reg_num_to_row.keys())
        
        # Прогресс-бар с редким обновлением
        with self.progress.task("Загрузка пачками", 
                               total=len(reg_numbers), 
                               unit="зап") as pbar:
            
            for i in range(0, len(reg_numbers), batch_size):
                batch_numbers = reg_numbers[i:i+batch_size]
                
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_numbers,
                    ip_type=ip_type
                ).select_related('ip_type'):
                    existing_objects[obj.registration_number] = obj
                
                pbar.update(len(batch_numbers))

        self.progress.step(f"Найдено в БД: {len(existing_objects)}")

        # =====================================================================
        # ШАГ 3: Подготовка данных для IPObject
        # =====================================================================
        self.progress.step("Подготовка данных IPObject")
        
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        relations_data = []
        
        # Прогресс-бар с редким обновлением
        with self.progress.task("Подготовка данных IPObject", 
                               total=len(reg_num_to_row), 
                               unit="зап") as pbar:

            for reg_num, row in reg_num_to_row.items():
                try:
                    if not self.command.force and upload_date and reg_num in existing_objects:
                        existing = existing_objects[reg_num]
                        if existing.updated_at and existing.updated_at.date() >= upload_date:
                            skipped_by_date.append(reg_num)
                            pbar.update(1)
                            # Обновляем статистику прямо в прогресс-баре
                            pbar.set_postfix(
                                новые=len(to_create),
                                обнов=len(to_update),
                                без_изм=unchanged_count,
                                пропущ=len(skipped_by_date),
                                ошибок=len(error_reg_numbers)
                            )
                            continue

                    name = self.clean_string(row.get('invention name'))
                    if name:
                        name = self.rid_formatter.format(name)
                    else:
                        name = f"Изобретение №{reg_num}"

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
                        'ip_type_id': ip_type.id,
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
                        self.progress.error(f"Ошибка подготовки записи {reg_num}: {e}")
                    elif len(error_reg_numbers) == 10:
                        self.progress.warning("... и далее ошибки подавляются")
                    
                    logger.error(f"Error preparing invention {reg_num}: {e}", exc_info=True)

                pbar.update(1)
                
                # Выводим статистику редко (каждые 50000 записей)
                if pbar.n % 50000 == 0:
                    self.progress.step(f"Обработано {pbar.n} записей: новых={len(to_create)}, "
                                      f"обнов={len(to_update)}, без изм={unchanged_count}, "
                                      f"пропущ={len(skipped_by_date)}, ошибок={len(error_reg_numbers)}")

        self.progress.step(f"Итого: новых={len(to_create)}, обновление={len(to_update)}, "
                          f"без изменений={unchanged_count}, ошибок={len(error_reg_numbers)}")

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        # =====================================================================
        # ШАГ 4: Создание/обновление IPObject
        # =====================================================================
        if to_create and not self.command.dry_run:
            self.progress.step(f"Создание {len(to_create)} новых записей")
            with self.progress.task("Создание", total=len(to_create), unit="зап") as pbar:
                stats['created'] = self._bulk_create_objects(to_create, pbar)

        if to_update and not self.command.dry_run:
            self.progress.step(f"Обновление {len(to_update)} записей")
            with self.progress.task("Обновление", total=len(to_update), unit="зап") as pbar:
                stats['updated'] = self._bulk_update_objects(to_update, existing_objects, pbar)

        # =====================================================================
        # ШАГ 5: Получаем актуальный маппинг reg_number -> ip_id
        # =====================================================================
        self.progress.step("Построение маппинга регистрационных номеров")
        
        all_reg_numbers = list(set(
            list(existing_objects.keys()) + 
            [data['registration_number'] for data in to_create]
        ))
        
        reg_to_ip = {}
        with self.progress.task("Загрузка ID объектов", total=len(all_reg_numbers), unit="зап") as pbar:
            batch_size = 1000
            for i in range(0, len(all_reg_numbers), batch_size):
                batch_nums = all_reg_numbers[i:i+batch_size]
                for obj in IPObject.objects.filter(
                    registration_number__in=batch_nums,
                    ip_type=ip_type
                ).only('id', 'registration_number'):
                    reg_to_ip[obj.registration_number] = obj.id
                pbar.update(len(batch_nums))

        self.progress.step(f"Загружено ID для {len(reg_to_ip)} объектов")

        # =====================================================================
        # ШАГ 6: Обработка связей через единый DataFrame
        # =====================================================================
        if relations_data and not self.command.dry_run:
            self.progress.step("Обработка связей")
            self._process_relations_dataframe(relations_data, reg_to_ip)

        gc.collect()

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        self.progress.success("Парсинг изобретений завершен")
        self.progress.step(f"Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                          f"Без изменений: {stats['unchanged']}")
        self.progress.step(f"Пропущено: {stats['skipped']} (из них по дате: {stats['skipped_by_date']})")
        self.progress.step(f"Ошибок: {stats['errors']}")

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
            
            if created_count % 50000 == 0:
                self.progress.step(f"Создано {created_count} записей")

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
            
            if updated_count % 50000 == 0:
                self.progress.step(f"Обновлено {updated_count} записей")

        return updated_count

    def _process_relations_dataframe(self, relations_data: List[Dict], reg_to_ip: Dict):
        """Обработка всех связей через единый DataFrame"""
        if not relations_data:
            self.progress.step("Нет данных для обработки связей")
            return

        self.progress.step("Создание DataFrame связей")
        df_relations = pd.DataFrame(relations_data)
        
        self.progress.step(f"Всего записей связей: {len(df_relations)}")
        self.progress.step(f"Уникальных регистрационных номеров: {df_relations['reg_number'].nunique()}")

        self.progress.step("Добавление ID объектов")
        df_relations['ip_id'] = df_relations['reg_number'].map(reg_to_ip)

        missing_ip = df_relations['ip_id'].isna().sum()
        if missing_ip > 0:
            self.progress.warning(f"Пропущено {missing_ip} связей с отсутствующими ID объектов")
            df_relations = df_relations.dropna(subset=['ip_id']).copy()
        
        df_relations['ip_id'] = df_relations['ip_id'].astype(int)

        # =====================================================================
        # ШАГ 6.1: Определение типов для правообладателей
        # =====================================================================
        self.progress.step("Определение типов сущностей через Natasha")
        
        unique_entities = df_relations[['entity_name', 'entity_type']].drop_duplicates()
        holders_to_check = unique_entities[unique_entities['entity_type'].isna()]['entity_name'].tolist()

        if holders_to_check:
            self.progress.step(f"Определение типов для {len(holders_to_check)} правообладателей")
            entity_type_map = self.type_detector.detect_type_batch(holders_to_check)

            mask = df_relations['entity_type'].isna()
            df_relations.loc[mask, 'entity_type'] = \
                df_relations.loc[mask, 'entity_name'].map(entity_type_map)

        type_stats = df_relations['entity_type'].value_counts().to_dict()
        self.progress.step(f"Распределение типов: люди={type_stats.get('person', 0)}, "
                          f"организации={type_stats.get('organization', 0)}")

        # =====================================================================
        # ШАГ 6.2: Группировка по сущностям
        # =====================================================================
        unique_entities = df_relations[['entity_name', 'entity_type']].drop_duplicates()
        
        persons_df = unique_entities[unique_entities['entity_type'] == 'person']
        orgs_df = unique_entities[unique_entities['entity_type'] == 'organization']

        person_map = {}
        if not persons_df.empty:
            self.progress.step(f"Обработка {len(persons_df)} уникальных людей")
            with self.progress.task("Создание/поиск людей", 
                                   total=len(persons_df), 
                                   unit="чел") as pbar:
                person_map = self._create_persons_from_dataframe(persons_df, pbar)

        org_map = {}
        if not orgs_df.empty:
            self.progress.step(f"Обработка {len(orgs_df)} уникальных организаций")
            with self.progress.task("Создание/поиск организаций", 
                                   total=len(orgs_df), 
                                   unit="орг") as pbar:
                org_map = self._create_organizations_from_dataframe(orgs_df, pbar)

        # =====================================================================
        # ШАГ 6.3: Подготовка связей
        # =====================================================================
        self.progress.step("Подготовка связей для вставки в БД")
        
        authors_df = df_relations[df_relations['relation_type'] == 'author'].copy()
        holders_df = df_relations[df_relations['relation_type'] == 'holder'].copy()

        author_relations = []
        if not authors_df.empty:
            # ИСПРАВЛЕНО: используем ceo_id вместо id
            authors_df['person_id'] = authors_df['entity_name'].map(
                {name: p.ceo_id for name, p in person_map.items()}
            )
            authors_unique = authors_df[['ip_id', 'person_id']].drop_duplicates()
            author_relations = [(row['ip_id'], row['person_id']) 
                               for _, row in authors_unique.iterrows()]
            self.progress.step(f"Подготовлено {len(author_relations)} уникальных связей авторов")

        holder_person_relations = []
        holder_org_relations = []
        
        if not holders_df.empty:
            holders_persons = holders_df[holders_df['entity_type'] == 'person'].copy()
            if not holders_persons.empty:
                # ИСПРАВЛЕНО: используем ceo_id вместо id
                holders_persons['person_id'] = holders_persons['entity_name'].map(
                    {name: p.ceo_id for name, p in person_map.items()}
                )
                holders_persons_unique = holders_persons[['ip_id', 'person_id']].drop_duplicates()
                holder_person_relations = [(row['ip_id'], row['person_id']) 
                                          for _, row in holders_persons_unique.iterrows()]
                self.progress.step(f"Подготовлено {len(holder_person_relations)} связей правообладателей-людей")

            holders_orgs = holders_df[holders_df['entity_type'] == 'organization'].copy()
            if not holders_orgs.empty:
                # ИСПРАВЛЕНО: используем organization_id вместо id
                holders_orgs['org_id'] = holders_orgs['entity_name'].map(
                    {name: o.organization_id for name, o in org_map.items()}
                )
                holders_orgs_unique = holders_orgs[['ip_id', 'org_id']].drop_duplicates()
                holder_org_relations = [(row['ip_id'], row['org_id']) 
                                       for _, row in holders_orgs_unique.iterrows()]
                self.progress.step(f"Подготовлено {len(holder_org_relations)} связей правообладателей-организаций")

        # =====================================================================
        # ШАГ 6.4: Массовое создание связей
        # =====================================================================
        if author_relations:
            self.progress.step("Создание связей авторов")
            ip_ids = list(set(ip_id for ip_id, _ in author_relations))
            with self.progress.task("Удаление старых связей авторов", 
                                   total=len(ip_ids), 
                                   unit="ip") as pbar:
                self._delete_author_relations(ip_ids, pbar)
            
            with self.progress.task("Создание новых связей авторов", 
                                   total=len(author_relations), 
                                   unit="св") as pbar:
                self._create_author_relations(author_relations, pbar)

        if holder_person_relations:
            self.progress.step("Создание связей правообладателей (люди)")
            ip_ids = list(set(ip_id for ip_id, _ in holder_person_relations))
            with self.progress.task("Удаление старых связей", 
                                   total=len(ip_ids), 
                                   unit="ip") as pbar:
                self._delete_holder_person_relations(ip_ids, pbar)
            
            with self.progress.task("Создание новых связей", 
                                   total=len(holder_person_relations), 
                                   unit="св") as pbar:
                self._create_holder_person_relations(holder_person_relations, pbar)

        if holder_org_relations:
            self.progress.step("Создание связей правообладателей (организации)")
            ip_ids = list(set(ip_id for ip_id, _ in holder_org_relations))
            with self.progress.task("Удаление старых связей", 
                                   total=len(ip_ids), 
                                   unit="ip") as pbar:
                self._delete_holder_org_relations(ip_ids, pbar)
            
            with self.progress.task("Создание новых связей", 
                                   total=len(holder_org_relations), 
                                   unit="св") as pbar:
                self._create_holder_org_relations(holder_org_relations, pbar)

        self.progress.success("Обработка всех связей завершена")

    def _create_persons_from_dataframe(self, persons_df: pd.DataFrame, pbar) -> Dict:
        """Создание людей из DataFrame"""
        person_map = {}
        all_names = persons_df['entity_name'].tolist()
        
        # Разбиваем имена для поиска
        name_parts = {}
        for name in all_names:
            parts = name.split()
            if len(parts) >= 2:
                last = parts[0]
                first = parts[1]
                middle = parts[2] if len(parts) > 2 else ''
                name_parts[name] = (last, first, middle)

        # Строим запрос для поиска существующих
        if name_parts:
            query = models.Q()
            name_to_query_key = {}  # Для обратного маппинга
            
            for name, (last, first, middle) in name_parts.items():
                if middle:
                    q = models.Q(last_name=last, first_name=first, middle_name=middle)
                else:
                    q = models.Q(last_name=last, first_name=first) & \
                        (models.Q(middle_name='') | models.Q(middle_name__isnull=True))
                query |= q
                # Сохраняем соответствие для быстрого поиска
                name_to_query_key[name] = (last, first, middle)
            
            # Ищем всех существующих людей одним запросом
            # ИСПРАВЛЕНО: используем ceo_id вместо id
            for person in Person.objects.filter(query).only('ceo_id', 'last_name', 'first_name', 'middle_name', 'ceo'):
                # Проверяем каждое имя
                for name, (last, first, middle) in name_parts.items():
                    if (person.last_name == last and 
                        person.first_name == first and 
                        (not middle or person.middle_name == middle)):
                        person_map[name] = person
                        self.person_cache[name] = person
                        break

        # Определяем новых людей
        new_names = [name for name in all_names if name not in person_map]
        
        if new_names:
            max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
            existing_slugs = set(Person.objects.values_list('slug', flat=True)[:100000])
            
            people_to_create = []
            
            for name in new_names:
                parts = name.split()
                if len(parts) >= 2:
                    last_name = parts[0]
                    first_name = parts[1]
                    middle_name = parts[2] if len(parts) > 2 else ''
                    
                    name_parts_list = [last_name, first_name]
                    if middle_name:
                        name_parts_list.append(middle_name)
                    
                    base_slug = slugify(' '.join(name_parts_list)) or 'person'
                    unique_slug = base_slug
                    counter = 1
                    while unique_slug in existing_slugs:
                        unique_slug = f"{base_slug}-{counter}"
                        counter += 1
                    existing_slugs.add(unique_slug)
                    
                    person = Person(
                        ceo_id=max_id + len(people_to_create) + 1,
                        ceo=name,
                        last_name=last_name,
                        first_name=first_name,
                        middle_name=middle_name or '',
                        slug=unique_slug
                    )
                    people_to_create.append(person)
                    person_map[name] = person
                    self.person_cache[name] = person
                
                pbar.update(1)
                
                if pbar.n % 50000 == 0:
                    self.progress.step(f"Обработано {pbar.n} людей")
            
            if people_to_create:
                for batch in batch_iterator(people_to_create, 500):
                    Person.objects.bulk_create(batch, batch_size=500)

        return person_map

    def _create_organizations_from_dataframe(self, orgs_df: pd.DataFrame, pbar) -> Dict:
        """Создание организаций из DataFrame"""
        org_map = {}
        all_names = orgs_df['entity_name'].tolist()
        
        # Поиск существующих организаций
        existing_orgs = {}
        for org in Organization.objects.filter(name__in=all_names).only('organization_id', 'name'):
            existing_orgs[org.name] = org
            self.organization_cache[org.name] = org

        new_names = [name for name in all_names if name not in existing_orgs]
        
        if new_names:
            max_id = Organization.objects.aggregate(models.Max('organization_id'))['organization_id__max'] or 0
            existing_slugs = set(Organization.objects.values_list('slug', flat=True)[:50000])
            
            orgs_to_create = []
            
            for name in new_names:
                base_slug = slugify(name[:50]) or 'organization'
                unique_slug = base_slug
                counter = 1
                while unique_slug in existing_slugs:
                    unique_slug = f"{base_slug}-{counter}"
                    counter += 1
                existing_slugs.add(unique_slug)
                
                org = Organization(
                    organization_id=max_id + len(orgs_to_create) + 1,
                    name=name,
                    full_name=name,
                    short_name=name[:500] if len(name) > 500 else name,
                    slug=unique_slug,
                    register_opk=False,
                    strategic=False,
                )
                orgs_to_create.append(org)
                
                pbar.update(1)
                
                if pbar.n % 10000 == 0:
                    self.progress.step(f"Обработано {pbar.n} организаций")
            
            if orgs_to_create:
                for batch in batch_iterator(orgs_to_create, 500):
                    Organization.objects.bulk_create(batch, batch_size=500)

        for name in all_names:
            if name in existing_orgs:
                org_map[name] = existing_orgs[name]
            elif name in self.organization_cache:
                org_map[name] = self.organization_cache[name]

        return org_map

    def _delete_author_relations(self, ip_ids: List[int], pbar):
        """Удаление связей авторов"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.authors.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    def _delete_holder_person_relations(self, ip_ids: List[int], pbar):
        """Удаление связей правообладателей-людей"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.owner_persons.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    def _delete_holder_org_relations(self, ip_ids: List[int], pbar):
        """Удаление связей правообладателей-организаций"""
        delete_batch_size = 500
        for i in range(0, len(ip_ids), delete_batch_size):
            batch_ids = ip_ids[i:i+delete_batch_size]
            IPObject.owner_organizations.through.objects.filter(
                ipobject_id__in=batch_ids
            ).delete()
            pbar.update(len(batch_ids))

    def _create_author_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей авторов"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.authors.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in batch
            ]
            IPObject.authors.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))

    def _create_holder_person_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей правообладателей-людей"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.owner_persons.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in batch
            ]
            IPObject.owner_persons.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))

    def _create_holder_org_relations(self, relations: List[Tuple[int, int]], pbar):
        """Создание связей правообладателей-организаций"""
        create_batch_size = 2000
        for batch in batch_iterator(relations, create_batch_size):
            through_objs = [
                IPObject.owner_organizations.through(
                    ipobject_id=ip_id,
                    organization_id=org_id
                )
                for ip_id, org_id in batch
            ]
            IPObject.owner_organizations.through.objects.bulk_create(
                through_objs, batch_size=2000, ignore_conflicts=True
            )
            pbar.update(len(batch))