"""
Диалоги калибровки.
v7.1 — с локализацией RU/EN
"""

import customtkinter as ctk
from config.settings import COLORS, FONTS
from core.i18n import t


class CalibrationDialog(ctk.CTkToplevel):
    """Диалог ввода значений осей для калибровки."""

    def __init__(self, parent, defaults=None, title=None):
        super().__init__(parent)
        self.result = None

        self.title(title or t('calib.title'))
        self.geometry('460x420')
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_main'])
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 460) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 420) // 2
        self.geometry(f'+{x}+{y}')

        # Значения по умолчанию
        if defaults:
            self._defaults = defaults
        else:
            self._defaults = {'X0': '0', 'Y0': '0', 'X1': '10', 'Y1': '10'}

        self._entries = {}
        self._build_ui()

        self.after(50, self._focus_first)
        parent.wait_window(self)

    def _focus_first(self):
        try:
            self.lift()
            self.focus_force()
            self._entries['X0'].focus_set()
            self._entries['X0'].select_range(0, 'end')
        except Exception as e:
            print(f'[CALIB FOCUS ERROR] {e}')

    def _build_ui(self):
        # Заголовок
        ctk.CTkLabel(
            self, text=t('calib.title'),
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        ).pack(pady=(24, 4))

        # Подсказка
        ctk.CTkLabel(
            self, text=t('calib.x0') + ' / ' + t('calib.y0') + ' — ' +
                       t('calib.x1') + ' / ' + t('calib.y1'),
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(pady=(0, 16))

        # Поля ввода
        fields_frame = ctk.CTkFrame(self, fg_color='transparent')
        fields_frame.pack(fill='x', padx=40, pady=4)

        # Сетка 2x2
        for i, (key, label_key) in enumerate([
            ('X0', 'calib.x0'),
            ('Y0', 'calib.y0'),
            ('X1', 'calib.x1'),
            ('Y1', 'calib.y1'),
        ]):
            row = i // 2
            col = i % 2

            cell = ctk.CTkFrame(fields_frame, fg_color='transparent')
            cell.grid(row=row, column=col, padx=6, pady=6, sticky='ew')
            fields_frame.grid_columnconfigure(col, weight=1)

            ctk.CTkLabel(
                cell, text=t(label_key),
                font=FONTS['small'], text_color=COLORS['text_primary'],
                anchor='w'
            ).pack(anchor='w', pady=(0, 2))

            entry = ctk.CTkEntry(
                cell, height=40, corner_radius=8,
                font=FONTS['normal_bold'],
                fg_color=COLORS['bg_panel'],
                border_color=COLORS['accent'],
                border_width=2,
                text_color=COLORS['text_primary'],
            )
            entry.insert(0, str(self._defaults.get(key, '0')))
            entry.pack(fill='x')
            self._entries[key] = entry

        # Кнопки
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(fill='x', padx=40, pady=(24, 24))

        ctk.CTkButton(
            btn_frame, text=t('btn.cancel'), height=44, corner_radius=8,
            fg_color=COLORS['bg_hover'], hover_color=COLORS['border'],
            text_color=COLORS['text_primary'],
            font=FONTS['button'],
            command=self._cancel
        ).pack(side='left', fill='x', expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text=t('btn.ok'), height=44, corner_radius=8,
            fg_color=COLORS['success'], hover_color=COLORS['success_hover'],
            font=FONTS['button'],
            command=self._apply
        ).pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Горячие клавиши
        self.bind('<Return>', lambda e: self._apply())
        self.bind('<KP_Enter>', lambda e: self._apply())
        self.bind('<Escape>', lambda e: self._cancel())

        # Tab-навигация
        for key in ['X0', 'Y0', 'X1', 'Y1']:
            self._entries[key].bind('<Return>', lambda e, k=key: self._next_field(k))
            self._entries[key].bind('<KP_Enter>', lambda e, k=key: self._next_field(k))

    def _next_field(self, current_key):
        """Переход к следующему полю по Enter."""
        order = ['X0', 'Y0', 'X1', 'Y1']
        try:
            idx = order.index(current_key)
            if idx < len(order) - 1:
                next_key = order[idx + 1]
                self._entries[next_key].focus_set()
                self._entries[next_key].select_range(0, 'end')
            else:
                self._apply()
        except Exception:
            self._apply()

    def _apply(self):
        """Считывает значения и закрывает диалог."""
        values = {}
        for key, entry in self._entries.items():
            raw = entry.get().strip().replace(',', '.')
            if not raw:
                self._show_error(t('msg.enter_value'))
                entry.focus_set()
                return
            try:
                values[key] = float(raw)
            except ValueError:
                self._show_error(f'{t("msg.error")}: {key}')
                entry.focus_set()
                return

        self.result = values
        self.destroy()

    def _show_error(self, msg):
        from tkinter import messagebox
        messagebox.showwarning(t('msg.warning'), msg, parent=self)

    def _cancel(self):
        self.result = None
        self.destroy()