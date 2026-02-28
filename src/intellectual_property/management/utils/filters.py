"""
Утилиты для фильтрации DataFrame
Поддерживают фильтрацию по диапазону лет
"""

from datetime import datetime
import pandas as pd


def filter_by_registration_year(df, min_year, stdout=None, max_year=None):
    """
    Фильтрация DataFrame по году регистрации с поддержкой диапазона
    
    Args:
        df: DataFrame для фильтрации
        min_year: минимальный год
        stdout: поток вывода
        max_year: максимальный год (опционально)
    """
    def extract_year(date_str):
        try:
            if pd.isna(date_str) or not date_str:
                return None

            date_str = str(date_str).strip()
            if not date_str:
                return None

            for fmt in ['%Y%m%d', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str, fmt).year
                except (ValueError, TypeError):
                    continue

            try:
                return pd.to_datetime(date_str).year
            except (ValueError, TypeError):
                return None
        except:
            return None

    if stdout:
        stdout.write("  🔍 Фильтрация по году регистрации...")

    if 'registration date' not in df.columns:
        if stdout:
            stdout.write("  ⚠️ Колонка 'registration date' не найдена, пропускаем фильтрацию по году")
        return df

    df['_year'] = df['registration date'].apply(extract_year)

    if stdout:
        # Фильтруем None значения для статистики
        valid_years = df['_year'].dropna()
        if not valid_years.empty:
            years_dist = valid_years.value_counts().sort_index()
            years_list = list(years_dist.items())
            if len(years_list) > 0:
                stdout.write(f"     Диапазон годов: {years_list[0][0]:.0f} - {years_list[-1][0]:.0f}")

    # Применяем фильтр по годам
    condition = df['_year'] >= min_year
    if max_year:
        condition &= df['_year'] <= max_year
    
    filtered_df = df[condition].copy() if '_year' in df.columns else df.copy()
    
    if '_year' in filtered_df.columns:
        filtered_df.drop('_year', axis=1, inplace=True)

    return filtered_df


def filter_by_actual(df, stdout=None):
    """
    Фильтрация DataFrame по активности (actual = True)
    """
    def parse_actual(value):
        if pd.isna(value) or not value:
            return False
        value = str(value).lower().strip()
        return value in ['1', 'true', 'yes', 'да', 'действует', 't', '1.0', 'активен']

    if 'actual' not in df.columns:
        if stdout:
            stdout.write("  ⚠️ Колонка 'actual' не найдена, пропускаем фильтрацию по активности")
        return df

    df['_actual'] = df['actual'].apply(parse_actual)
    filtered_df = df[df['_actual'] == True].copy()
    filtered_df.drop('_actual', axis=1, inplace=True)

    return filtered_df


def apply_filters(df, min_year, only_active, stdout=None, max_year=None):
    """
    Применение всех фильтров к DataFrame
    
    Args:
        df: DataFrame для фильтрации
        min_year: минимальный год
        only_active: фильтровать только активные
        stdout: поток вывода
        max_year: максимальный год (опционально)
    """
    original_count = len(df)

    if min_year is not None:
        df = filter_by_registration_year(df, min_year, stdout, max_year)

    if only_active:
        df = filter_by_actual(df, stdout)

    filtered_count = len(df)
    if stdout and filtered_count < original_count:
        stdout.write(f"  🔍 Фильтрация: {original_count} → {filtered_count} записей")

    return df