"""
Загрузчик изображений.
"""

import cv2
import numpy as np


class ImageLoader:
    def __init__(self):
        self.original = None
        self.current = None
        self.path = None

    def load(self, path):
        try:
            with open(path, 'rb') as f:
                data = np.frombuffer(f.read(), np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if img is None:
                return False
            self.original = img.copy()
            self.current = img.copy()
            self.path = path
            return True
        except Exception as e:
            print(f'Ошибка загрузки: {e}')
            return False

    def reset(self):
        if self.original is not None:
            self.current = self.original.copy()

    @property
    def shape(self):
        if self.current is None:
            return None
        return self.current.shape

    def is_loaded(self):
        return self.current is not None