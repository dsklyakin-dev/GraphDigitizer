"""
Надёжное выравнивание изображения графика.

Метод: перебор углов + анализ проекций.
Для каждого пробного угла:
  - поворачиваем картинку,
  - считаем профиль по X и по Y (сумма яркостей),
  - измеряем "резкость" профиля (дисперсию градиента).

Выровненное изображение даёт максимальную резкость,
потому что линии сетки совпадают в одну строку/столбец.

v2.0
"""

import cv2
import numpy as np


def _sharpness(profile):
    """
    Мера "резкости" профиля.
    Чем больше пиков, тем выше значение.
    Используем сумму квадратов первой производной.
    """
    p = profile.astype(np.float32)
    p = p - p.mean()
    grad = np.diff(p)
    return float(np.sum(grad * grad))


def _rotate_gray(gray, angle):
    """Поворачивает gray-картинку на угол, расширяя границы белым."""
    h, w = gray.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    M[0, 2] += (new_w / 2) - w / 2
    M[1, 2] += (new_h / 2) - h / 2

    return cv2.warpAffine(
        gray, M, (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    ), M, (new_w, new_h)


def find_best_angle(image_bgr,
                    angle_range=10.0,
                    angle_step=0.25,
                    inner_margin=30):
    """
    Ищет угол, при котором картинка максимально "выровнена".

    Параметры:
      angle_range: диапазон поиска в градусах (от -angle_range до +angle_range)
      angle_step:  шаг перебора
      inner_margin: сколько пикселей отступить от края (там белый фон
                    после поворота, его не надо учитывать)

    Возвращает:
      best_angle (float) — угол, на который нужно повернуть.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # Предобработка: инвертируем, чтобы линии были яркими на тёмном фоне
    gray_inv = 255 - gray

    best_angle = 0.0
    best_score = -1.0

    # Пробегаем углы
    angles = np.arange(-angle_range, angle_range + angle_step / 2, angle_step)

    for angle in angles:
        rot, _, _ = _rotate_gray(gray_inv, angle)

        # Обрезаем по inner_margin
        m = inner_margin
        if rot.shape[0] < 2 * m or rot.shape[1] < 2 * m:
            continue
        inner = rot[m:-m, m:-m]

        # Профили: сумма по строкам (вертикальные линии → пики)
        #          и сумма по столбцам (горизонтальные линии → пики)
        prof_x = inner.sum(axis=0)  # по столбцам — для вертикалей
        prof_y = inner.sum(axis=1)  # по строкам — для горизонталей

        score = _sharpness(prof_x) + _sharpness(prof_y)

        if score > best_score:
            best_score = score
            best_angle = float(angle)

    return best_angle


def auto_align(image_bgr,
               angle_range=10.0,
               angle_step=0.25,
               min_angle=0.15):
    """
    Выравнивает картинку.

    Возвращает (result_image, angle) или (None, None), если угол найден,
    но он слишком мал (< min_angle).
    """
    angle = find_best_angle(
        image_bgr,
        angle_range=angle_range,
        angle_step=angle_step,
    )

    if abs(angle) < min_angle:
        # Картинка уже ровная
        return None, None

    h, w = image_bgr.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    M[0, 2] += (new_w / 2) - w / 2
    M[1, 2] += (new_h / 2) - h / 2

    result = cv2.warpAffine(
        image_bgr, M, (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )

    return result, angle