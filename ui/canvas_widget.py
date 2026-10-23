"""
Canvas для отображения графика. tkinter.Canvas + PIL — быстрый рендер.
Поддерживает панорамирование, зум, overlay-элементы.
"""

import tkinter as tk
from PIL import Image, ImageTk
from config.settings import COLORS


class GraphCanvas(tk.Frame):
    def __init__(self, parent, on_click=None, on_drag=None, on_release=None,
                 on_motion=None, on_right_click=None, on_zoom_change=None):
        super().__init__(parent, bg=COLORS['bg_canvas'], highlightthickness=0)

        self.canvas = tk.Canvas(
            self, bg=COLORS['bg_canvas'],
            highlightthickness=0, cursor='crosshair'
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Коллбэки
        self.on_click = on_click
        self.on_drag = on_drag
        self.on_release = on_release
        self.on_motion = on_motion
        self.on_right_click = on_right_click
        self.on_zoom_change = on_zoom_change
        self._calib_marks_callback = None

        # Изображение
        self.pil_image = None
        self.photo_image = None
        self.image_id = None

        # Трансформация
        self.scale = 1.0
        self.base_scale = 1.0
        self.user_zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Панорамирование
        self._pan_start = None
        self._pan_offset_start = None

        # Ctrl
        self._ctrl_pressed = False

        # Размеры canvas
        self._canvas_w = 0
        self._canvas_h = 0

        # Кэш resized-изображений
        self._resized_cache = {}

        # Хранилище overlay-элементов в координатах изображения
        # Каждый элемент: dict(type='point'|'line'|'rect'|'circle', ...)
        self._overlay_data = []

        # Привязки
        self.canvas.bind('<Configure>', self._on_resize)
        self.canvas.bind('<Button-1>', self._on_left_press)
        self.canvas.bind('<Button-3>', self._on_right_press)
        self.canvas.bind('<B1-Motion>', self._on_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_release)
        self.canvas.bind('<Motion>', self._on_motion)
        self.canvas.bind('<MouseWheel>', self._on_wheel)
        self.canvas.bind('<Enter>', lambda e: self.focus_set())

        self.canvas.bind('<KeyPress-Control_L>', lambda e: self._set_ctrl(True))
        self.canvas.bind('<KeyRelease-Control_L>', lambda e: self._set_ctrl(False))
        self.canvas.bind('<KeyPress-Control_R>', lambda e: self._set_ctrl(True))
        self.canvas.bind('<KeyRelease-Control_R>', lambda e: self._set_ctrl(False))

    def _set_ctrl(self, pressed):
        self._ctrl_pressed = pressed

    def set_calib_marks_callback(self, callback):
        """Коллбэк для перерисовки меток калибровки после render."""
        self._calib_marks_callback = callback

    # ============================================================
    # РАБОТА С ИЗОБРАЖЕНИЕМ
    # ============================================================

    def set_image(self, pil_image):
        self.pil_image = pil_image
        self.user_zoom = 1.0
        self._resized_cache.clear()
        self._fit_to_canvas()

    def clear_image(self):
        self.pil_image = None
        self.photo_image = None
        self.canvas.delete('all')
        self._resized_cache.clear()
        self._overlay_data.clear()

    def _on_resize(self, event):
        self._canvas_w = event.width
        self._canvas_h = event.height
        if self.pil_image is None:
            return
        self._fit_to_canvas()

    def _fit_to_canvas(self):
        if self.pil_image is None:
            return
        if self._canvas_w < 10 or self._canvas_h < 10:
            return

        img_w, img_h = self.pil_image.size
        scale_w = (self._canvas_w - 20) / img_w
        scale_h = (self._canvas_h - 20) / img_h
        self.base_scale = min(scale_w, scale_h)
        self.scale = self.base_scale * self.user_zoom

        new_w = int(img_w * self.scale)
        new_h = int(img_h * self.scale)

        self.offset_x = (self._canvas_w - new_w) // 2
        self.offset_y = (self._canvas_h - new_h) // 2

        self._render()

    def _render(self):
        """Перерисовывает изображение + overlay + метки калибровки."""
        if self.pil_image is None:
            return

        new_w = int(self.pil_image.size[0] * self.scale)
        new_h = int(self.pil_image.size[1] * self.scale)

        if new_w < 1 or new_h < 1:
            return

        # Кэш
        cache_key = (new_w, new_h)
        if cache_key in self._resized_cache:
            resized = self._resized_cache[cache_key]
        else:
            resized = self.pil_image.resize((new_w, new_h), Image.LANCZOS)
            if len(self._resized_cache) > 3:
                self._resized_cache.clear()
            self._resized_cache[cache_key] = resized

        self.photo_image = ImageTk.PhotoImage(resized)

        # Удаляем изображение и overlay
        self.canvas.delete('image')
        self.canvas.delete('overlay')
        self.canvas.delete('calib_marks')

        self.image_id = self.canvas.create_image(
            self.offset_x, self.offset_y,
            anchor='nw', image=self.photo_image, tags='image'
        )

        # Перерисовываем все overlay-элементы в новых координатах
        for item in self._overlay_data:
            self._render_overlay_item(item)

        # Перерисовываем метки калибровки через коллбэк
        if self._calib_marks_callback:
            self._calib_marks_callback()

        if self.on_zoom_change:
            self.on_zoom_change(self.scale, self.user_zoom)

    # ============================================================
    # ЗУМ
    # ============================================================

    def _on_wheel(self, event):
        if not self._ctrl_pressed:
            return

        old_scale = self.scale

        if event.delta > 0:
            self.user_zoom *= 1.15
        else:
            self.user_zoom /= 1.15

        self.user_zoom = max(0.1, min(20.0, self.user_zoom))
        self.scale = self.base_scale * self.user_zoom

        img_x = (event.x - self.offset_x) / old_scale
        img_y = (event.y - self.offset_y) / old_scale

        self.offset_x = int(event.x - img_x * self.scale)
        self.offset_y = int(event.y - img_y * self.scale)

        self._render()

    def reset_zoom(self):
        self.user_zoom = 1.0
        self._fit_to_canvas()

    # ============================================================
    # СОБЫТИЯ МЫШИ
    # ============================================================

    def _on_left_press(self, event):
        consumed = False
        if self.on_click:
            img_x, img_y = self.canvas_to_img(event.x, event.y)
            consumed = self.on_click(event.x, event.y, img_x, img_y)

        if not consumed:
            self._pan_start = (event.x, event.y)
            self._pan_offset_start = (self.offset_x, self.offset_y)
            self.canvas.configure(cursor='fleur')

    def _on_drag(self, event):
        if self._pan_start is not None:
            dx = event.x - self._pan_start[0]
            dy = event.y - self._pan_start[1]
            self.offset_x = self._pan_offset_start[0] + dx
            self.offset_y = self._pan_offset_start[1] + dy
            self._render()
        elif self.on_drag:
            img_x, img_y = self.canvas_to_img(event.x, event.y)
            self.on_drag(event.x, event.y, img_x, img_y)

    def _on_release(self, event):
        was_panning = self._pan_start is not None
        self._pan_start = None
        self._pan_offset_start = None
        self.canvas.configure(cursor='crosshair')

        if not was_panning and self.on_release:
            img_x, img_y = self.canvas_to_img(event.x, event.y)
            self.on_release(event.x, event.y, img_x, img_y)

    def _on_right_press(self, event):
        if self.on_right_click:
            self.on_right_click(event.x, event.y)

    def _on_motion(self, event):
        if self.on_motion:
            img_x, img_y = self.canvas_to_img(event.x, event.y)
            self.on_motion(event.x, event.y, img_x, img_y)

    # ============================================================
    # КООРДИНАТЫ
    # ============================================================

    def canvas_to_img(self, cx, cy):
        if self.scale == 0:
            return 0, 0
        img_x = int((cx - self.offset_x) / self.scale)
        img_y = int((cy - self.offset_y) / self.scale)
        return img_x, img_y

    def img_to_canvas(self, img_x, img_y):
        cx = int(img_x * self.scale + self.offset_x)
        cy = int(img_y * self.scale + self.offset_y)
        return cx, cy

    # ============================================================
    # OVERLAY — РИСОВАНИЕ
    # ============================================================

    def clear_overlay(self):
        self._overlay_data.clear()
        self.canvas.delete('overlay')
        self.canvas.delete('calib_marks')

    def draw_point(self, img_x, img_y, color='red', size=5, outline='white',
                   tag='overlay', shape='circle'):
        item = {
            'type': 'point', 'x': img_x, 'y': img_y,
            'color': color, 'size': size, 'outline': outline,
            'shape': shape, 'tag': tag,
        }
        self._overlay_data.append(item)
        self._render_overlay_item(item)

    def draw_line(self, x1, y1, x2, y2, color='red', width=2, dash=None, tag='overlay'):
        item = {
            'type': 'line', 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'color': color, 'width': width, 'dash': dash, 'tag': tag,
        }
        self._overlay_data.append(item)
        self._render_overlay_item(item)

    def draw_rect(self, x1, y1, x2, y2, color='red', width=2, dash=None, tag='overlay'):
        item = {
            'type': 'rect', 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'color': color, 'width': width, 'dash': dash, 'tag': tag,
        }
        self._overlay_data.append(item)
        self._render_overlay_item(item)

    def draw_circle(self, img_x, img_y, radius_img, color='red', fill='', tag='overlay'):
        item = {
            'type': 'circle', 'x': img_x, 'y': img_y, 'r': radius_img,
            'color': color, 'fill': fill, 'tag': tag,
        }
        self._overlay_data.append(item)
        self._render_overlay_item(item)

    def _render_overlay_item(self, item):
        """Рисует один overlay-элемент."""
        t = item['type']
        tag = item.get('tag', 'overlay')

        if t == 'point':
            cx, cy = self.img_to_canvas(item['x'], item['y'])
            size = item['size']
            color = item['color']
            outline = item.get('outline', 'white')

            if item.get('shape') == 'cross':
                w = 3
                self.canvas.create_line(cx - size, cy - size, cx + size, cy + size,
                                        fill=color, width=w, tags=tag)
                self.canvas.create_line(cx - size, cy + size, cx + size, cy - size,
                                        fill=color, width=w, tags=tag)
            else:
                self.canvas.create_oval(
                    cx - size, cy - size, cx + size, cy + size,
                    fill=color, outline=outline, width=2, tags=tag
                )

        elif t == 'line':
            cx1, cy1 = self.img_to_canvas(item['x1'], item['y1'])
            cx2, cy2 = self.img_to_canvas(item['x2'], item['y2'])
            self.canvas.create_line(
                cx1, cy1, cx2, cy2,
                fill=item['color'], width=item['width'],
                dash=item.get('dash'), tags=tag
            )

        elif t == 'rect':
            cx1, cy1 = self.img_to_canvas(item['x1'], item['y1'])
            cx2, cy2 = self.img_to_canvas(item['x2'], item['y2'])
            self.canvas.create_rectangle(
                cx1, cy1, cx2, cy2,
                outline=item['color'], width=item['width'],
                dash=item.get('dash'), tags=tag
            )

        elif t == 'circle':
            cx, cy = self.img_to_canvas(item['x'], item['y'])
            r = item['r'] * self.scale
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=item['color'], fill=item.get('fill', ''),
                width=2, tags=tag
            )

    # ============================================================
    # МЕТКИ КАЛИБРОВКИ (рисуются поверх всего)
    # ============================================================

    def draw_calibration_marks(self, calibrator):
        """Рисует крестики калибровки. Вызывается из _render."""
        self.canvas.delete('calib_marks')

        if not calibrator.points:
            return

        marks = {
            'origin': ('#F59E0B', 'O'),
            'x_max': ('#3B82F6', 'X'),
            'y_max': ('#10B981', 'Y'),
        }

        for name, (color, label) in marks.items():
            if name not in calibrator.points:
                continue

            px, py = calibrator.points[name]['pixel']
            cx, cy = self.img_to_canvas(px, py)

            size = 12
            # Крестик
            self.canvas.create_line(cx - size, cy, cx + size, cy,
                                    fill=color, width=3, tags='calib_marks')
            self.canvas.create_line(cx, cy - size, cx, cy + size,
                                    fill=color, width=3, tags='calib_marks')
            # Кружок
            self.canvas.create_oval(cx - 8, cy - 8, cx + 8, cy + 8,
                                    outline=color, width=2, tags='calib_marks')
            # Подпись
            vx, vy = calibrator.points[name]['value']
            text = f'{label} ({vx:g}, {vy:g})'
            self.canvas.create_text(cx + 18, cy - 18, text=text,
                                    fill=color, font=('Segoe UI', 11, 'bold'),
                                    anchor='w', tags='calib_marks')

