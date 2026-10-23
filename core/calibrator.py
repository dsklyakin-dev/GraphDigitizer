"""
Калибровка осей координат.
Хранит точки калибровки и переводит пиксели в значения.
"""

import json
from pathlib import Path


class Calibrator:
    """Управляет калибровкой графика."""

    def __init__(self):
        # Точки калибровки: {name: {'pixel': (x, y), 'value': (vx, vy)}}
        self.points = {}

        # Масштаб
        self.x_scale = 1.0
        self.y_scale = 1.0
        self.x_offset = 0.0
        self.y_offset = 0.0

        # Текущий шаг ручной калибровки (0, 1, 2)
        self.step = 0

        # Значения по умолчанию для диалога
        self.field_values = {
            'X0': '0', 'Y0': '0', 'X1': '10', 'Y1': '10'
        }

    def is_calibrated(self):
        """Проверяет, откалиброван ли график."""
        return len(self.points) >= 3

    def reset(self):
        """Сбрасывает калибровку."""
        self.points = {}
        self.step = 0
        self.x_scale = 1.0
        self.y_scale = 1.0
        self.x_offset = 0.0
        self.y_offset = 0.0

    def set_from_axis_detection(self, origin_px, x_end_px, y_end_px,
                                x0, y0, x1, y1):
        """Устанавливает калибровку из автоопределения осей."""
        self.points = {
            'origin': {'pixel': tuple(origin_px), 'value': (x0, y0)},
            'x_max': {'pixel': tuple(x_end_px), 'value': (x1, y0)},
            'y_max': {'pixel': tuple(y_end_px), 'value': (x0, y1)},
        }
        self.field_values = {
            'X0': str(x0), 'Y0': str(y0),
            'X1': str(x1), 'Y1': str(y1),
        }
        self._recalc()

    def add_point(self, step, pixel_xy, value_xy):
        """Добавляет точку ручной калибровки."""
        names = ['origin', 'x_max', 'y_max']
        self.points[names[step]] = {
            'pixel': tuple(pixel_xy),
            'value': tuple(value_xy),
        }
        if len(self.points) == 3:
            self._recalc()

    def _recalc(self):
        """Пересчитывает масштаб."""
        o = self.points['origin']
        x = self.points['x_max']
        y = self.points['y_max']

        # Защита от деления на ноль
        dvx = x['value'][0] - o['value'][0]
        dvy = y['value'][1] - o['value'][1]

        dx_px = x['pixel'][0] - o['pixel'][0]
        dy_px = o['pixel'][1] - y['pixel'][1]

        # Если значения совпадают или пиксели совпадают — ставим 1.0
        if abs(dvx) < 1e-9 or abs(dx_px) < 1e-9:
            self.x_scale = 1.0
        else:
            self.x_scale = dx_px / dvx

        if abs(dvy) < 1e-9 or abs(dy_px) < 1e-9:
            self.y_scale = 1.0
        else:
            self.y_scale = dy_px / dvy

        # Защита для offset
        if abs(self.x_scale) > 1e-9:
            self.x_offset = o['value'][0] - o['pixel'][0] / self.x_scale
        else:
            self.x_offset = 0.0

        if abs(self.y_scale) > 1e-9:
            self.y_offset = o['value'][1] + o['pixel'][1] / self.y_scale
        else:
            self.y_offset = 0.0

    def px_to_val(self, px, py):
        """Пиксели → значения. Защита от деления на ноль."""
        if abs(self.x_scale) < 1e-9:
            x_val = 0.0
        else:
            x_val = px / self.x_scale + self.x_offset

        if abs(self.y_scale) < 1e-9:
            y_val = 0.0
        else:
            y_val = -py / self.y_scale + self.y_offset

        return x_val, y_val

    def val_to_px(self, x_val, y_val):
        """Значения → пиксели."""
        px = int((x_val - self.x_offset) * self.x_scale)
        py = int(-(y_val - self.y_offset) * self.y_scale)
        return px, py

    def save(self, path):
        """Сохраняет калибровку в JSON."""
        data = {
            'points': {
                name: {
                    'pixel': list(info['pixel']),
                    'value': list(info['value']),
                }
                for name, info in self.points.items()
            },
            'field_values': self.field_values,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, path):
        """Загружает калибровку из JSON."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'points' not in data or len(data['points']) < 3:
                return False

            self.points = {
                name: {
                    'pixel': tuple(info['pixel']),
                    'value': tuple(info['value']),
                }
                for name, info in data['points'].items()
            }
            self.field_values = data.get('field_values', self.field_values)
            self._recalc()
            return True
        except Exception as e:
            print(f'Ошибка загрузки калибровки: {e}')
            return False