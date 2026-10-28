"""
Диалоги для работы с данными.
v7.5 — с ограничениями по X и удалением строк
"""

import tkinter as tk
import tkinter.ttk as ttk
import customtkinter as ctk
from tkinter import messagebox
from config.settings import COLORS, FONTS
from core.i18n import t


class DataViewerDialog(ctk.CTkToplevel):
    """Окно просмотра, редактирования и ограничения точек."""

    def __init__(self, parent, data_points, graph_mode, x3_value=None, curve_names=None):
        super().__init__(parent)

        self.title(t('dv.title'))
        self.geometry('950x800')
        self.configure(fg_color=COLORS['bg_main'])
        self.transient(parent)

        self.data_points = data_points
        self.graph_mode = graph_mode
        self.x3_value = x3_value

        # Сюда сохраняем измененные данные для возврата в app_window
        self.updated_data = None
        self._last_selected = None

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 950) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 800) // 2
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

        info = self._get_info_text()
        ctk.CTkLabel(
            self, text=info,
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(pady=(0, 10))

        # ===== ПАНЕЛЬ ОГРАНИЧЕНИЙ =====
        limits_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_panel'], corner_radius=8)
        limits_frame.pack(fill='x', padx=16, pady=(0, 10))

        ctk.CTkLabel(
            limits_frame, text=t('dv.limits_title'),
            font=FONTS['small_bold'], text_color=COLORS['text_primary']
        ).pack(side='left', padx=(10, 10), pady=10)

        ctk.CTkLabel(limits_frame, text=t('dv.min'), font=FONTS['small']).pack(side='left')
        self.entry_xmin = ctk.CTkEntry(limits_frame, width=90, height=32)
        self.entry_xmin.pack(side='left', padx=(5, 15))

        ctk.CTkLabel(limits_frame, text=t('dv.max'), font=FONTS['small']).pack(side='left')
        self.entry_xmax = ctk.CTkEntry(limits_frame, width=90, height=32)
        self.entry_xmax.pack(side='left', padx=(5, 15))

        ctk.CTkButton(
            limits_frame, text=t('dv.apply_limits'), width=100, height=32,
            fg_color=COLORS['warning'], hover_color=COLORS['warning_hover'],
            command=self._apply_limits
        ).pack(side='left', padx=5)

        ctk.CTkButton(
            limits_frame, text=t('dv.delete_selected'), width=150, height=32,
            fg_color=COLORS['danger'], hover_color=COLORS['danger_hover'],
            command=self._delete_selected
        ).pack(side='right', padx=10)

        # ===== ТАБЛИЦА =====
        frame = ctk.CTkFrame(self, fg_color=COLORS['bg_panel'], corner_radius=8)
        frame.pack(fill='both', expand=True, padx=16, pady=(0, 10))

        # Настройка стилей Treeview для темной/светлой темы
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=COLORS['bg_panel'],
                        foreground=COLORS['text_primary'],
                        fieldbackground=COLORS['bg_panel'],
                        borderwidth=0)
        style.map("Treeview", background=[('selected', COLORS['primary'])])
        style.configure("Treeview.Heading",
                        background=COLORS['bg_hover'],
                        foreground=COLORS['text_primary'],
                        relief="flat")

        self.tree = ttk.Treeview(frame, show='headings', selectmode='extended')
        self.tree.pack(side='left', fill='both', expand=True, padx=2, pady=2)

        scroll_y = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scroll_y.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scroll_y.set)

        # Привязка для редактирования по двойному клику
        self.tree.bind('<Double-1>', self._on_tree_double_click)

        # Кнопки внизу
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(fill='x', padx=16, pady=(0, 16))

        ctk.CTkButton(
            btn_frame, text=t('btn.copy_all'), height=40, corner_radius=8,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_hover'],
            font=FONTS['button'],
            command=self._copy_all
        ).pack(side='left', fill='x', expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text=t('dv.apply_and_close'), height=40, corner_radius=8,
            fg_color=COLORS['success'], hover_color=COLORS['success_hover'],
            font=FONTS['button'],
            command=self._apply_and_close
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
        """Наполняет таблицу данными."""
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

        self.tree["columns"] = headers
        for col in headers:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor='center')

        # Заполняем данными
        if self.graph_mode == '1d':
            for x, y in self.data_points:
                x_str = str(round(x, 4)).replace('.', ',')
                y_str = str(round(y, 4)).replace('.', ',')
                if self.x3_value:
                    self.tree.insert("", "end", values=(x_str, self.x3_value, y_str))
                else:
                    self.tree.insert("", "end", values=(x_str, y_str))
        else:
            for curve_name, points in self.data_points.items():
                for x, y in points:
                    x_str = str(round(x, 4)).replace('.', ',')
                    y_str = str(round(y, 4)).replace('.', ',')
                    if self.x3_value:
                        self.tree.insert("", "end", values=(x_str, curve_name, self.x3_value, y_str))
                    else:
                        self.tree.insert("", "end", values=(x_str, curve_name, y_str))

    def _on_tree_double_click(self, event):
        """Редактирование ячейки по двойному клику."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        current_values = self.tree.item(item_id, 'values')
        col_index = int(column.replace('#', '')) - 1

        x, y, width, height = self.tree.bbox(item_id, column)

        entry = ctk.CTkEntry(self.tree, width=width, height=height, corner_radius=0)
        entry.place(x=x, y=y)
        entry.insert(0, current_values[col_index])
        entry.focus()
        entry.select_range(0, 'end')

        def save_edit(event=None):
            new_val = entry.get()
            new_val = new_val.replace(',', '.')

            try:
                float(new_val)
            except ValueError:
                messagebox.showerror(t('msg.error'), t('dv.error_number'))
                return

            new_values = list(current_values)
            new_values[col_index] = new_val.replace('.', ',')
            self.tree.item(item_id, values=new_values)

            entry.destroy()

        entry.bind('<Return>', save_edit)
        entry.bind('<FocusOut>', save_edit)
        entry.bind('<Escape>', lambda e: entry.destroy())

    def _apply_limits(self):
        try:
            x_min_val = float(self.entry_xmin.get().replace(',', '.')) if self.entry_xmin.get().strip() else None
        except ValueError:
            messagebox.showerror("Ошибка", t('dv.error_min'))
            return

        try:
            x_max_val = float(self.entry_xmax.get().replace(',', '.')) if self.entry_xmax.get().strip() else None
        except ValueError:
            messagebox.showerror("Ошибка", t('dv.error_max'))
            return

        if x_min_val is None and x_max_val is None:
            return

        # Собираем данные из таблицы
        items = list(self.tree.get_children())
        if not items:
            return

        # Группируем по кривым (для 2D) или в один список (для 1D)
        from collections import defaultdict
        curve_data = defaultdict(list)  # {curve_name: [(item_id, x_val)]}

        for item_id in items:
            vals = self.tree.item(item_id, 'values')
            try:
                x_val = float(vals[0].replace(',', '.'))
            except ValueError:
                continue

            if self.graph_mode == '1d':
                curve_name = 'single'
            else:
                curve_name = vals[1]  # X2

            curve_data[curve_name].append((item_id, x_val))

        # Для каждой кривой находим min и max X
        for curve_name, points in curve_data.items():
            if not points:
                continue

            # Находим минимальный и максимальный X
            min_item, min_x = min(points, key=lambda p: p[1])
            max_item, max_x = max(points, key=lambda p: p[1])

            # Если задан Min и текущий min_x близок к нему (разница < 2% от диапазона)
            if x_min_val is not None:
                # Проверяем, насколько близко
                if abs(min_x - x_min_val) < abs(x_max_val - x_min_val) * 0.02 if x_max_val else True:
                    # Меняем крайнюю точку
                    vals = list(self.tree.item(min_item, 'values'))
                    vals[0] = str(round(x_min_val, 4)).replace('.', ',')
                    self.tree.item(min_item, values=vals)

            # Если задан Max и текущий max_x близок к нему
            if x_max_val is not None:
                if abs(max_x - x_max_val) < abs(x_max_val - x_min_val) * 0.02 if x_min_val else True:
                    vals = list(self.tree.item(max_item, 'values'))
                    vals[0] = str(round(x_max_val, 4)).replace('.', ',')
                    self.tree.item(max_item, values=vals)

        messagebox.showinfo(t('msg.done'), t('dv.limits_applied'))

    def _delete_selected(self):
        """Удаляет выделенные строки из таблицы."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo(t('dv.delete_title'), t('dv.delete_info'))
            return

        for item_id in selected:
            self.tree.delete(item_id)

    def _apply_and_close(self):
        """Собирает данные из таблицы и закрывает окно."""
        new_data_1d = []
        new_data_2d = {}

        for item_id in self.tree.get_children():
            vals = self.tree.item(item_id, 'values')

            try:
                x_val = float(vals[0].replace(',', '.'))

                if self.graph_mode == '1d':
                    if self.x3_value:
                        y_val = float(vals[2].replace(',', '.'))
                    else:
                        y_val = float(vals[1].replace(',', '.'))
                    new_data_1d.append((x_val, y_val))
                else:
                    if self.x3_value:
                        curve_name = vals[1]
                        y_val = float(vals[3].replace(',', '.'))
                    else:
                        curve_name = vals[1]
                        y_val = float(vals[2].replace(',', '.'))

                    if curve_name not in new_data_2d:
                        new_data_2d[curve_name] = []
                    new_data_2d[curve_name].append((x_val, y_val))
            except Exception as e:
                print(f"Ошибка парсинга строки: {e}")
                continue

        if self.graph_mode == '1d':
            self.updated_data = new_data_1d
        else:
            self.updated_data = new_data_2d

        self._close()

    def _copy_all(self):
        """Копирует таблицу в буфер без заголовков."""
        from utils.clipboard_excel import copy_table_to_clipboard

        rows = []
        for item_id in self.tree.get_children():
            vals = self.tree.item(item_id, 'values')
            rows.append(list(vals))

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