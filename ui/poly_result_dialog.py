"""
Окно результатов построения по полиному.
v1.4 — добавлена кнопка "Открыть в Excel", копирование с табуляцией
"""

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import re
import os
import csv
import tempfile
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from config.settings import COLORS, FONTS
from core.i18n import t
from utils.text_bindings import bind_text_clipboard


def replace_variable_with_x(formula, var_name):
    """Заменяет переменную (F94, E14, x) на 'X' для отображения."""
    if not var_name:
        return formula
    if var_name == 'x':
        return re.sub(r'\bx\b', 'X', formula)
    pattern = r'\b' + re.escape(var_name) + r'\b'
    return re.sub(pattern, 'X', formula, flags=re.IGNORECASE)


class PolyResultDialog(ctk.CTkToplevel):
    def __init__(self, parent, points, x2=None, x3=None,
                 formula=None, var_name=None):
        super().__init__(parent)

        self.points = points
        self.x2 = x2
        self.x3 = x3
        self.formula = formula or ''
        self.var_name = var_name

        self.title(t('poly.result_title'))
        self.geometry('900x780')
        self.minsize(720, 540)
        self.configure(fg_color=COLORS['bg_main'])
        self.transient(parent)

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 900) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 780) // 2
        self.geometry(f'+{px}+{py}')

        self._build_ui()
        self._fill_data()

        self.after(50, self._focus_window)
        self.grab_set()
        parent.wait_window(self)

    def _focus_window(self):
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        PAD = 16

        # ===== Кнопки (снизу) =====
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(side='bottom', fill='x', padx=PAD, pady=(8, 16))

        ctk.CTkButton(
            btn_frame, text=t('poly.graph_view'), height=42, corner_radius=8,
            fg_color=COLORS['accent'], hover_color=COLORS['accent_hover'],
            font=FONTS['button'],
            command=self._show_graph,
        ).pack(side='left', fill='x', expand=True, padx=(0, 5))

        ctk.CTkButton(
            btn_frame, text=t('poly.open_excel'), height=42, corner_radius=8,
            fg_color=COLORS['success'], hover_color=COLORS['success_hover'],
            font=FONTS['button'],
            command=self._open_in_excel,
        ).pack(side='left', fill='x', expand=True, padx=5)

        ctk.CTkButton(
            btn_frame, text=t('btn.copy_all'), height=42, corner_radius=8,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_hover'],
            font=FONTS['button'],
            command=self._copy_all,
        ).pack(side='left', fill='x', expand=True, padx=5)

        ctk.CTkButton(
            btn_frame, text=t('btn.close'), height=42, corner_radius=8,
            fg_color=COLORS['bg_hover'], hover_color=COLORS['border'],
            text_color=COLORS['text_primary'],
            font=FONTS['button'],
            command=self._close,
        ).pack(side='left', fill='x', expand=True, padx=(5, 0))

        # ===== Инфо-строка =====
        n = len(self.points)
        ctk.CTkLabel(
            self, text=t('poly.result_info', n=n),
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(side='bottom', pady=(0, 6))

        # ===== Горизонтальный скролл =====
        scroll_x = ctk.CTkScrollbar(self, orientation='horizontal')
        scroll_x.pack(side='bottom', fill='x', padx=PAD, pady=(0, 6))

        # ===== Заголовок =====
        ctk.CTkLabel(
            self, text=t('poly.result_title'),
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        ).pack(side='top', pady=(16, 10))

        # ===== Формула =====
        if self.formula:
            display = self.formula.strip()
            display = replace_variable_with_x(display, self.var_name)
            if len(display) > 200:
                display = display[:197] + '...'

            formula_frame = ctk.CTkFrame(
                self, fg_color=COLORS['bg_hover'], corner_radius=8
            )
            formula_frame.pack(side='top', fill='x', padx=PAD, pady=(0, 12))

            ctk.CTkLabel(
                formula_frame,
                text=display,
                font=('Consolas', 13),
                text_color=COLORS['text_primary'],
                wraplength=820, justify='center',
            ).pack(padx=12, pady=10)

        # ===== Текстовое поле =====
        frame = ctk.CTkFrame(self, fg_color=COLORS['bg_panel'], corner_radius=8)
        frame.pack(side='top', fill='both', expand=True, padx=PAD, pady=(0, 4))

        self.text_widget = tk.Text(
            frame, wrap='none',
            font=('Consolas', 10),
            bg=COLORS['bg_panel'], fg=COLORS['text_primary'],
            relief='flat', borderwidth=0, padx=10, pady=10,
        )
        self.text_widget.pack(side='left', fill='both', expand=True)

        scroll_y = ctk.CTkScrollbar(frame, command=self.text_widget.yview)
        scroll_y.pack(side='right', fill='y', padx=(0, 4), pady=4)

        self.text_widget.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )
        scroll_x.configure(command=self.text_widget.xview)

        bind_text_clipboard(self.text_widget)

        self.bind('<Escape>', lambda e: self._close())

    # ============================================================
    # ЗАПОЛНЕНИЕ
    # ============================================================

    def _get_headers(self):
        headers = ['X']
        if self.x2:
            headers.append('X2')
        if self.x3:
            headers.append('X3')
        headers.append('Y')
        return headers

    def _get_row(self, x, y):
        row = [self._fmt(x)]
        if self.x2:
            row.append(self.x2)
        if self.x3:
            row.append(self.x3)
        row.append(self._fmt(y))
        return row

    def _fill_data(self):
        headers = self._get_headers()
        rows = [self._get_row(x, y) for x, y in self.points]

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

        self.text_widget.insert('1.0', '\n'.join(lines))
        self.text_widget.config(state='disabled')

    def _fmt(self, val):
        s = f'{val:.6f}'.rstrip('0').rstrip('.')
        return s.replace('.', ',')

    # ============================================================
    # КОПИРОВАНИЕ В БУФЕР
    # ============================================================

    def _copy_all(self):
        from utils.clipboard_excel import copy_table_to_clipboard

        rows = []
        for x, y in self.points:
            row = [self._fmt(x)]
            if self.x2:
                row.append(self.x2)
            if self.x3:
                row.append(self.x3)
            row.append(self._fmt(y))
            rows.append(row)

        # headers=[] — без заголовков
        copy_table_to_clipboard(self, [], rows)
        messagebox.showinfo(t('msg.copied'), t('msg.copied_text'), parent=self)

    # ============================================================
    # ОТКРЫТИЕ В EXCEL
    # ============================================================

    def _open_in_excel(self):
        """
        Сохраняет данные во временный .csv и открывает его Excel'ом.
        Excel сам разобьёт по столбцам.
        """
        # Формируем путь к временному файлу
        tmp_dir = tempfile.gettempdir()
        # Имя с временной меткой, чтобы не перезаписывать
        import time
        fname = f'graph_digitizer_{int(time.time())}.csv'
        path = os.path.join(tmp_dir, fname)

        headers = self._get_headers()

        try:
            with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(headers)
                for x, y in self.points:
                    row = [self._fmt(x)]
                    if self.x2:
                        row.append(self.x2)
                    if self.x3:
                        row.append(self.x3)
                    row.append(self._fmt(y))
                    writer.writerow(row)
        except Exception as e:
            messagebox.showerror(
                t('msg.error'),
                f'Не удалось сохранить файл:\n{e}',
                parent=self
            )
            return

        # Открываем через системный ассоциатор (Excel)
        try:
            os.startfile(path)
            messagebox.showinfo(
                t('poly.opened_excel'),
                t('poly.opened_excel_text', path=path),
                parent=self
            )
        except Exception as e:
            messagebox.showerror(
                t('msg.error'),
                f'Не удалось открыть файл:\n{e}\n\nФайл сохранён: {path}',
                parent=self
            )

    # ============================================================
    # ГРАФИК
    # ============================================================

    def _show_graph(self):
        fig = plt.figure(figsize=(10, 6), facecolor='white')
        ax = fig.add_subplot(111)

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]

        label = self.x2 if self.x2 else t('poly.graph_label')
        ax.plot(xs, ys, '-', color='#3B82F6', linewidth=2, label=label)
        ax.scatter(xs, ys, color='#EF4444', s=20, zorder=3)

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_title(t('poly.graph_title'))
        ax.grid(True, alpha=0.3)
        if label:
            ax.legend(loc='best')

        fig.tight_layout()
        plt.show()

    def _close(self):
        self.grab_release()
        self.destroy()