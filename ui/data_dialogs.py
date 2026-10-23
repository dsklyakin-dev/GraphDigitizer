"""
Диалоги для работы с данными.
v7.1 — с локализацией RU/EN
"""

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from config.settings import COLORS, FONTS
from core.i18n import t
from utils.text_bindings import bind_text_clipboard


class DataViewerDialog(ctk.CTkToplevel):
    """Окно просмотра точек с таблицей и кнопками."""

    def __init__(self, parent, data_points, graph_mode, x3_value=None, curve_names=None):
        super().__init__(parent)

        self.title(t('dv.title'))
        self.geometry('900x750')
        self.configure(fg_color=COLORS['bg_main'])
        self.transient(parent)

        self.data_points = data_points
        self.graph_mode = graph_mode
        self.x3_value = x3_value

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 900) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 750) // 2
        self.geometry(f'+{x}+{y}')

        self._build_ui()
        self._fill_data()

        # Фокус и модальность
        self.after(50, self._focus_window)
        self.grab_set()
        parent.wait_window(self)

    def _focus_window(self):
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _build_ui(self):
        # Заголовок
        ctk.CTkLabel(
            self, text=t('dv.title'),
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        ).pack(pady=(18, 4))

        # Инфо-строка
        info = self._get_info_text()
        ctk.CTkLabel(
            self, text=info,
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(pady=(0, 10))

        # Текстовое поле в рамке
        frame = ctk.CTkFrame(self, fg_color=COLORS['bg_panel'], corner_radius=8)
        frame.pack(fill='both', expand=True, padx=16, pady=(0, 10))

        self.text_widget = tk.Text(
            frame,
            wrap='none',
            font=('Consolas', 10),
            bg=COLORS['bg_panel'],
            fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary'],
            relief='flat',
            borderwidth=0,
            padx=10,
            pady=10,
        )
        bind_text_clipboard(self.text_widget)
        self.text_widget.pack(side='left', fill='both', expand=True)

        scroll_y = ctk.CTkScrollbar(frame, command=self.text_widget.yview)
        scroll_y.pack(side='right', fill='y', padx=(0, 4), pady=4)
        self.text_widget.configure(yscrollcommand=scroll_y.set)

        scroll_x = ctk.CTkScrollbar(self, orientation='horizontal',
                                    command=self.text_widget.xview)
        scroll_x.pack(fill='x', padx=16, pady=(0, 6))
        self.text_widget.configure(xscrollcommand=scroll_x.set)

        # Кнопки
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(fill='x', padx=16, pady=(0, 16))

        ctk.CTkButton(
            btn_frame, text=t('btn.copy_all'), height=40, corner_radius=8,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_hover'],
            font=FONTS['button'],
            command=self._copy_all
        ).pack(side='left', fill='x', expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text=t('btn.close'), height=40, corner_radius=8,
            fg_color=COLORS['bg_hover'], hover_color=COLORS['border'],
            text_color=COLORS['text_primary'],
            font=FONTS['button'],
            command=self._close
        ).pack(side='left', fill='x', expand=True, padx=(8, 0))

        self.bind('<Escape>', lambda e: self._close())

    def _get_info_text(self):
        if self.graph_mode == '1d':
            n = len(self.data_points)
            return t('dv.1d_info', n=n)
        else:
            total = sum(len(p) for p in self.data_points.values())
            curves = len(self.data_points)
            return t('dv.2d_info', curves=curves, points=total)

    def _fill_data(self):
        """Наполняет текстовое поле данными с выравниванием."""
        if self.graph_mode == '1d':
            if self.x3_value:
                headers = [t('dv.col_x'), t('dv.col_x3'), t('dv.col_y')]
            else:
                headers = [t('dv.col_x'), t('dv.col_y')]
        else:
            if self.x3_value:
                headers = [t('dv.col_x'), t('dv.col_x2'), t('dv.col_x3'), t('dv.col_y')]
            else:
                headers = [t('dv.col_x'), t('dv.col_x2'), t('dv.col_y')]

        rows = []
        if self.graph_mode == '1d':
            for x, y in self.data_points:
                x_str = str(round(x, 4)).replace('.', ',')
                y_str = str(round(y, 4)).replace('.', ',')
                if self.x3_value:
                    rows.append([x_str, self.x3_value, y_str])
                else:
                    rows.append([x_str, y_str])
        else:
            for curve_name, points in self.data_points.items():
                for x, y in points:
                    x_str = str(round(x, 4)).replace('.', ',')
                    y_str = str(round(y, 4)).replace('.', ',')
                    if self.x3_value:
                        rows.append([x_str, curve_name, self.x3_value, y_str])
                    else:
                        rows.append([x_str, curve_name, y_str])

        # Ширина колонок
        widths = []
        for i in range(len(headers)):
            max_w = len(headers[i])
            for row in rows:
                if i < len(row):
                    max_w = max(max_w, len(str(row[i])))
            widths.append(max_w + 2)

        lines = []
        header_line = '  '.join(h.ljust(widths[i]) for i, h in enumerate(headers))
        lines.append(header_line)
        lines.append('─' * len(header_line))

        for row in rows:
            line = '  '.join(str(row[i]).ljust(widths[i]) for i in range(len(headers)))
            lines.append(line)

        text = '\n'.join(lines)

        self.text_widget.insert('1.0', text)
        self.text_widget.config(state='disabled')

    def _copy_all(self):
        """Копирует таблицу в буфер без заголовков."""
        from utils.clipboard_excel import copy_table_to_clipboard

        rows = []
        if self.graph_mode == '1d':
            for x, y in self.data_points:
                x_str = str(round(x, 4)).replace('.', ',')
                y_str = str(round(y, 4)).replace('.', ',')
                if self.x3_value:
                    rows.append([x_str, self.x3_value, y_str])
                else:
                    rows.append([x_str, y_str])
        else:
            for curve_name, points in self.data_points.items():
                for x, y in points:
                    x_str = str(round(x, 4)).replace('.', ',')
                    y_str = str(round(y, 4)).replace('.', ',')
                    if self.x3_value:
                        rows.append([x_str, curve_name, self.x3_value, y_str])
                    else:
                        rows.append([x_str, curve_name, y_str])

        # headers=[] — без заголовков
        copy_table_to_clipboard(self, [], rows)
        messagebox.showinfo(t('msg.copied'), t('msg.copied_text'), parent=self)

    def _close(self):
        self.grab_release()
        self.destroy()


class X2Dialog(ctk.CTkToplevel):
    """Диалог ввода X2 для кривой."""

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None

        self.title(t('x2.title'))
        self.geometry('420x240')
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_main'])
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 420) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 240) // 2
        self.geometry(f'+{x}+{y}')

        self._build_ui()

        self.after(10, self._try_focus)
        self.after(100, self._try_focus)
        self.after(300, self._try_focus)

        parent.wait_window(self)

    def _try_focus(self):
        try:
            self.lift()
            self.attributes('-topmost', True)
            self.attributes('-topmost', False)
            self.focus_force()
            self.entry.focus_force()
            self.entry.focus_set()
            self.entry.icursor('end')
        except Exception as e:
            print(f'[X2 FOCUS ERROR] {e}')

    def _build_ui(self):
        ctk.CTkLabel(
            self, text=t('x2.prompt'),
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        ).pack(pady=(24, 4))

        ctk.CTkLabel(
            self, text=t('x2.hint'),
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(pady=(0, 16))

        self.entry = ctk.CTkEntry(
            self, height=44, corner_radius=8,
            font=FONTS['normal_bold'],
            fg_color=COLORS['bg_panel'],
            border_color=COLORS['accent'],
            border_width=2,
            text_color=COLORS['text_primary'],
        )
        self.entry.pack(fill='x', padx=40, pady=4)

        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(fill='x', padx=40, pady=(16, 24))

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

        self.bind('<Return>', lambda e: self._apply())
        self.bind('<KP_Enter>', lambda e: self._apply())
        self.bind('<Escape>', lambda e: self._cancel())

    def _apply(self):
        val = self.entry.get().strip()
        if not val:
            messagebox.showwarning(t('msg.warning'), t('msg.enter_value'), parent=self)
            return
        self.result = val
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()