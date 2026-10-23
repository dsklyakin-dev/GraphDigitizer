"""
Удаление сетки через FFT для лучшего поиска кривых.
"""

import cv2
import numpy as np


class GridRemover:
    def __init__(self, image_bgr):
        self.gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        self._cache = None

    def remove_grid_fft(self):
        """Удаляет периодическую сетку через FFT."""
        if self._cache is not None:
            return self._cache

        f = np.fft.fft2(self.gray.astype(np.float32))
        fshift = np.fft.fftshift(f)
        rows, cols = self.gray.shape
        crow, ccol = rows // 2, cols // 2

        mask = np.ones((rows, cols), np.float32)
        # Гасим центральные частоты (горизонтальные и вертикальные линии сетки)
        mask[crow - 3:crow + 3, :] = 0.08
        mask[:, ccol - 3:ccol + 3] = 0.08
        cv2.circle(mask, (ccol, crow), 6, 0.08, -1)

        fshift *= mask
        img_back = np.abs(np.fft.ifft2(np.fft.ifftshift(fshift)))
        img_back = ((img_back - img_back.min()) / (img_back.max() - img_back.min()) * 255).astype(np.uint8)

        # Усиление контраста тёмных линий
        img_back = img_back.astype(np.float32)
        img_back[img_back < 90] *= 0.6

        result = cv2.cvtColor(np.clip(img_back, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        self._cache = result
        return result