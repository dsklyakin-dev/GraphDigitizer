"""
Автоматическое определение осей на графике.
Простой и надёжный алгоритм.
"""

import cv2
import numpy as np


class AxisDetector:
    def __init__(self, image_bgr):
        self.gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        self.height, self.width = self.gray.shape

        flat = self.gray.flatten()
        p5 = np.percentile(flat, 5)
        self.dark_threshold = max(60, min(120, p5 + 30))

    def _find_horizontal_segments(self, y, min_length=50):
        """Ищет длинные горизонтальные линии, пропуская короткие разрывы."""
        row = self.gray[y, :]
        dark = row < self.dark_threshold

        segments = []
        start = None
        gap = 0
        max_gap = 5  # Разрыв до 5 пикселей внутри линии

        for x, d in enumerate(dark):
            if d:
                if start is None:
                    start = x
                gap = 0
            else:
                if start is not None:
                    gap += 1
                    if gap > max_gap:
                        if x - gap - start >= min_length:
                            segments.append((start, x - gap - 1))
                        start = None
                        gap = 0

        if start is not None:
            end = len(row) - gap - 1
            if end - start >= min_length:
                segments.append((start, end))

        return segments

    def _find_vertical_segment_up(self, x, y_start, min_length=50):
        """
        Ищет верхнюю точку вертикальной оси.
        Останавливается на разрыве длиной > 8 пикселей.
        """
        # Убеждаемся что стартуем с тёмной вертикальной линии
        best_x = x
        best_dark = 0
        for dx in range(-5, 6):
            nx = x + dx
            if 0 <= nx < self.width:
                cnt = 0
                for dy in range(0, 30):
                    yy = min(self.height - 1, y_start + dy)
                    if self.gray[yy, nx] < self.dark_threshold:
                        cnt += 1
                if cnt > best_dark:
                    best_dark = cnt
                    best_x = nx

        x = best_x

        top_y = y_start
        gap = 0
        max_gap = 8  # максимум 8 светлых пикселей подряд

        for y in range(y_start, max(0, y_start - 2000), -1):
            # Проверяем широкое окно ±8 по X — ось толстая
            is_dark = False
            for dx in range(-8, 9):
                nx = x + dx
                if 0 <= nx < self.width and self.gray[y, nx] < self.dark_threshold:
                    is_dark = True
                    break

            if is_dark:
                top_y = y
                gap = 0
            else:
                gap += 1
                if gap > max_gap:
                    break

        length = y_start - top_y
        return length, top_y

    def detect(self):
        """Ищет оси. Предполагает, что картинка уже выровнена."""
        return self._detect_no_rotation()

    def find_origin(self, min_length=100):
        """
        Ищет левый нижний угол графика (пересечение осей X и Y).
        Ищет вертикальную линию и горизонтальную, которые образуют угол.
        """
        # 1. Ищем все длинные горизонтальные сегменты
        h_segments = []
        for y in range(0, self.height, 2):
            segs = self._find_horizontal_segments(y, min_length)
            for start_x, end_x in segs:
                h_segments.append((start_x, end_x, y))

        if not h_segments:
            return None

        # Сортируем горизонтали по длине (от самой длинной к короткой)
        # Но мы знаем, что рамка самая длинная - её лучше пропустить
        h_segments.sort(key=lambda s: s[1] - s[0], reverse=True)

        best_score = -1
        best_origin = None

        # Проходим по всем горизонталям
        for h_start, h_end, h_y in h_segments:
            # Пропускаем слишком короткие
            if (h_end - h_start) < min_length:
                continue

            # Ищем вертикаль, которая начинается в левой части этой горизонтали
            # (в пределах 50 пикселей от начала)
            best_v_len = 0
            best_v_x = None

            for x in range(h_start, min(h_start + 50, self.width)):
                # Ищем вверх от этой горизонтали
                v_len, top_y = self._find_vertical_segment_up(x, h_y, min_length)
                if v_len > best_v_len:
                    best_v_len = v_len
                    best_v_x = x

            # Если нашли вертикаль, которая длиннее горизонтали (или хотя бы 50% от неё)
            # И она находится в левой части экрана (x < width/2) — это хороший кандидат
            if best_v_x is not None and best_v_len > 50:
                # Оценка: длина горизонтали + длина вертикали,
                # но со штрафом, если точка далеко справа (чтобы не брать рамку)
                score = (h_end - h_start) + best_v_len

                # Если ось X начинается далеко справа (например, x > width/2),
                # это, скорее всего, не начало координат, а часть рамки
                if h_start < self.width * 0.5:
                    # Это хороший кандидат
                    if score > best_score:
                        best_score = score
                        # Уточняем X: ищем самый темный столбец в окне ±10 от best_v_x
                        refined_x = best_v_x
                        max_dark_count = 0
                        for dx in range(-10, 11):
                            test_x = best_v_x + dx
                            if 0 <= test_x < self.width:
                                # Считаем тёмные пиксели вверх от h_y
                                cnt = 0
                                for dy in range(0, 100):
                                    yy = h_y - dy
                                    if yy >= 0 and self.gray[yy, test_x] < self.dark_threshold:
                                        cnt += 1
                                if cnt > max_dark_count:
                                    max_dark_count = cnt
                                    refined_x = test_x
                        best_origin = (refined_x, h_y)

        return best_origin

    def _detect_no_rotation(self):
        """Исходная логика: ищем максимальную площадь (h_end - x) * v_len."""
        best_origin = None
        best_x_end = None
        best_y_end = None
        best_score = 0

        all_h_segments = {}
        for y in range(0, self.height, 2):
            segs = self._find_horizontal_segments(y, 50)
            if segs:
                all_h_segments[y] = segs

        for y, segments in all_h_segments.items():
            for h_start, h_end in segments:
                for x in range(h_start, min(h_start + 15, h_end)):
                    v_len, top_y = self._find_vertical_segment_up(x, y, 50)
                    if v_len >= 50:
                        score = (h_end - x) * v_len
                        if score > best_score:
                            best_score = score
                            best_origin = (x, y)
                            best_x_end = (h_end, y)
                            best_y_end = (x, top_y)
                        break

        if best_origin is None:
            return None

        return {
            'origin': best_origin,
            'x_end': best_x_end,
            'y_end': best_y_end,
        }

    def find_x_end(self, origin_x, origin_y, max_search=3000):
        """
        Идёт от (origin_x, origin_y) ВПРАВО по горизонтали,
        находит конец оси X.
        Возвращает (end_x, end_y) или None.
        """
        # Проверяем, что начало лежит на тёмной горизонтали
        # Ищем строку рядом с origin_y, где больше всего тёмных пикселей вправо
        best_row = origin_y
        best_dark = 0

        for dy in range(-5, 6):
            y = origin_y + dy
            if not (0 <= y < self.height):
                continue
            # Считаем тёмные пиксели вправо от origin_x
            dark_count = 0
            gap = 0
            for x in range(origin_x, min(self.width, origin_x + max_search)):
                if self.gray[y, x] < self.dark_threshold:
                    dark_count += 1
                    gap = 0
                else:
                    gap += 1
                    if gap > 15:  # разрыв больше 15 — стоп
                        break
            if dark_count > best_dark:
                best_dark = dark_count
                best_row = y

        y = best_row

        # Идём вправо по этой строке, ищем конец
        end_x = origin_x
        gap = 0
        max_gap = 15
        for x in range(origin_x, min(self.width, origin_x + max_search)):
            # Смотрим широкое окно ±4 по Y (линия толстая)
            is_dark = False
            for dy in range(-4, 5):
                yy = y + dy
                if 0 <= yy < self.height and self.gray[yy, x] < self.dark_threshold:
                    is_dark = True
                    break

            if is_dark:
                end_x = x
                gap = 0
            else:
                gap += 1
                if gap > max_gap:
                    break

        return (end_x, y)

    def find_y_end(self, origin_x, origin_y, max_search=3000):
        """
        Идёт от (origin_x, origin_y) ВВЕРХ по вертикали,
        находит конец оси Y.
        Возвращает (end_x, end_y) или None.
        """
        # Аналогично — ищем столбец рядом с origin_x, где больше всего тёмных пикселей вверх
        best_col = origin_x
        best_dark = 0

        for dx in range(-5, 6):
            x = origin_x + dx
            if not (0 <= x < self.width):
                continue
            dark_count = 0
            gap = 0
            for y in range(origin_y, max(0, origin_y - max_search), -1):
                if self.gray[y, x] < self.dark_threshold:
                    dark_count += 1
                    gap = 0
                else:
                    gap += 1
                    if gap > 15:
                        break
            if dark_count > best_dark:
                best_dark = dark_count
                best_col = x

        x = best_col

        # Идём вверх по этому столбцу
        end_y = origin_y
        gap = 0
        max_gap = 15
        for y in range(origin_y, max(0, origin_y - max_search), -1):
            # Смотрим широкое окно ±4 по X
            is_dark = False
            for dx in range(-4, 5):
                xx = x + dx
                if 0 <= xx < self.width and self.gray[y, xx] < self.dark_threshold:
                    is_dark = True
                    break

            if is_dark:
                end_y = y
                gap = 0
            else:
                gap += 1
                if gap > max_gap:
                    break

        return (x, end_y)

    def refine_point(self, x, y, search=30):
        """Заглушка."""
        return x, y