"""
Всплывающее уведомление — скруглённая плашка с эффектом лёгкости.
v3.0
"""

import customtkinter as ctk
from config.settings import COLORS, FONTS


class Toast:
    def __init__(self, parent_window):
        self.parent = parent_window
        self._toplevel = None
        self._after_id = None

    def show(self, text, duration=3.5, color='info', icon=''):
        self.hide()

        # Цвета — берём из палитры, но ДЕЛАЕМ ЧУТЬ БОЛЕЕ ПРИГЛУШЁННЫМИ
        # для эффекта "полупрозрачности".
        base_colors = {
            'info': COLORS['primary'],
            'success': COLORS['success'],
            'warning': COLORS['warning'],
            'danger': COLORS['danger'],
        }
        base = base_colors.get(color, COLORS['primary'])

        # Приглушаем цвет — смешиваем с фоном окна
        bg_main = COLORS['bg_main']
        bg = self._blend(base, bg_main, 0.15)  # 15% фона

        # === Toplevel ===
        self._toplevel = ctk.CTkToplevel(self.parent)
        self._toplevel.overrideredirect(True)
        self._toplevel.attributes('-topmost', True)

        # Полупрозрачность
        try:
            self._toplevel.attributes('-alpha', 0.92)
        except Exception:
            pass

        # Цвет "прозрачного" фона — магический розовый
        # Всё, что за пределами скруглённого фрейма, станет прозрачным
        try:
            self._toplevel.attributes('-transparentcolor', '#FF00FF')
            self._toplevel.configure(fg_color='#FF00FF')
        except Exception:
            # Не Windows или не поддерживается — просто фон окна
            self._toplevel.configure(fg_color=COLORS['bg_main'])

        # Внутренний скруглённый фрейм
        frame = ctk.CTkFrame(
            self._toplevel,
            fg_color=bg,
            corner_radius=18,
        )
        frame.pack(padx=0, pady=0, fill='both', expand=True)

        # Layout
        inner = ctk.CTkFrame(frame, fg_color='transparent')
        inner.pack(padx=22, pady=14)

        if icon:
            ctk.CTkLabel(
                inner, text=icon,
                font=('Segoe UI', 18),
                text_color='white',
            ).pack(side='left', padx=(0, 10))

        self._label = ctk.CTkLabel(
            inner, text=text,
            font=('Segoe UI', 13, 'bold'),
            text_color='white',
            justify='left',
            wraplength=360,
        )
        self._label.pack(side='left')

        # Позиционирование
        self._toplevel.update_idletasks()
        self._position_centered()

        if duration > 0:
            self._after_id = self.parent.after(
                int(duration * 1000), self.hide
            )

    def _position_centered(self):
        try:
            self.parent.update_idletasks()

            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()

            self._toplevel.update_idletasks()
            tw = self._toplevel.winfo_width()
            th = self._toplevel.winfo_height()

            # По центру
            x = px + (pw - tw) // 2
            y = py + (ph - th) // 2

            self._toplevel.geometry(f'+{x}+{y}')
        except Exception as e:
            print(f'[toast position error] {e}')

    def _blend(self, color1, color2, ratio):
        """
        Смешивает два hex-цвета.
        ratio=0 → color1, ratio=1 → color2.
        """
        try:
            r1 = int(color1[1:3], 16)
            g1 = int(color1[3:5], 16)
            b1 = int(color1[5:7], 16)
            r2 = int(color2[1:3], 16)
            g2 = int(color2[3:5], 16)
            b2 = int(color2[5:7], 16)

            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)

            return f'#{r:02x}{g:02x}{b:02x}'
        except Exception:
            return color1

    def hide(self):
        if self._after_id is not None:
            try:
                self.parent.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

        if self._toplevel is not None:
            try:
                self._toplevel.destroy()
            except Exception:
                pass
            self._toplevel = None