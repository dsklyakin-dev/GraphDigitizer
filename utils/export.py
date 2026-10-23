"""
Экспорт данных в Excel / CSV.
"""

import numpy as np
import pandas as pd
from pathlib import Path


def export_1d_data(data_points, x3_value, path):
    """
    Экспорт 1D данных.
    data_points: [[x, y], ...]
    x3_value: строка или None
    path: путь к файлу
    """
    if not data_points:
        return False

    data = np.array(data_points)

    if x3_value:
        df = pd.DataFrame({
            'X': data[:, 0],
            'X3': x3_value,
            'Y': data[:, 1],
        })
    else:
        df = pd.DataFrame({
            'X': data[:, 0],
            'Y': data[:, 1],
        })

    return _save_df(df, path, 'Данные')


def export_2d_data(data_points_2d, x3_value, path):
    """
    Экспорт 2D данных.
    data_points_2d: {curve_name: [[x, y], ...]}
    x3_value: строка или None
    path: путь к файлу
    """
    all_data = []
    for curve_name, points in data_points_2d.items():
        for x, y in points:
            if x3_value:
                all_data.append([x, curve_name, x3_value, y])
            else:
                all_data.append([x, curve_name, y])

    if not all_data:
        return False

    if x3_value:
        df = pd.DataFrame(all_data, columns=['X', 'X2', 'X3', 'Y'])
    else:
        df = pd.DataFrame(all_data, columns=['X', 'X2', 'Y'])

    return _save_df(df, path, 'Данные')


def _save_df(df, path, sheet_name):
    """Сохраняет DataFrame в xlsx или csv."""
    path = str(path)
    try:
        if path.endswith('.xlsx'):
            df.to_excel(path, sheet_name=sheet_name, index=False, engine='openpyxl')
        else:
            df.to_csv(path, index=False, sep=',')
        return True
    except Exception as e:
        print(f'Ошибка сохранения: {e}')
        return False