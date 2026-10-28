import cv2
import numpy as np
import os
import math


class PredictiveDetector:
    def __init__(self, image_bgr, calibrator):
        self.image = image_bgr.copy()
        self.calibrator = calibrator
        self.height, self.width = image_bgr.shape[:2]

        os.makedirs("debug", exist_ok=True)

        # 1. Переводим в оттенки серого
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        # 2. Улучшаем контраст (растягиваем гистограмму)
        # Это делает тусклые линии более чёрными, а фон — более белым
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

        # 3. Легкое размытие для удаления шума
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # 4. Фиксированный порог (150 — хорошо для большинства картинок после нормализации)
        _, self.binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

        # 5. Убираем сетку (эрозия + дилатация)
        kernel = np.ones((2, 2), np.uint8)
        self.thick_lines = cv2.erode(self.binary, kernel, iterations=1)
        self.thick_lines = cv2.dilate(self.thick_lines, kernel, iterations=1)

        cv2.imwrite("debug/1_thick_lines.png", self.thick_lines)

    def _scan_direction(self, direction, step_pixels, ignore_mask):
        """Сканирует изображение в заданном направлении.
        direction: 'lr' (слева-направо), 'rl' (справа-налево),
                   'tb' (сверху-вниз), 'bt' (снизу-вверх).
        """
        px_origin = self.calibrator.points['origin']['pixel']
        px_xmax = self.calibrator.points['x_max']['pixel']
        px_ymax = self.calibrator.points['y_max']['pixel']

        x_min, x_max = int(px_origin[0]), int(px_xmax[0])
        y_min, y_max = int(px_ymax[1]), int(px_origin[1])

        cleaned = np.zeros_like(self.thick_lines)
        cleaned[y_min:y_max, x_min:x_max] = self.thick_lines[y_min:y_max, x_min:x_max]

        # Убираем оси (5 пикселей)
        axis_thickness = 5
        cleaned[y_min:y_max, x_min:x_min + axis_thickness] = 0
        cleaned[y_max - axis_thickness:y_max, x_min:x_max] = 0
        cleaned[y_min:y_min + axis_thickness, x_min:x_max] = 0
        cleaned[y_min:y_max, x_max - axis_thickness:x_max] = 0

        # Разрыв в точке схода
        gap_x_end = x_min + 25
        gap_y_start = int(px_origin[1]) - 15
        gap_y_end = int(px_origin[1]) + 15
        cleaned[gap_y_start:gap_y_end, x_min:gap_x_end] = 0

        # === УДАЛЯЕМ ТЕКСТ (маленькие объекты) ===
        # Находим все контуры на изображении
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Создаем маску для удаления
        text_mask = np.zeros_like(cleaned)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            x, y, w, h = cv2.boundingRect(cnt)

            # Если объект маленький (буква или цифра) — удаляем его
            # Кривые обычно длинные (w > 50 или h > 50)
            if w < 30 and h < 20:
                cv2.drawContours(text_mask, [cnt], -1, 255, -1)

        # Вычитаем текст из изображения
        cleaned = cv2.subtract(cleaned, text_mask)
        # =========================================

        # Маска пунктира
        if ignore_mask is not None:
            ignore_inv = cv2.bitwise_not(ignore_mask)
            cleaned = cv2.bitwise_and(cleaned, ignore_inv)

        # Определяем порядок обхода
        if direction == 'lr':  # слева направо (по X)
            x_range = range(x_min + axis_thickness + 5, x_max - axis_thickness - 5, step_pixels)
            scan_by_x = True
        elif direction == 'rl':  # справа налево
            x_range = range(x_max - axis_thickness - 5, x_min + axis_thickness + 5, -step_pixels)
            scan_by_x = True
        elif direction == 'tb':  # сверху вниз (по Y)
            x_range = range(y_min + axis_thickness + 5, y_max - axis_thickness - 5, step_pixels)
            scan_by_x = False
        elif direction == 'bt':  # снизу вверх
            x_range = range(y_max - axis_thickness - 5, y_min + axis_thickness + 5, -step_pixels)
            scan_by_x = False
        else:
            return {}

        curves = {}
        curve_id = 1
        debug_vis = self.image.copy()
        curve_trends = {}

        for coord in x_range:
            if scan_by_x:
                col = cleaned[y_min:y_max, coord]
                base_coord = y_min
            else:
                col = cleaned[coord, x_min:x_max]
                base_coord = x_min

            if np.sum(col) == 0:
                continue

            clusters = []
            in_cluster = False
            start = 0

            for i, val in enumerate(col):
                if val > 0 and not in_cluster:
                    in_cluster = True
                    start = i
                elif val == 0 and in_cluster:
                    in_cluster = False
                    if 2 < (i - start) < 30:
                        clusters.append((start + base_coord, i + base_coord))
            if in_cluster:
                if 2 < (len(col) - start) < 30:
                    clusters.append((start + base_coord, len(col) + base_coord))

            if not clusters:
                continue

            clusters.sort(key=lambda c: c[0])
            used_clusters = set()

            for cid, pts in curves.items():
                trend = curve_trends.get(cid, 0)
                if scan_by_x:
                    last_vx, last_vy = pts[-1]
                else:
                    last_vy, last_vx = pts[-1]

                last_px, last_py = self.calibrator.val_to_px(last_vx, last_vy)
                expected = (last_py + trend) if scan_by_x else (last_px + trend)

                best_cluster_idx = None
                min_dist = 25

                for idx, (c_start, c_end) in enumerate(clusters):
                    if idx in used_clusters:
                        continue
                    cc = (c_start + c_end) // 2
                    dist = abs(cc - expected)

                    # ПРОВЕРКА: расстояние не должно быть больше step_pixels * 2
                    # (то есть алгоритм не должен прыгать слишком далеко)
                    if dist > step_pixels * 2:
                        continue

                    if dist < min_dist:
                        min_dist = dist
                        best_cluster_idx = idx

                if best_cluster_idx is not None:
                    c_start, c_end = clusters[best_cluster_idx]
                    cc = (c_start + c_end) // 2
                    used_clusters.add(best_cluster_idx)

                    if scan_by_x:
                        vx, vy = self.calibrator.px_to_val(coord, cc)
                    else:
                        vx, vy = self.calibrator.px_to_val(cc, coord)

                    curves[cid].append((vx, vy))
                    new_trend = cc - expected
                    curve_trends[cid] = 0.8 * trend + 0.2 * new_trend

                    if scan_by_x:
                        cv2.circle(debug_vis, (coord, cc), 2, (0, 0, 255), -1)
                    else:
                        cv2.circle(debug_vis, (cc, coord), 2, (0, 0, 255), -1)

            for idx, (c_start, c_end) in enumerate(clusters):
                if idx not in used_clusters:
                    cc = (c_start + c_end) // 2
                    if scan_by_x:
                        vx, vy = self.calibrator.px_to_val(coord, cc)
                    else:
                        vx, vy = self.calibrator.px_to_val(cc, coord)
                    curves[curve_id] = [(vx, vy)]
                    curve_trends[curve_id] = 0
                    curve_id += 1

        # Финальный фильтр
        final_curves = {}
        idx = 1
        for cid, pts in curves.items():
            if len(pts) > 15:
                final_curves[idx] = pts
                idx += 1

        return final_curves

    def find_all_curves(self, step_pixels=5, ignore_mask=None):
        """Ансамблевый метод: сканирует в 4 направлениях и выбирает лучший."""
        directions = ['lr', 'rl', 'tb', 'bt']
        results = {}

        for d in directions:
            print(f"[Ensemble] Сканирование {d}...")
            curves = self._scan_direction(d, step_pixels, ignore_mask)
            total_points = sum(len(pts) for pts in curves.values())
            results[d] = {
                'curves': curves,
                'num_curves': len(curves),
                'total_points': total_points
            }
            print(f"[Ensemble] {d}: {len(curves)} кривых, {total_points} точек")

        # Выбираем направление с максимумом кривых (при равенстве — с максимумом точек)
        best_direction = max(results, key=lambda d: (results[d]['num_curves'], results[d]['total_points']))
        print(f"[Ensemble] Лучшее направление: {best_direction}")

        # === ФИЛЬТР ПЛОТНОСТИ (убираем случайные точки) ===
        best_curves = results[best_direction]['curves']
        filtered_curves = {}
        idx = 1

        for cid, pts in best_curves.items():
            if len(pts) < 10:
                continue

            good_points = []
            for i, (vx, vy) in enumerate(pts):
                px, py = self.calibrator.val_to_px(vx, vy)

                # Считаем соседей в радиусе 15 пикселей
                neighbors = 0
                for j, (vx2, vy2) in enumerate(pts):
                    if i == j:
                        continue
                    px2, py2 = self.calibrator.val_to_px(vx2, vy2)
                    dist = math.hypot(px2 - px, py2 - py)
                    if dist < 25:
                        neighbors += 1

                # Оставляем точку, если у неё есть хотя бы 2 соседа
                if neighbors >= 2:
                    good_points.append((vx, vy))

            # Если после фильтрации осталось достаточно точек — сохраняем
            if len(good_points) > 15:
                filtered_curves[idx] = good_points
                idx += 1

        print(f"--- После фильтра плотности: {len(filtered_curves)} кривых ---")
        return filtered_curves