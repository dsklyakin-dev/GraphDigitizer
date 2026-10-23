"""
Детектор кривых на графике.
Метод: водяной поток с фильтрацией по контрасту (кривая темнее сетки).
v7.1 — фикс _snap_to_curve (не возвращает None)
"""

import cv2
import numpy as np
from collections import deque


class CurveDetector:
    def __init__(self, image_bgr, calibrator):
        self.image = image_bgr
        self.gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        self.calibrator = calibrator
        self.h, self.w = self.gray.shape

        # Кэш
        self._mask_cache = None
        self._bounds_cache = None
        self._roi_offset = (0, 0)

    def _get_bounds(self):
        if not self.calibrator.is_calibrated():
            return 0, self.w, 0, self.h
        o = self.calibrator.points['origin']['pixel']
        x_end = self.calibrator.points['x_max']['pixel']
        y_end = self.calibrator.points['y_max']['pixel']
        return int(o[0]), int(x_end[0]), int(y_end[1]), int(o[1])

    # ============================================================
    # МАСКА "ГДЕ МОЖЕТ БЫТЬ КРИВАЯ"
    # ============================================================

    def _get_mask(self):
        """
        Маска: эрозия 3x3 + обрезка осей + удаление верхнего правого угла.
        """
        x_min, x_max, y_min, y_max = self._get_bounds()
        key = (x_min, x_max, y_min, y_max)

        if self._mask_cache is not None and self._bounds_cache == key:
            return self._mask_cache

        roi = self.gray[y_min:y_max, x_min:x_max].copy()

        # 1. Бинаризация
        _, binary = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 2. Эрозия 3x3
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        eroded = cv2.erode(binary, kernel_erode, iterations=1)

        # 3. Дилатация
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        restored = cv2.dilate(eroded, kernel_dilate, iterations=1)

        # 4. Оставляем крупные компоненты
        num, labels, stats, _ = cv2.connectedComponentsWithStats(restored, 8)
        cleaned = np.zeros_like(restored)
        for i in range(1, num):
            area = stats[i, cv2.CC_STAT_AREA]
            if area > 100:
                cleaned[labels == i] = 255

        # 5. ОБРЕЗАЕМ МАСКУ ОТ ОСЕЙ
        margin = 15
        h_mask, w_mask = cleaned.shape
        cleaned[:margin, :] = 0
        cleaned[-margin:, :] = 0
        cleaned[:, :margin] = 0
        cleaned[:, -margin:] = 0

        # 6. Обрезаем верхний правый угол
        corner = 40
        cleaned[:corner, -corner:] = 0

        self._mask_cache = cleaned
        self._bounds_cache = key
        self._roi_offset = (x_min, y_min)

        return cleaned

    def _remove_horizontal_lines(self, mask):
        """
        Удаляет чисто горизонтальные участки (сетка).
        Оставляем только пиксели, у которых есть вертикальные соседи.
        """
        h, w = mask.shape

        vertical_thickness = np.zeros_like(mask, dtype=np.int32)

        for y in range(h):
            for x in range(w):
                if mask[y, x] > 0:
                    count = 0
                    for dy in range(-2, 3):
                        ny = y + dy
                        if 0 <= ny < h and mask[ny, x] > 0:
                            count += 1
                    vertical_thickness[y, x] = count

        result = np.zeros_like(mask)
        result[vertical_thickness >= 3] = 255

        return result

    def _debug_show_mask(self):
        """Для отладки — возвращает маску."""
        return self._get_mask()

    # ============================================================
    # ВОДЯНОЙ ПОТОК ПО МАСКЕ
    # ============================================================

    def water_flow(self, start_x, start_y, end_x=None, end_y=None,
                   step_pixels=8, search_window=10, max_gap=8):
        mask = self._get_mask()
        ox, oy = self._roi_offset
        h_roi, w_roi = mask.shape

        sx = int(start_x - ox)
        sy = int(start_y - oy)
        sx = max(0, min(w_roi - 1, sx))
        sy = max(0, min(h_roi - 1, sy))

        # Проверяем: клик попал на кривую? Если нет — ищем рядом.
        # ВАЖНО: _snap_to_curve теперь всегда возвращает (x, y), даже если
        # не нашёл пиксель — вернёт исходную точку.
        snapped = self._snap_to_curve(mask, sx, sy, radius=15)
        sx, sy = snapped
        print(f'[DIGITIZE] Точка привязана к: ({sx}, {sy})')

        if end_x is not None and end_y is not None:
            ex = max(0, min(w_roi - 1, int(end_x - ox)))
            ey = max(0, min(h_roi - 1, int(end_y - oy)))
            ex, ey = self._snap_to_curve(mask, ex, ey, radius=15)
            path = self._follow_between(mask, sx, sy, ex, ey, step_pixels, search_window)
        else:
            right = self._follow_direction(mask, sx, sy, +1, step_pixels, search_window)
            left = self._follow_direction(mask, sx, sy, -1, step_pixels, search_window)
            left.reverse()
            if left and right and left[-1] == right[0]:
                left = left[:-1]
            path = left + right

        path_px = [(int(px + ox), int(py + oy)) for px, py in path]
        return path_px

    def _snap_to_curve(self, mask, x, y, radius=15):
        """
        Привязывает точку к ближайшему пикселю маски.
        ВСЕГДА возвращает кортеж (x, y):
        - если пиксель найден — координаты ближайшего пикселя маски;
        - если не найден — исходные (x, y) без изменений.
        """
        x1 = max(0, x - radius)
        x2 = min(mask.shape[1], x + radius)
        y1 = max(0, y - radius)
        y2 = min(mask.shape[0], y + radius)

        # Если окно поиска вырождено — возвращаем исходную точку
        if x1 >= x2 or y1 >= y2:
            return int(x), int(y)

        roi = mask[y1:y2, x1:x2]
        ys, xs = np.where(roi > 0)

        # Если в окне нет пикселей маски — возвращаем исходную точку
        if len(xs) == 0:
            return int(x), int(y)

        xs_abs = xs + x1
        ys_abs = ys + y1
        dists = (xs_abs - x) ** 2 + (ys_abs - y) ** 2
        idx = int(np.argmin(dists))

        return int(xs_abs[idx]), int(ys_abs[idx])

    def _find_pixel_in_column(self, mask, xi, cy, window, expected_dy):
        """Ищет пиксель маски в окне."""
        h_roi = mask.shape[0]

        if abs(expected_dy) > 0.5:
            center = int(cy + expected_dy)
        else:
            center = int(cy)

        w = max(5, int(window))
        y1 = max(0, center - w)
        y2 = min(h_roi, center + w)

        if y1 >= y2:
            return None

        column = mask[y1:y2, xi]
        if len(column) == 0:
            return None

        on_pixels = np.where(column > 0)[0]

        if len(on_pixels) == 0:
            return None

        expected_local = int(cy + expected_dy) - y1 if abs(expected_dy) > 0.5 else int(cy) - y1
        expected_local = max(0, min(len(column) - 1, expected_local))

        dists = np.abs(on_pixels - expected_local)
        best_idx = int(np.argmin(dists))
        best_y_local = int(on_pixels[best_idx])

        new_y = float(y1 + best_y_local)

        dy_total = new_y - cy
        max_jump = w * 2
        if abs(dy_total) > max_jump:
            new_y = cy + max_jump * (1 if dy_total > 0 else -1)

        return new_y

    def _follow_direction(self, mask, sx, sy, direction, step, window):
        h_roi, w_roi = mask.shape
        path = [(sx, sy)]
        cx, cy = float(sx), float(sy)
        y_history = deque(maxlen=8)
        y_history.append(cy)

        missed = 0
        stuck_count = 0
        prev_y = None

        while True:
            cx += direction * step
            if cx < 0 or cx >= w_roi:
                break

            xi = int(cx)

            expected_dy = 0
            if len(y_history) >= 3:
                yh = list(y_history)
                try:
                    expected_dy = np.polyfit(np.arange(len(yh)), yh, 1)[0]
                except Exception:
                    pass

            current_window = int(window)
            if abs(expected_dy) > 1.5:
                current_window = int(window * 1.8)

            new_y = self._find_pixel_in_column(mask, xi, cy, current_window, expected_dy)

            if new_y is None:
                new_y = self._find_pixel_in_column(mask, xi, cy, current_window * 2, expected_dy)

            if new_y is None:
                missed += 1
                if missed > 0:
                    break
                if len(y_history) >= 3:
                    new_y = cy + expected_dy
                else:
                    new_y = cy
            else:
                missed = 0

            if prev_y is not None and abs(new_y - prev_y) < 0.5:
                stuck_count += 1
            else:
                stuck_count = 0
            prev_y = new_y

            if stuck_count > 25 and len(path) > 30:
                break

            cy = new_y
            y_history.append(cy)
            path.append((int(cx), int(cy)))

        return path

    def _follow_between(self, mask, sx, sy, ex, ey, step, window):
        """
        Идёт от start до end. Автоматически выбирает направление:
        - Горизонтальное (по X) если |dx| > |dy|
        - Вертикальное (по Y) если |dy| > |dx|
        """
        dx = ex - sx
        dy = ey - sy

        if abs(dx) >= abs(dy):
            return self._follow_between_horizontal(mask, sx, sy, ex, ey, step, window)
        else:
            return self._follow_between_vertical(mask, sx, sy, ex, ey, step, window)

    def _follow_between_horizontal(self, mask, sx, sy, ex, ey, step, window):
        """Идёт по X (горизонтальный сегмент)."""
        h_roi, w_roi = mask.shape
        path = [(sx, sy)]
        cx, cy = float(sx), float(sy)
        y_history = deque(maxlen=8)
        y_history.append(sy)

        direction = 1 if ex >= sx else -1
        trend_slope = (ey - sy) / max(1, abs(ex - sx))

        while True:
            if direction > 0 and cx >= ex:
                break
            if direction < 0 and cx <= ex:
                break

            cx += direction * step
            if cx < 0 or cx >= w_roi:
                break

            xi = int(cx)

            expected_dy = 0
            if len(y_history) >= 3:
                yh = list(y_history)
                try:
                    expected_dy = np.polyfit(np.arange(len(yh)), yh, 1)[0]
                except Exception:
                    expected_dy = trend_slope * step * direction

            current_window = int(window)
            if abs(expected_dy) > 1.5:
                current_window = int(window * 1.8)

            new_y = self._find_pixel_in_column(mask, xi, cy, current_window, expected_dy)

            if new_y is None:
                new_y = self._find_pixel_in_column(mask, xi, cy, current_window * 2, expected_dy)

            if new_y is None:
                break

            cy = new_y
            y_history.append(cy)
            path.append((int(cx), int(cy)))

        path.append((ex, ey))
        return path

    def _follow_between_vertical(self, mask, sx, sy, ex, ey, step, window):
        """Идёт по Y (вертикальный сегмент)."""
        h_roi, w_roi = mask.shape
        path = [(sx, sy)]
        cx, cy = float(sx), float(sy)
        x_history = deque(maxlen=8)
        x_history.append(sx)

        direction = 1 if ey >= sy else -1
        trend_slope = (ex - sx) / max(1, abs(ey - sy))

        while True:
            if direction > 0 and cy >= ey:
                break
            if direction < 0 and cy <= ey:
                break

            cy += direction * step
            if cy < 0 or cy >= h_roi:
                break

            yi = int(cy)

            expected_dx = 0
            if len(x_history) >= 3:
                xh = list(x_history)
                try:
                    expected_dx = np.polyfit(np.arange(len(xh)), xh, 1)[0]
                except Exception:
                    expected_dx = trend_slope * step * direction

            current_window = int(window)
            if abs(expected_dx) > 1.5:
                current_window = int(window * 1.8)

            new_x = self._find_pixel_in_row(mask, yi, cx, current_window, expected_dx)

            if new_x is None:
                new_x = self._find_pixel_in_row(mask, yi, cx, current_window * 2, expected_dx)

            if new_x is None:
                break

            cx = new_x
            x_history.append(cx)
            path.append((int(cx), int(cy)))

        path.append((ex, ey))
        return path

    def _find_pixel_in_row(self, mask, yi, cx, window, expected_dx):
        """Ищет пиксель маски в строке yi (для вертикального движения)."""
        w_roi = mask.shape[1]

        if abs(expected_dx) > 0.5:
            center = int(cx + expected_dx)
        else:
            center = int(cx)

        w = max(5, int(window))
        x1 = max(0, center - w)
        x2 = min(w_roi, center + w)

        if x1 >= x2:
            return None

        row = mask[yi, x1:x2]
        if len(row) == 0:
            return None

        on_pixels = np.where(row > 0)[0]

        if len(on_pixels) == 0:
            return None

        expected_local = int(cx + expected_dx) - x1 if abs(expected_dx) > 0.5 else int(cx) - x1
        expected_local = max(0, min(len(row) - 1, expected_local))

        dists = np.abs(on_pixels - expected_local)
        best_idx = int(np.argmin(dists))
        best_x_local = int(on_pixels[best_idx])

        new_x = float(x1 + best_x_local)

        dx_total = new_x - cx
        max_jump = w * 2
        if abs(dx_total) > max_jump:
            new_x = cx + max_jump * (1 if dx_total > 0 else -1)

        return new_x

    # ============================================================
    # ОБРАБОТКА
    # ============================================================

    def pixels_to_values(self, path):
        if not self.calibrator.is_calibrated():
            return [(px, py) for px, py in path]
        return [list(self.calibrator.px_to_val(px, py)) for px, py in path]

    def thin_path(self, path, step_values=8):
        if len(path) < 2:
            return path
        reduced = [path[0]]
        for pt in path[1:]:
            dx = pt[0] - reduced[-1][0]
            dy = pt[1] - reduced[-1][1]
            if np.sqrt(dx * dx + dy * dy) >= step_values:
                reduced.append(pt)
        if reduced[-1] != path[-1]:
            reduced.append(path[-1])
        return reduced

    def clear_cache(self):
        self._mask_cache = None
        self._bounds_cache = None