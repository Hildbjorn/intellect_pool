"""
Нормализация названий организаций (только для поиска, не для сохранения)
"""

import re
from typing import Dict, Any

import pandas as pd

from core.models import OrganizationNormalizationRule
from .text_processor import RussianTextProcessor


class OrganizationNormalizer:
    """Нормализация названий организаций (только для поиска, не для сохранения)"""

    def __init__(self):
        self.rules_cache = None
        self.processor = RussianTextProcessor()
        self.load_rules()

    def load_rules(self):
        """Загрузка правил из БД"""
        try:
            rules = OrganizationNormalizationRule.objects.all().order_by('priority')
            self.rules_cache = [
                {
                    'original': rule.original_text.lower(),
                    'replacement': rule.replacement_text.lower(),
                    'type': rule.rule_type,
                    'priority': rule.priority
                }
                for rule in rules
            ]
        except Exception as e:
            self.rules_cache = []
            # Логирование ошибки, но не падаем

    def normalize_for_search(self, name: str) -> Dict[str, Any]:
        """
        Нормализация названия ТОЛЬКО для поиска дубликатов
        Само название остается как в CSV
        """
        if pd.isna(name) or not name:
            return {'normalized': '', 'keywords': [], 'original': name}

        original = str(name).strip()
        name_lower = original.lower()

        # Применяем правила из БД для нормализации
        normalized = name_lower
        if self.rules_cache:
            for rule in self.rules_cache:
                try:
                    if rule['type'] == 'ignore':
                        pattern = r'\b' + re.escape(rule['original']) + r'\b'
                        normalized = re.sub(pattern, '', normalized)
                    else:
                        pattern = r'\b' + re.escape(rule['original']) + r'\b'
                        normalized = re.sub(pattern, rule['replacement'], normalized)
                except Exception:
                    continue

        # Убираем кавычки и знаки препинания для поиска
        normalized = re.sub(r'["\'«»„“”]', '', normalized)
        normalized = re.sub(r'[^\w\s-]', ' ', normalized)
        normalized = ' '.join(normalized.split())

        # Извлекаем ключевые слова для поиска
        keywords = []

        # Слова в кавычках
        quoted = re.findall(r'"([^"]+)"', original)
        for q in quoted:
            words = q.lower().split()
            keywords.extend([w for w in words if len(w) > 3])

        # Аббревиатуры
        abbrs = re.findall(r'\b[А-ЯЁA-Z]{2,}\b', original)
        keywords.extend([a.lower() for a in abbrs if len(a) >= 2])

        # Коды (ИНН, ОГРН и т.д.)
        codes = re.findall(r'\b\d{10,}\b', original)
        keywords.extend(codes)

        return {
            'normalized': normalized,
            'keywords': list(set(keywords)),
            'original': original,
        }

    def format_organization_name(self, name: str) -> str:
        """Возвращает оригинальное название без изменений"""
        return name
