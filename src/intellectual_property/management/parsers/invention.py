"""
Парсер для изобретений с пакетной обработкой
"""

import logging
from collections import defaultdict

from django.db import models
from django.utils.text import slugify
from tqdm import tqdm
import pandas as pd

# Добавляем недостающие импорты
from intellectual_property.models import IPObject, IPType, Person
from core.models import Organization  # <-- Добавлен этот импорт
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

        # Получаем дату загрузки каталога
        upload_date = catalogue.upload_date.date() if catalogue.upload_date else None

        # ШАГ 1: Собираем все регистрационные номера
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

        # ШАГ 2: Загружаем существующие записи ПАЧКАМИ
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

                if (i // batch_size) % 10 == 0:
                    pbar.set_postfix({"найдено": len(existing_objects)})

        self.stdout.write(f"  📊 Найдено в БД: {len(existing_objects)}")

        # ШАГ 3: Подготавливаем данные для пакетной обработки
        self.stdout.write("  🔄 Подготовка данных...")
        to_create = []
        to_update = []
        skipped_by_date = []
        unchanged_count = 0
        error_reg_numbers = []

        authors_cache = defaultdict(list)
        holders_cache = defaultdict(list)

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

                    # Подготовка данных
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
                        # Проверяем, изменились ли данные
                        existing = existing_objects[reg_num]
                        if self._has_data_changed(existing, obj_data):
                            to_update.append(obj_data)
                        else:
                            unchanged_count += 1
                    else:
                        to_create.append(obj_data)

                    # Сохраняем авторов и правообладателей
                    authors_str = row.get('authors')
                    if not pd.isna(authors_str) and authors_str:
                        authors_cache[reg_num] = self.parse_authors(authors_str)

                    holders_str = row.get('patent holders')
                    if not pd.isna(holders_str) and holders_str:
                        holders_cache[reg_num] = self.parse_patent_holders(holders_str)

                except Exception as e:
                    error_reg_numbers.append(reg_num)
                    self.stdout.write(self.style.ERROR(f"\n  ❌ Ошибка подготовки записи {reg_num}: {e}"))
                    logger.error(f"Error preparing invention {reg_num}: {e}", exc_info=True)

                pbar.update(1)
                if pbar.n % 1000 == 0:
                    pbar.set_postfix({
                        "новые": len(to_create),
                        "обнов": len(to_update),
                        "без изм": unchanged_count,
                        "пропущ": len(skipped_by_date)
                    })

        stats['skipped_by_date'] = len(skipped_by_date)
        stats['skipped'] += len(skipped_by_date)
        stats['errors'] = len(error_reg_numbers)
        stats['unchanged'] = unchanged_count

        self.stdout.write(f"     Итого: новых={len(to_create)}, обновление={len(to_update)}, без изменений={unchanged_count}")

        # ШАГ 4: Пакетное создание новых записей
        if to_create and not self.command.dry_run:
            self.stdout.write(f"  📦 Создание {len(to_create)} записей...")
            create_objects = [IPObject(**data) for data in to_create]

            batch_size = 1000
            created_count = 0

            with tqdm(total=len(create_objects), desc="     Создание", unit=" зап") as pbar:
                for i in range(0, len(create_objects), batch_size):
                    batch = create_objects[i:i+batch_size]
                    IPObject.objects.bulk_create(batch, batch_size=batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))
                    pbar.set_postfix({"создано": created_count})

            stats['created'] = created_count

            # Обновляем кэш новыми объектами
            self.stdout.write("     Обновление кэша...")

            with tqdm(total=len(to_create), desc="     Обновление кэша", unit=" зап") as pbar:
                for i in range(0, len(to_create), batch_size):
                    batch_data = to_create[i:i+batch_size]
                    batch_nums = [d['registration_number'] for d in batch_data]

                    for obj in IPObject.objects.filter(
                        registration_number__in=batch_nums,
                        ip_type=ip_type
                    ):
                        existing_objects[obj.registration_number] = obj

                    pbar.update(len(batch_data))

        # ШАГ 5: Пакетное обновление существующих записей
        if to_update and not self.command.dry_run:
            self.stdout.write(f"  📦 Обновление {len(to_update)} записей...")
            updated_count = 0

            with tqdm(total=len(to_update), desc="     Обновление", unit=" зап") as pbar:
                for data in to_update:
                    obj = existing_objects[data['registration_number']]
                    update_fields = []

                    if obj.name != data['name']:
                        obj.name = data['name']
                        update_fields.append('name')

                    if obj.application_date != data['application_date']:
                        obj.application_date = data['application_date']
                        update_fields.append('application_date')

                    if obj.registration_date != data['registration_date']:
                        obj.registration_date = data['registration_date']
                        update_fields.append('registration_date')

                    if obj.patent_starting_date != data['patent_starting_date']:
                        obj.patent_starting_date = data['patent_starting_date']
                        update_fields.append('patent_starting_date')

                    if obj.expiration_date != data['expiration_date']:
                        obj.expiration_date = data['expiration_date']
                        update_fields.append('expiration_date')

                    if obj.actual != data['actual']:
                        obj.actual = data['actual']
                        update_fields.append('actual')

                    if obj.publication_url != data['publication_url']:
                        obj.publication_url = data['publication_url']
                        update_fields.append('publication_url')

                    if obj.abstract != data['abstract']:
                        obj.abstract = data['abstract']
                        update_fields.append('abstract')

                    if obj.claims != data['claims']:
                        obj.claims = data['claims']
                        update_fields.append('claims')

                    if obj.creation_year != data['creation_year']:
                        obj.creation_year = data['creation_year']
                        update_fields.append('creation_year')

                    if update_fields:
                        obj.save(update_fields=update_fields)
                        updated_count += 1

                    pbar.update(1)
                    if pbar.n % 100 == 0:
                        pbar.set_postfix({"обновлено": updated_count})

            stats['updated'] = updated_count
            self.stdout.write(f"     Реально обновлено: {updated_count} из {len(to_update)}")

        # ШАГ 6: Пакетная обработка авторов
        if authors_cache and not self.command.dry_run:
            self.stdout.write(f"  📦 Обработка авторов ({len(authors_cache)} записей)...")
            self._process_authors_batch_with_progress(existing_objects, authors_cache)

        # ШАГ 7: Пакетная обработка патентообладателей
        if holders_cache and not self.command.dry_run:
            self.stdout.write(f"  📦 Обработка патентообладателей ({len(holders_cache)} записей)...")
            self._process_holders_batch_with_progress(existing_objects, holders_cache)

        stats['processed'] = len(df) - stats['skipped'] - stats['errors']

        self.stdout.write(self.style.SUCCESS(f"  ✅ Парсинг изобретений завершен"))
        self.stdout.write(f"     Создано: {stats['created']}, Обновлено: {stats['updated']}, "
                         f"Без изменений: {stats['unchanged']}, "
                         f"Пропущено всего: {stats['skipped']} (из них по дате: {stats['skipped_by_date']}), "
                         f"Ошибок: {stats['errors']}")

        return stats

    def _process_authors_batch_with_progress(self, existing_objects, authors_cache):
        """Обработка авторов с прогресс-баром и разбивкой на пачки"""
        self.stdout.write(f"     ⚡ Обработка авторов...")

        # ШАГ 1: Сбор уникальных авторов
        self.stdout.write("        Шаг 1/6: Сбор уникальных авторов...")
        author_to_key = {}
        total_relations = 0

        for reg_num, authors_data in authors_cache.items():
            ip_object = existing_objects.get(reg_num)
            if not ip_object:
                continue

            for author_data in authors_data:
                key = f"{author_data['last_name']}|{author_data['first_name']}|{author_data['middle_name']}"
                if key not in author_to_key:
                    author_to_key[key] = {
                        'data': author_data,
                        'ip_objects': []
                    }
                author_to_key[key]['ip_objects'].append(ip_object)
                total_relations += 1

        all_keys = list(author_to_key.keys())
        self.stdout.write(f"        Уникальных авторов: {len(all_keys)}, всего связей: {total_relations}")

        # ШАГ 2: Поиск в БД
        self.stdout.write("        Шаг 2/6: Поиск в БД...")
        existing_people = {}
        batch_size = 50

        with tqdm(total=len(all_keys), desc="           Поиск", unit=" ключ") as pbar:
            for i in range(0, len(all_keys), batch_size):
                batch_keys = all_keys[i:i+batch_size]

                name_conditions = models.Q()
                for key in batch_keys:
                    last, first, middle = key.split('|')
                    if middle:
                        name_conditions |= models.Q(
                            last_name=last,
                            first_name=first,
                            middle_name=middle
                        )
                    else:
                        name_conditions |= models.Q(
                            last_name=last,
                            first_name=first,
                            middle_name__isnull=True
                        ) | models.Q(
                            last_name=last,
                            first_name=first,
                            middle_name=''
                        )

                for person in Person.objects.filter(name_conditions):
                    key = f"{person.last_name}|{person.first_name}|{person.middle_name or ''}"
                    existing_people[key] = person
                    self.person_cache[key] = person

                pbar.update(len(batch_keys))
                if (i // batch_size) % 10 == 0:
                    pbar.set_postfix({"найдено": len(existing_people)})

        self.stdout.write(f"        Найдено существующих: {len(existing_people)}")

        # ШАГ 3: Подготовка новых авторов
        self.stdout.write("        Шаг 3/6: Подготовка новых авторов...")
        people_to_create = []
        key_to_new_person = {}

        max_id = Person.objects.aggregate(models.Max('ceo_id'))['ceo_id__max'] or 0
        next_id = max_id + 1
        existing_slugs = set(Person.objects.values_list('slug', flat=True))

        with tqdm(total=len(all_keys), desc="           Подготовка", unit=" ключ") as pbar:
            for key, info in author_to_key.items():
                if key not in existing_people:
                    author_data = info['data']

                    name_parts = [author_data['last_name'], author_data['first_name']]
                    if author_data['middle_name']:
                        name_parts.append(author_data['middle_name'])

                    base_slug = slugify(' '.join(name_parts).strip())
                    if not base_slug:
                        base_slug = 'person'

                    unique_slug = base_slug
                    counter = 1
                    while unique_slug in existing_slugs or any(p.slug == unique_slug for p in people_to_create):
                        unique_slug = f"{base_slug}-{counter}"
                        counter += 1

                    person = Person(
                        ceo_id=next_id,
                        ceo=author_data['full_name'],
                        last_name=author_data['last_name'],
                        first_name=author_data['first_name'],
                        middle_name=author_data['middle_name'] or '',
                        slug=unique_slug
                    )
                    people_to_create.append(person)
                    key_to_new_person[key] = person
                    next_id += 1
                    existing_slugs.add(unique_slug)

                pbar.update(1)
                if pbar.n % 10000 == 0:
                    pbar.set_postfix({"к созданию": len(people_to_create)})

        self.stdout.write(f"        Новых авторов для создания: {len(people_to_create)}")

        # ШАГ 4: Создание новых авторов
        if people_to_create:
            self.stdout.write(f"        Шаг 4/6: Создание новых авторов...")
            batch_size = 500
            created_count = 0

            with tqdm(total=len(people_to_create), desc="           Создание", unit=" чел") as pbar:
                for i in range(0, len(people_to_create), batch_size):
                    batch = people_to_create[i:i+batch_size]
                    Person.objects.bulk_create(batch, batch_size=batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))
                    pbar.set_postfix({"создано": created_count})

            for person in people_to_create:
                key = f"{person.last_name}|{person.first_name}|{person.middle_name}"
                self.person_cache[key] = person

        # ШАГ 5: Подготовка связей
        self.stdout.write("        Шаг 5/6: Подготовка связей...")
        unique_pairs = set()
        through_objs = []

        for key, info in author_to_key.items():
            person = existing_people.get(key) or key_to_new_person.get(key)
            if not person:
                continue

            unique_ip_objects = {ip.pk: ip for ip in info['ip_objects']}

            for ip_object in unique_ip_objects.values():
                pair = (ip_object.pk, person.pk)
                if pair not in unique_pairs:
                    unique_pairs.add(pair)
                    through_objs.append(
                        IPObject.authors.through(
                            ipobject_id=ip_object.pk,
                            person_id=person.pk
                        )
                    )

        self.stdout.write(f"        Уникальных связей для создания: {len(through_objs)}")

        # ШАГ 6: Создание связей
        if through_objs:
            self.stdout.write(f"        Шаг 6/6: Создание связей...")

            # Получаем все уникальные ID IP-объектов
            ip_ids = list(set(obj.ipobject_id for obj in through_objs))
            self.stdout.write(f"           Удаление старых связей для {len(ip_ids)} IP-объектов...")

            # Удаляем старые связи ПАЧКАМИ по 500 ID
            delete_batch_size = 500
            deleted_total = 0

            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.authors.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted

                if (i // delete_batch_size) % 10 == 0:
                    self.stdout.write(f"              Удалено {deleted_total} связей...")

            self.stdout.write(f"           Удалено старых связей: {deleted_total}")

            # Создаем новые связи пачками
            create_batch_size = 1000
            created_count = 0

            with tqdm(total=len(through_objs), desc="           Добавление", unit=" связь") as pbar:
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.authors.through.objects.bulk_create(batch, batch_size=create_batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))
                    pbar.set_postfix({"создано": created_count})

        self.stdout.write(f"        ✅ Обработка авторов завершена")

    def _process_holders_batch_with_progress(self, existing_objects, holders_cache):
        """Обработка правообладателей с прогресс-баром и разбивкой на пачки"""
        self.stdout.write(f"     ⚡ Обработка правообладателей...")

        # ШАГ 1: Сбор уникальных правообладателей
        self.stdout.write("        Шаг 1/7: Сбор уникальных правообладателей...")
        all_holders = set()
        for holders_list in holders_cache.values():
            all_holders.update(holders_list)

        self.stdout.write(f"        Уникальных правообладателей: {len(all_holders)}")

        # ШАГ 2: Определение типов
        self.stdout.write("        Шаг 2/7: Определение типов...")
        person_holders = []
        org_holders = []

        with tqdm(total=len(all_holders), desc="           Анализ", unit=" об") as pbar:
            for holder in all_holders:
                if self.type_detector.detect_type(holder) == 'person':
                    person_holders.append(holder)
                else:
                    org_holders.append(holder)
                pbar.update(1)

        self.stdout.write(f"        Люди: {len(person_holders)}, Организации: {len(org_holders)}")

        # ШАГ 3: Обработка организаций (ЧАСТЯМИ)
        self.stdout.write("        Шаг 3/7: Обработка организаций...")
        org_map = {}

        if org_holders:
            CHUNK_SIZE = 1000
            total_orgs = len(org_holders)

            self.stdout.write(f"        Обработка {total_orgs} организаций частями по {CHUNK_SIZE}...")

            for chunk_start in range(0, total_orgs, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, total_orgs)
                chunk_holders = org_holders[chunk_start:chunk_end]

                # Поиск существующих в этой части
                existing_orgs = {}
                for org in Organization.objects.filter(name__in=chunk_holders):
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

                # Мгновенно создаем в БД
                if orgs_to_create:
                    batch_size = 500
                    for i in range(0, len(orgs_to_create), batch_size):
                        batch = orgs_to_create[i:i+batch_size]
                        Organization.objects.bulk_create(batch, batch_size=batch_size)

                # Освобождаем память
                del existing_orgs
                del orgs_to_create

                progress = (chunk_end / total_orgs) * 100
                self.stdout.write(f"           Прогресс: {progress:.1f}%")

            # Финальный маппинг
            for holder in org_holders:
                org_map[holder] = self.organization_cache.get(holder)

        # ШАГ 4: Обработка людей (ЧАСТЯМИ)
        self.stdout.write("        Шаг 4/7: Обработка людей...")
        person_map = {}

        if person_holders:
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

                # Мгновенно создаем в БД
                if people_to_create:
                    batch_size = 500
                    for i in range(0, len(people_to_create), batch_size):
                        batch = people_to_create[i:i+batch_size]
                        Person.objects.bulk_create(batch, batch_size=batch_size)

                # Освобождаем память
                del existing_people
                del people_to_create

                progress = (chunk_end / total_people) * 100
                self.stdout.write(f"           Прогресс: {progress:.1f}%")

            # Финальный маппинг
            for holder in person_holders:
                person_map[holder] = self.person_cache.get(holder)

        # ШАГ 5: Подготовка связей
        self.stdout.write("        Шаг 5/7: Подготовка связей...")

        org_relations = set()
        person_relations = set()

        with tqdm(total=sum(len(h) for h in holders_cache.values()), desc="           Сбор связей", unit=" св") as pbar:
            for reg_num, holders_list in holders_cache.items():
                ip_object = existing_objects.get(reg_num)
                if not ip_object:
                    continue

                for holder in holders_list:
                    if holder in org_map and org_map[holder]:
                        org_relations.add((ip_object.pk, org_map[holder].pk))
                    elif holder in person_map and person_map[holder]:
                        person_relations.add((ip_object.pk, person_map[holder].pk))
                    pbar.update(1)

        self.stdout.write(f"        Уникальных связей с организациями: {len(org_relations)}")
        self.stdout.write(f"        Уникальных связей с людьми: {len(person_relations)}")

        # ШАГ 6: Создание связей с организациями
        if org_relations:
            self.stdout.write("        Шаг 6/7: Создание связей с организациями...")

            ip_ids = list(set(ip_id for ip_id, _ in org_relations))

            # Удаляем старые связи ПАЧКАМИ
            delete_batch_size = 500
            deleted_total = 0
            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.owner_organizations.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted
                if (i // delete_batch_size) % 10 == 0:
                    self.stdout.write(f"              Удалено {deleted_total} связей с организациями...")

            self.stdout.write(f"           Удалено старых связей: {deleted_total}")

            # Создаем новые связи пачками
            through_objs = [
                IPObject.owner_organizations.through(
                    ipobject_id=ip_id,
                    organization_id=org_id
                )
                for ip_id, org_id in org_relations
            ]

            create_batch_size = 1000
            created_count = 0
            with tqdm(total=len(through_objs), desc="           Добавление", unit=" св") as pbar:
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.owner_organizations.through.objects.bulk_create(batch, batch_size=create_batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))

        # ШАГ 7: Создание связей с людьми
        if person_relations:
            self.stdout.write("        Шаг 7/7: Создание связей с людьми...")

            ip_ids = list(set(ip_id for ip_id, _ in person_relations))

            # Удаляем старые связи ПАЧКАМИ
            delete_batch_size = 500
            deleted_total = 0
            for i in range(0, len(ip_ids), delete_batch_size):
                batch_ip_ids = ip_ids[i:i+delete_batch_size]
                deleted, _ = IPObject.owner_persons.through.objects.filter(
                    ipobject_id__in=batch_ip_ids
                ).delete()
                deleted_total += deleted
                if (i // delete_batch_size) % 10 == 0:
                    self.stdout.write(f"              Удалено {deleted_total} связей с людьми...")

            self.stdout.write(f"           Удалено старых связей: {deleted_total}")

            # Создаем новые связи пачками
            through_objs = [
                IPObject.owner_persons.through(
                    ipobject_id=ip_id,
                    person_id=person_id
                )
                for ip_id, person_id in person_relations
            ]

            create_batch_size = 1000
            created_count = 0
            with tqdm(total=len(through_objs), desc="           Добавление", unit=" св") as pbar:
                for i in range(0, len(through_objs), create_batch_size):
                    batch = through_objs[i:i+create_batch_size]
                    IPObject.owner_persons.through.objects.bulk_create(batch, batch_size=create_batch_size)
                    created_count += len(batch)
                    pbar.update(len(batch))

        self.stdout.write(f"        ✅ Обработка правообладателей завершена")
