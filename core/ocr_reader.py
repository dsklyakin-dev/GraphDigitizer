"""
Распознавание цифр и подписей осей на графиках через Tesseract.
v2.0 — встроенный Tesseract, работает в .exe и Python
"""

import os
import sys
import re
import cv2
import numpy as np


# ============================================================
# ПОИСК РЕСУРСОВ (работает и в .exe, и в Python)
# ============================================================

def resource_path(relative_path):
    """
    Возвращает абсолютный путь к ресурсу.
    - В .exe: временная папка _MEIPASS, куда PyInstaller распаковал файлы.
    - В Python: текущая папка проекта.
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)


# ============================================================
# ИНИЦИАЛИЗАЦИЯ TESSERACT
# ============================================================

try:
    import pytesseract

    # Путь к tesseract.exe внутри проекта / .exe
    TESSERACT_EXE = resource_path('tesseract/tesseract.exe')
    TESSDATA_DIR = resource_path('tesseract/tessdata')

    print(f'[OCR] TESSERACT_EXE = {TESSERACT_EXE}')
    print(f'[OCR] TESSERACT_EXE exists = {os.path.exists(TESSERACT_EXE)}')
    print(f'[OCR] TESSDATA_DIR = {TESSDATA_DIR}')
    print(f'[OCR] TESSDATA_DIR exists = {os.path.exists(TESSDATA_DIR)}')

    if os.path.exists(TESSERACT_EXE):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

        # Переменная окружения — чтобы Tesseract нашёл языковые данные
        if os.path.exists(TESSDATA_DIR):
            os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR

        HAS_TESSERACT = True
    else:
        # Fallback: пробуем системный Tesseract (если установлен)
        print('[OCR] Встроенный Tesseract не найден, пробуем системный...')
        HAS_TESSERACT = True

except ImportError:
    print('[OCR] pytesseract не установлен')
    HAS_TESSERACT = False


# ============================================================
# OCR READER
# ============================================================

class OCRReader:
    def __init__(self, image_bgr):
        self.image = image_bgr
        self.gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        self.h, self.w = self.gray.shape

    def _preprocess(self, roi):
        """Бинаризация + шумоподавление для OCR."""
        # Апскейл — Tesseract лучше читает крупные цифры
        roi = cv2.resize(roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        # Убираем шум
        roi = cv2.GaussianBlur(roi, (3, 3), 0)
        # Бинаризация Otsu
        _, binary = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def _read_near_point(self, point, direction='bottom', radius=80):
        """
        Читает текст рядом с точкой.
        ВСЕГДА возвращает кортеж (numbers: list, had_dot: bool).
        """
        x, y = int(point[0]), int(point[1])

        if direction == 'bottom':
            roi = self.gray[max(0, y):min(self.h, y + radius),
                  max(0, x - radius):min(self.w, x + radius * 2)]
        elif direction == 'left':
            # Слева от origin, чуть выше и ниже — подписи Y
            roi = self.gray[max(0, y - 40):min(self.h, y + 30),
                           max(0, x - 100):max(0, x - 5)]
        elif direction == 'bottom-left':
            # Ниже origin — подписи X
            roi = self.gray[min(self.h, y + 5):min(self.h, y + radius),
                           max(0, x - radius * 2):x]
        elif direction == 'right':
            roi = self.gray[max(0, y - radius):min(self.h, y + radius),
                           x:min(self.w, x + radius)]
        elif direction == 'top':
            roi = self.gray[max(0, y - radius):y,
                           max(0, x - radius):min(self.w, x + radius)]
        else:
            return [], False

        if roi.size == 0:
            return [], False

        processed = self._preprocess(roi)

        # Разрешаем точку и запятую
        config = '--psm 6 -c tessedit_char_whitelist=0123456789.,-'
        try:
            text = pytesseract.image_to_string(processed, config=config)
        except Exception as e:
            print(f'[OCR {direction}] ошибка Tesseract: {e}')
            return [], False

        print(f'[OCR {direction}] сырой текст: {text!r}')

        text_norm = text.replace(',', '.')
        had_dot = ('.' in text_norm) or (',' in text)

        numbers_str = re.findall(r'-?\d+\.?\d*', text_norm)
        result = []
        for n in numbers_str:
            try:
                result.append(float(n))
            except ValueError:
                pass

        print(f'[OCR {direction}] числа: {result}, точка была: {had_dot}')
        return result, had_dot

    def _filter_fragments(self, values):
        """
        Фильтрует "обрывки": если число A является подстрокой другого числа B
        (например, '1' ⊂ '15') или сильно меньше B (в 3+ раза),
        то A отбрасывается.
        """
        cleaned = [v for v in values if abs(v) >= 0.1]
        if len(cleaned) <= 1:
            return cleaned

        # Сортируем по убыванию модуля
        sorted_vals = sorted(cleaned, key=lambda x: -abs(x))

        result = []
        for v in sorted_vals:
            is_fragment = False
            for other in result:
                v_str = str(int(abs(v)))
                other_str = str(int(abs(other)))

                # v — подстрока other
                if v_str in other_str:
                    is_fragment = True
                    break

                # v сильно меньше other
                if abs(v) * 3 < abs(other):
                    is_fragment = True
                    break

            if not is_fragment:
                result.append(v)

        return result

    def read_axis_labels(self, origin, x_end, y_end):
        """
        Читает подписи у осей.
        Возвращает dict: {'x0': ..., 'y0': ..., 'x1': ..., 'y1': ...}
        """
        if not HAS_TESSERACT:
            return None

        result = {}

        # ===== X0 =====
        x0_candidates = []
        r, _ = self._read_near_point(origin, direction='bottom')
        if r:
            x0_candidates.extend(r)

        x0_cleaned = self._filter_fragments(x0_candidates)
        if x0_cleaned:
            neg = [v for v in x0_cleaned if v < 0]
            if neg:
                result['x0'] = max(neg)
            else:
                result['x0'] = min(x0_cleaned)

        # ===== Y0 =====
        y0_candidates = []
        r, _ = self._read_near_point(origin, direction='left')
        if r:
            y0_candidates.extend(r)

        y0_cleaned = self._filter_fragments(y0_candidates)
        if y0_cleaned:
            pos = [v for v in y0_cleaned if v > 0]
            if pos:
                result['y0'] = min(pos)
            else:
                result['y0'] = min(y0_cleaned)

        # ===== X1 =====
        x1_candidates = []
        r, _ = self._read_near_point(x_end, direction='bottom')
        if r:
            x1_candidates.extend(r)
        r, _ = self._read_near_point(x_end, direction='right')
        if r:
            x1_candidates.extend(r)

        x1_cleaned = self._filter_fragments(x1_candidates)
        if x1_cleaned:
            result['x1'] = max(x1_cleaned)

        # ===== Y1 =====
        y1_candidates = []
        r, _ = self._read_near_point(y_end, direction='left')
        if r:
            y1_candidates.extend(r)
        r, _ = self._read_near_point(y_end, direction='top')
        if r:
            y1_candidates.extend(r)

        y1_cleaned = self._filter_fragments(y1_candidates)
        if y1_cleaned:
            result['y1'] = max(y1_cleaned)

        return result


# ============================================================
# УТИЛИТА
# ============================================================

def is_available():
    """Проверяет, доступен ли OCR (pytesseract + Tesseract)."""
    if not HAS_TESSERACT:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception as e:
        print(f'[OCR] Tesseract не отвечает: {e}')
        return False