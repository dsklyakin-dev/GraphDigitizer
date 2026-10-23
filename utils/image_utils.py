"""
Утилиты для работы с изображениями.
"""

import cv2
import numpy as np
from PIL import Image


def cv2_to_pil(image_bgr):
    """OpenCV BGR -> PIL RGB"""
    if image_bgr is None:
        return None
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def load_image_unicode(path):
    """Загрузка изображения с поддержкой русских путей"""
    with open(path, 'rb') as f:
        data = np.frombuffer(f.read(), np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def fit_image_to_canvas(pil_image, canvas_width, canvas_height):
    """Вписывает изображение в canvas с сохранением пропорций.
    Возвращает (resized_pil, scale, offset_x, offset_y)."""
    if pil_image is None:
        return None, 1.0, 0, 0

    img_w, img_h = pil_image.size
    scale = min(canvas_width / img_w, canvas_height / img_h)

    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    resized = pil_image.resize((new_w, new_h), Image.LANCZOS)

    offset_x = (canvas_width - new_w) // 2
    offset_y = (canvas_height - new_h) // 2

    return resized, scale, offset_x, offset_y


def canvas_to_image_coords(canvas_x, canvas_y, scale, offset_x, offset_y):
    """Canvas координаты -> координаты изображения"""
    if scale == 0:
        return 0, 0
    img_x = (canvas_x - offset_x) / scale
    img_y = (canvas_y - offset_y) / scale
    return int(img_x), int(img_y)


def image_to_canvas_coords(img_x, img_y, scale, offset_x, offset_y):
    """Координаты изображения -> canvas"""
    canvas_x = img_x * scale + offset_x
    canvas_y = img_y * scale + offset_y
    return int(canvas_x), int(canvas_y)