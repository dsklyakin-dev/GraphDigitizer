"""
Диалог ввода формулы для построения графика по полиному.
v1.4 — исправлена передача var_name, добавлена диагностика
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from config.settings import COLORS, FONTS
from core.i18n import t
from core.polynomial import (
    validate_formula,
    detect_macro,
    detect_variable,
    parse_data_paste,
    build_points,
    LinearInterpolator,
    FormulaError,
    MacroDetectedError,
)
from utils.text_bindings import bind_text_clipboard


class PolyDialog(ctk.CTkToplevel):
    """
    Диалог ввода формулы и диапазона X.
    Результат: dict с ключами
      - points: list of (x, y)
      - x2: строка или None
      - x3: строка или None
      - formula: исходная формула
      - var_name: имя переменной (F94, E14, x)
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None

        self.title(t('poly.dialog_title'))
        self.geometry('760x860')
        self.minsize(700, 700)
        self.configure(fg_color=COLORS['bg_main'])
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 720) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 780) // 2
        self.geometry(f'+{px}+{py}')

        self._interpolator = None
        self._build_ui()

        self.after(50, self._focus_formula)
        parent.wait_window(self)

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        PAD = 20

        # ===== Заголовок =====
        ctk.CTkLabel(
            self, text=t('poly.dialog_title'),
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        ).pack(side='top', pady=(18, 4))

        ctk.CTkLabel(
            self, text=t('poly.dialog_hint'),
            font=FONTS['small'], text_color=COLORS['text_secondary'],
            justify='left'
        ).pack(side='top', pady=(0, 12), padx=PAD)

        # ===== Кнопки снизу =====
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(side='bottom', fill='x', padx=PAD, pady=(8, 16))

        ctk.CTkButton(
            btn_frame, text=t('btn.cancel'), height=44, corner_radius=10,
            fg_color=COLORS['bg_hover'], hover_color=COLORS['border'],
            text_color=COLORS['text_primary'],
            font=FONTS['button'],
            command=self._cancel,
        ).pack(side='left', fill='x', expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text=t('poly.build'), height=44, corner_radius=10,
            fg_color=COLORS['success'], hover_color=COLORS['success_hover'],
            font=FONTS['button'],
            command=self._build,
        ).pack(side='left', fill='x', expand=True, padx=(6, 0))

        # ============================================================
        # ВАЖНО: сначала СОЗДАЁМ и ПАКУЕМ macro_frame, потом СРАЗУ скрываем.
        # Он будет "запомнен" в порядке упаковки и вернётся туда же.
        # ============================================================
        self.macro_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.macro_frame.pack(side='top', fill='x', padx=PAD, pady=(8, 4))
        self.macro_frame.pack_forget()  # ← скрыт, но место запомнено

        # Наполнение macro_frame (создаётся сразу)
        ctk.CTkLabel(
            self.macro_frame, text=t('poly.macro_data'),
            font=FONTS['small_bold'], text_color=COLORS['text_primary']
        ).pack(anchor='w', pady=(4, 2))

        ctk.CTkLabel(
            self.macro_frame, text=t('poly.macro_data_hint'),
            font=FONTS['small'], text_color=COLORS['text_secondary'],
            justify='left'
        ).pack(anchor='w', pady=(0, 4))

        self.macro_text = tk.Text(
            self.macro_frame, height=4, wrap='none',
            font=('Consolas', 10),
            bg=COLORS['bg_panel'], fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary'],
            relief='flat', borderwidth=0, padx=8, pady=8,
        )
        self.macro_text.pack(fill='x', pady=(0, 4))
        bind_text_clipboard(self.macro_text)

        # ===== Диапазон X =====
        self.range_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.range_frame.pack(side='top', fill='x', padx=PAD, pady=(8, 4))

        ctk.CTkLabel(
            self.range_frame, text=t('poly.range'),
            font=FONTS['small_bold'], text_color=COLORS['text_primary']
        ).grid(row=0, column=0, columnspan=6, sticky='w', pady=(0, 6))

        ctk.CTkLabel(
            self.range_frame, text=t('poly.x_start'),
            font=FONTS['small'], text_color=COLORS['text_primary']
        ).grid(row=1, column=0, sticky='w', padx=(0, 6))

        self.x_start_entry = ctk.CTkEntry(
            self.range_frame, width=100, height=34,
            font=FONTS['small_bold'],
            fg_color=COLORS['bg_panel'],
            border_color=COLORS['border'],
            text_color=COLORS['text_primary'],
        )
        self.x_start_entry.insert(0, '0')
        self.x_start_entry.grid(row=1, column=1, padx=(0, 12))

        ctk.CTkLabel(
            self.range_frame, text=t('poly.x_end'),
            font=FONTS['small'], text_color=COLORS['text_primary']
        ).grid(row=1, column=2, sticky='w', padx=(0, 6))

        self.x_end_entry = ctk.CTkEntry(
            self.range_frame, width=100, height=34,
            font=FONTS['small_bold'],
            fg_color=COLORS['bg_panel'],
            border_color=COLORS['border'],
            text_color=COLORS['text_primary'],
        )
        self.x_end_entry.insert(0, '10')
        self.x_end_entry.grid(row=1, column=3, padx=(0, 12))

        ctk.CTkLabel(
            self.range_frame, text=t('poly.x_step'),
            font=FONTS['small'], text_color=COLORS['text_primary']
        ).grid(row=1, column=4, sticky='w', padx=(0, 6))

        self.x_step_entry = ctk.CTkEntry(
            self.range_frame, width=100, height=34,
            font=FONTS['small_bold'],
            fg_color=COLORS['bg_panel'],
            border_color=COLORS['border'],
            text_color=COLORS['text_primary'],
        )
        self.x_step_entry.insert(0, '1')
        self.x_step_entry.grid(row=1, column=5)

        # ===== X2 / X3 =====
        extra_frame = ctk.CTkFrame(self, fg_color='transparent')
        extra_frame.pack(side='top', fill='x', padx=PAD, pady=(8, 4))

        ctk.CTkLabel(
            extra_frame, text=t('poly.extra'),
            font=FONTS['small_bold'], text_color=COLORS['text_primary']
        ).grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 6))

        ctk.CTkLabel(
            extra_frame, text=t('poly.x2'),
            font=FONTS['small'], text_color=COLORS['text_primary']
        ).grid(row=1, column=0, sticky='w', padx=(0, 6))

        self.x2_entry = ctk.CTkEntry(
            extra_frame, width=180, height=34,
            font=FONTS['small_bold'],
            fg_color=COLORS['bg_panel'],
            border_color=COLORS['border'],
            text_color=COLORS['text_primary'],
            placeholder_text=t('poly.optional'),
        )
        self.x2_entry.grid(row=1, column=1, padx=(0, 16))

        ctk.CTkLabel(
            extra_frame, text=t('poly.x3'),
            font=FONTS['small'], text_color=COLORS['text_primary']
        ).grid(row=1, column=2, sticky='w', padx=(0, 6))

        self.x3_entry = ctk.CTkEntry(
            extra_frame, width=180, height=34,
            font=FONTS['small_bold'],
            fg_color=COLORS['bg_panel'],
            border_color=COLORS['border'],
            text_color=COLORS['text_primary'],
            placeholder_text=t('poly.optional'),
        )
        self.x3_entry.grid(row=1, column=3)

        # ===== Формула =====
        ctk.CTkLabel(
            self, text=t('poly.formula'),
            font=FONTS['small_bold'], text_color=COLORS['text_primary']
        ).pack(side='top', anchor='w', padx=PAD, pady=(8, 2))

        self.formula_text = tk.Text(
            self, height=4, wrap='word',
            font=('Consolas', 10),
            bg=COLORS['bg_panel'], fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary'],
            relief='flat', borderwidth=0, padx=8, pady=8,
        )
        self.formula_text.pack(side='top', fill='x', padx=PAD, pady=(0, 4))
        bind_text_clipboard(self.formula_text)

        # ===== Кнопка проверки + статус =====
        check_frame = ctk.CTkFrame(self, fg_color='transparent')
        check_frame.pack(side='top', fill='x', padx=PAD, pady=(0, 8))

        ctk.CTkButton(
            check_frame, text=t('poly.check'), height=32, corner_radius=8,
            fg_color=COLORS['bg_hover'], hover_color=COLORS['border'],
            text_color=COLORS['text_primary'],
            font=FONTS['small_bold'],
            command=self._check_formula,
            width=160,
        ).pack(side='left')

        self.status_label = ctk.CTkLabel(
            check_frame, text='',
            font=FONTS['small'], text_color=COLORS['text_secondary'],
            justify='left', wraplength=460,
        )
        self.status_label.pack(side='left', padx=(10, 0), fill='x', expand=True)

        self.bind('<Escape>', lambda e: self._cancel())

    # ============================================================
    # ФОКУС
    # ============================================================

    def _focus_formula(self):
        try:
            self.lift()
            self.focus_force()
            self.formula_text.focus_set()
        except Exception:
            pass

    # ============================================================
    # ПРОВЕРКА ФОРМУЛЫ
    # ============================================================

    def _check_formula(self):
        formula = self.formula_text.get('1.0', 'end').strip()
        if not formula:
            self._set_status(t('poly.error_empty'), 'danger')
            return

        macro = detect_macro(formula)
        if macro:
            var = macro.get('var_cell') or '—'
            self._set_status(
                t('poly.macro_found',
                  name=macro['macro_name'],
                  sheet=macro.get('sheet') or '—',
                  rng=macro.get('cell_range') or '—'),
                'warning'
            )
            # Показ поля — просто pack(), место уже запомнено
            if not self.macro_frame.winfo_ismapped():
                self.macro_frame.pack(side='top', fill='x', padx=20, pady=(0, 8))
            return

        ok, msg, _ = validate_formula(formula)
        if ok:
            self._set_status(msg, 'success')
        else:
            self._set_status(msg, 'danger')

    def _set_status(self, text, kind='info'):
        colors = {
            'info': COLORS['text_secondary'],
            'success': COLORS['success'],
            'warning': COLORS['warning'],
            'danger': COLORS['danger'],
        }
        self.status_label.configure(
            text=text, text_color=colors.get(kind, COLORS['text_secondary'])
        )

    # ============================================================
    # ПОСТРОЕНИЕ
    # ============================================================

    def _build(self):
        print('[POLY] _build вызван')

        formula = self.formula_text.get('1.0', 'end').strip()
        print(f'[POLY] formula: {formula[:80]!r}')

        if not formula:
            self._set_status(t('poly.error_empty'), 'danger')
            return

        # --- Диапазон ---
        try:
            x_start = float(self.x_start_entry.get().strip().replace(',', '.'))
            x_end = float(self.x_end_entry.get().strip().replace(',', '.'))
            x_step = float(self.x_step_entry.get().strip().replace(',', '.'))
        except ValueError:
            self._set_status(t('poly.error_range'), 'danger')
            return

        print(f'[POLY] range: {x_start} … {x_end}, step={x_step}')

        # --- Макрос ---
        macro = detect_macro(formula)
        interpolator = None

        if macro:
            print(f'[POLY] macro: {macro}')
            data_text = self.macro_text.get('1.0', 'end').strip()
            if not data_text:
                self._set_status(t('poly.error_macro_data'), 'danger')
                if not self.macro_frame.winfo_ismapped():
                    self.macro_frame.pack(side='top', fill='x', padx=20, pady=(0, 8))
                return
            try:
                xs, ys = parse_data_paste(data_text)
                interpolator = LinearInterpolator(xs, ys)
                print(f'[POLY] interpolator: {len(xs)} точек')
            except FormulaError as e:
                self._set_status(str(e), 'danger')
                return

        # --- Строим ---
        try:
            points = build_points(
                formula, x_start, x_end, x_step,
                interpolator=interpolator,
                max_points=10000,
            )
        except MacroDetectedError:
            self._set_status(t('poly.error_macro_data'), 'danger')
            if not self.macro_frame.winfo_ismapped():
                self.macro_frame.pack(side='top', fill='x', padx=20, pady=(0, 8))
            return
        except FormulaError as e:
            self._set_status(str(e), 'danger')
            return
        except Exception as e:
            self._set_status(f'Ошибка: {e}', 'danger')
            return

        print(f'[POLY] points: {len(points)}')

        if not points:
            self._set_status(t('poly.error_no_points'), 'danger')
            return

        # --- X2 / X3 ---
        x2 = self.x2_entry.get().strip() or None
        x3 = self.x3_entry.get().strip() or None

        # --- Переменная (для отображения формулы с X) ---
        try:
            var_name = detect_variable(formula, macro=macro)
        except Exception:
            var_name = None

        print(f'[POLY] result: var_name={var_name}, x2={x2}, x3={x3}')

        self.result = {
            'points': points,
            'x2': x2,
            'x3': x3,
            'formula': formula,
            'var_name': var_name,
        }

        print('[POLY] закрываю диалог')
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()