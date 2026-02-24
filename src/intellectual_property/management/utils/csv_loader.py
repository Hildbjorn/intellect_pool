"""
Утилиты для загрузки CSV файлов
"""

import pandas as pd


def load_csv_with_strategies(file_path, encoding, delimiter, stdout=None):
    """
    Загрузка CSV с несколькими стратегиями
    """
    strategies = [
        {'encoding': encoding, 'delimiter': delimiter, 'skipinitialspace': True},
        {'encoding': 'cp1251', 'delimiter': delimiter, 'skipinitialspace': True},
        {'encoding': 'utf-8', 'delimiter': ';', 'skipinitialspace': True},
        {'encoding': 'cp1251', 'delimiter': ';', 'skipinitialspace': True},
        {'encoding': 'utf-8', 'delimiter': '\t', 'skipinitialspace': True},
    ]

    for strategy in strategies:
        try:
            df = pd.read_csv(file_path, **strategy, dtype=str, keep_default_na=False)
            if stdout:
                stdout.write(f"  ✅ Успешно загружено с параметрами: {strategy}")

            df.columns = [col.strip().strip('\ufeff').strip('"') for col in df.columns]
            return df
        except Exception:
            continue

    raise Exception("Не удалось загрузить CSV ни одной стратегией")
