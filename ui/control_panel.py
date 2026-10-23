"""
Панель управления справа.
v7.4 — ровные отступы, 2 кнопки в ряд, язык+инструкция внизу
"""

import customtkinter as ctk
from config.settings import COLORS, FONTS, WINDOW
from core.i18n import t, i18n
from core.theme_manager import theme_manager




class ControlPanel(ctk.CTkFrame):
    def __init__(self, parent, on_action, on_language_change=None, on_help=None):
        super().__init__(
            parent,
            width=WINDOW['panel_width'],
            corner_radius=0,
            fg_color=COLORS['bg_panel'],
        )
        self.pack_propagate(False)

        self.on_action = on_action
        self.on_language_change = on_language_change
        self.on_help = on_help

        self.current_mode = '1d'
        self._widgets_to_update = []

        self._build_ui()
        i18n.on_change(lambda lang: self._retranslate())

    # ============================================================
    # ПОСТРОЕНИЕ
    # ============================================================

    def _build_ui(self):
        PAD = 16          # отступ панели слева/справа
        GAP = 6           # расстояние между кнопками в строке
        BH = WINDOW['button_height']  # 44
        BH_SMALL = 40

        # ===== ЗАГОЛОВОК =====
        self.title_label = ctk.CTkLabel(
            self, text=t('panel.control'),
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        )
        self.title_label.pack(anchor='w', padx=PAD, pady=(18, 14))
        self._reg(self.title_label, 'panel.control')

        # ===== Открыть (на всю ширину) =====
        self.btn_open = ctk.CTkButton(
            self, text=t('btn.open'), height=BH, corner_radius=10,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_hover'],
            font=FONTS['button'],
            command=lambda: self.on_action('open_image'),
        )
        self.btn_open.pack(fill='x', padx=PAD, pady=(0, GAP))
        self._reg(self.btn_open, 'btn.open')

        # ===== Авто-калиб. | Калибровка =====
        row = ctk.CTkFrame(self, fg_color='transparent')
        row.pack(fill='x', padx=PAD, pady=(0, GAP))

        self.btn_auto = ctk.CTkButton(
            row, text=t('btn.auto_calib'), height=BH, corner_radius=10,
            fg_color=COLORS['accent'], hover_color=COLORS['accent_hover'],
            font=FONTS['small_bold'],
            command=lambda: self.on_action('auto_calib'),
        )
        self.btn_auto.pack(side='left', fill='x', expand=True, padx=(0, GAP // 2))
        self._reg(self.btn_auto, 'btn.auto_calib')

        self.btn_manual_calib = ctk.CTkButton(
            row, text=t('btn.manual_calib'), height=BH, corner_radius=10,
            fg_color=COLORS['warning'], hover_color=COLORS['warning_hover'],
            font=FONTS['small_bold'],
            command=lambda: self.on_action('manual_calib'),
        )
        self.btn_manual_calib.pack(side='left', fill='x', expand=True, padx=(GAP // 2, 0))
        self._reg(self.btn_manual_calib, 'btn.manual_calib')

        # ===== Контейнер Оцифровать / Назначить кривую =====
        self.action_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.action_frame.pack(fill='x', padx=PAD, pady=(0, GAP))

        self.btn_digitize = ctk.CTkButton(
            self.action_frame, text=t('btn.digitize'), height=BH, corner_radius=10,
            fg_color=COLORS['success'], hover_color=COLORS['success_hover'],
            font=FONTS['button'],
            command=lambda: self.on_action('digitize_auto'),
        )
        self._reg(self.btn_digitize, 'btn.digitize')

        self.btn_assign = ctk.CTkButton(
            self.action_frame, text=t('btn.assign_curve'), height=BH, corner_radius=10,
            fg_color=COLORS['accent'], hover_color=COLORS['accent_hover'],
            font=FONTS['button'],
            command=lambda: self.on_action('assign_curve'),
        )
        self._reg(self.btn_assign, 'btn.assign_curve')

        self.multi_curve_var = ctk.BooleanVar(value=False)
        # ===== Кнопка-переключатель "Несколько кривых в одной" =====
        self.multi_curve_btn = ctk.CTkButton(
            self.action_frame,
            text=t('btn.multi_curve_off'),
            height=32,
            corner_radius=8,
            fg_color=COLORS['bg_hover'],
            hover_color=COLORS['border'],
            text_color=COLORS['text_secondary'],
            font=FONTS['button'],
            command=self._toggle_multi_curve_btn
        )
        self._reg(self.multi_curve_btn, 'btn.multi_curve_off')

        # ===== Сгладить (на всю ширину) =====
        self.btn_smooth = ctk.CTkButton(
            self, text=t('btn.smooth'), height=BH, corner_radius=10,
            fg_color="#8B5CF6", hover_color="#7C3AED",
            font=FONTS['button'],
            command=lambda: self.on_action('smooth_data'),
        )
        self.btn_smooth.pack(fill='x', padx=PAD, pady=(0, GAP))
        self._reg(self.btn_smooth, 'btn.smooth')

        # По умолчанию — 1D
        self.btn_digitize.pack(fill='x')

        # ===== Вручную | Двигать =====
        row = ctk.CTkFrame(self, fg_color='transparent')
        row.pack(fill='x', padx=PAD, pady=(0, GAP))

        self.btn_manual = ctk.CTkButton(
            row, text=t('btn.manual'), height=BH_SMALL, corner_radius=10,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_hover'],
            font=FONTS['small_bold'],
            command=lambda: self.on_action('tool_manual'),
        )
        self.btn_manual.pack(side='left', fill='x', expand=True, padx=(0, GAP // 2))
        self._reg(self.btn_manual, 'btn.manual')

        self.btn_drag = ctk.CTkButton(
            row, text=t('btn.drag'), height=BH_SMALL, corner_radius=10,
            fg_color=COLORS['warning'], hover_color=COLORS['warning_hover'],
            font=FONTS['small_bold'],
            command=lambda: self.on_action('tool_drag'),
        )
        self.btn_drag.pack(side='left', fill='x', expand=True, padx=(GAP // 2, 0))
        self._reg(self.btn_drag, 'btn.drag')

        # ===== Удалить | Карандаш =====
        row = ctk.CTkFrame(self, fg_color='transparent')
        row.pack(fill='x', padx=PAD, pady=(0, GAP))

        self.btn_delete = ctk.CTkButton(
            row, text=t('btn.delete'), height=BH_SMALL, corner_radius=10,
            fg_color=COLORS['danger'], hover_color=COLORS['danger_hover'],
            font=FONTS['small_bold'],
            command=lambda: self.on_action('tool_delete'),
        )
        self.btn_delete.pack(side='left', fill='x', expand=True, padx=(0, GAP // 2))
        self._reg(self.btn_delete, 'btn.delete')

        self.btn_pencil = ctk.CTkButton(
            row, text=t('btn.pencil'), height=BH_SMALL, corner_radius=10,
            fg_color='#F97316', hover_color='#EA580C',
            font=FONTS['small_bold'],
            command=lambda: self.on_action('tool_pencil'),
        )
        self.btn_pencil.pack(side='left', fill='x', expand=True, padx=(GAP // 2, 0))
        self._reg(self.btn_pencil, 'btn.pencil')

        # ===== Отрезок | Отменить =====
        row = ctk.CTkFrame(self, fg_color='transparent')
        row.pack(fill='x', padx=PAD, pady=(0, GAP))

        self.btn_segment = ctk.CTkButton(
            row, text=t('btn.segment'), height=BH_SMALL, corner_radius=10,
            fg_color=COLORS['accent'], hover_color=COLORS['accent_hover'],
            font=FONTS['small_bold'],
            command=lambda: self.on_action('tool_segment'),
        )
        self.btn_segment.pack(side='left', fill='x', expand=True, padx=(0, GAP // 2))
        self._reg(self.btn_segment, 'btn.segment')

        self.btn_undo = ctk.CTkButton(
            row, text=t('btn.undo'), height=BH_SMALL, corner_radius=10,
            fg_color='#607D8B', hover_color='#455A64',
            font=FONTS['small_bold'],
            command=lambda: self.on_action('undo'),
        )
        self.btn_undo.pack(side='left', fill='x', expand=True, padx=(GAP // 2, 0))
        self._reg(self.btn_undo, 'btn.undo')

        # ===== Показать | Сохранить =====
        row = ctk.CTkFrame(self, fg_color='transparent')
        row.pack(fill='x', padx=PAD, pady=(0, GAP))

        self.btn_show = ctk.CTkButton(
            row, text=t('btn.show'), height=BH, corner_radius=10,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_hover'],
            font=FONTS['button'],
            command=lambda: self.on_action('show_data'),
        )
        self.btn_show.pack(side='left', fill='x', expand=True, padx=(0, GAP // 2))
        self._reg(self.btn_show, 'btn.show')

        self.btn_save = ctk.CTkButton(
            row, text=t('btn.save'), height=BH, corner_radius=10,
            fg_color=COLORS['success'], hover_color=COLORS['success_hover'],
            font=FONTS['button'],
            command=lambda: self.on_action('save_data'),
        )
        self.btn_save.pack(side='left', fill='x', expand=True, padx=(GAP // 2, 0))
        self._reg(self.btn_save, 'btn.save')

        # ===== Очистить все (на всю ширину) =====
        self.btn_clear = ctk.CTkButton(
            self, text=t('btn.clear'), height=BH, corner_radius=10,
            fg_color=COLORS['danger'], hover_color=COLORS['danger_hover'],
            font=FONTS['button'],
            command=lambda: self.on_action('clear_all'),
        )
        self.btn_clear.pack(fill='x', padx=PAD, pady=(0, GAP))
        self._reg(self.btn_clear, 'btn.clear')

        # ===== DIVIDER =====
        divider = ctk.CTkFrame(self, fg_color=COLORS['border'], height=1)
        divider.pack(fill='x', padx=PAD, pady=(12, 10))

        # ===== НАСТРОЙКИ =====
        self.settings_label = ctk.CTkLabel(
            self, text=t('panel.settings'),
            font=FONTS['small_bold'], text_color=COLORS['text_secondary']
        )
        self.settings_label.pack(pady=(0, 8))
        self._reg(self.settings_label, 'panel.settings')

        # Шаг точек
        row = ctk.CTkFrame(self, fg_color='transparent')
        row.pack(fill='x', padx=PAD, pady=(0, GAP))
        self.step_label = ctk.CTkLabel(
            row, text=t('settings.step'),
            font=FONTS['small'], text_color=COLORS['text_primary']
        )
        self.step_label.pack(side='left')
        self._reg(self.step_label, 'settings.step')

        self.step_entry = ctk.CTkEntry(
            row, width=70, height=32,
            font=FONTS['small_bold'],
            fg_color=COLORS['bg_hover'],
            border_color=COLORS['border'],
            text_color=COLORS['text_primary'],
        )
        self.step_entry.insert(0, '8')
        self.step_entry.pack(side='right')

        # Толщина курсора
        row = ctk.CTkFrame(self, fg_color='transparent')
        row.pack(fill='x', padx=PAD, pady=(0, GAP))
        self.radius_label = ctk.CTkLabel(
            row, text=t('settings.radius'),
            font=FONTS['small'], text_color=COLORS['text_primary']
        )
        self.radius_label.pack(side='left')
        self._reg(self.radius_label, 'settings.radius')

        self.radius_entry = ctk.CTkEntry(
            row, width=70, height=32,
            font=FONTS['small_bold'],
            fg_color=COLORS['bg_hover'],
            border_color=COLORS['border'],
            text_color=COLORS['text_primary'],
        )
        self.radius_entry.insert(0, '10')
        self.radius_entry.pack(side='right')

        # ===== РАСПОРКА (занимает всё свободное место, прижимая низ) =====
        spacer = ctk.CTkFrame(self, fg_color='transparent')
        spacer.pack(fill='both', expand=True)

        # Принудительно прижимаем нижний блок к самому низу
        self.bottom_frame_placeholder = ctk.CTkFrame(self, fg_color='transparent', height=0)
        self.bottom_frame_placeholder.pack(side='bottom', fill='x')

        # ===== СТАТУС =====
        self.status_label = ctk.CTkLabel(
            self, text='',
            font=FONTS['small'], text_color=COLORS['text_secondary'],
            wraplength=WINDOW['panel_width'] - 32, justify='left'
        )
        self.status_label.pack(fill='x', padx=PAD, pady=(6, 2))

        self.info_label = ctk.CTkLabel(
            self, text='',
            font=FONTS['tiny'], text_color=COLORS['text_muted'],
            wraplength=WINDOW['panel_width'] - 32, justify='left'
        )
        ##self.info_label.pack(fill='x', padx=PAD, pady=(0, 6))

        # ===== RU | EN | 🌙 | Инструкция =====
        bottom = ctk.CTkFrame(
            self,
            fg_color='transparent',
            width=WINDOW['panel_width'] - 2 * PAD,
            height=40
        )
        # Вместо pack используем place с привязкой к низу
        bottom.place(relx=0, rely=1.0, anchor='sw', x=PAD, y=-10)
        bottom.place(relx=0, rely=1.0, anchor='sw', x=PAD, y=-10)
        bottom.pack_propagate(False)  # <--- разрешаем фиксированную высоту
        # ===== СТАТУС (привязан к низу, над кнопками) =====
        # Высота нижних кнопок = 34px + отступ 10px = 44px.
        # Ставим статус-бар на y=-54 (44 + 10 отступ).
        self.status_label.place(relx=0, rely=1.0, x=PAD, y=-54, anchor='sw')
        self.info_label.place(relx=0, rely=1.0, x=PAD, y=-74, anchor='sw')

        self.lang_ru = ctk.CTkButton(
            bottom, text='RU', width=44, height=30, corner_radius=6,
            fg_color=COLORS['primary'] if i18n.lang == 'ru' else COLORS['bg_hover'],
            hover_color=COLORS['primary_hover'],
            text_color=COLORS['text_on_primary'] if i18n.lang == 'ru' else COLORS['text_primary'],
            font=FONTS['small_bold'],
            command=lambda: self._switch_lang('ru'),
        )
        self.lang_ru.pack(side='left')

        self.lang_en = ctk.CTkButton(
            bottom, text='EN', width=44, height=30, corner_radius=6,
            fg_color=COLORS['primary'] if i18n.lang == 'en' else COLORS['bg_hover'],
            hover_color=COLORS['primary_hover'],
            text_color=COLORS['text_on_primary'] if i18n.lang == 'en' else COLORS['text_primary'],
            font=FONTS['small_bold'],
            command=lambda: self._switch_lang('en'),
        )
        self.lang_en.pack(side='left', padx=(6, 0))

        # ← НОВАЯ КНОПКА ТЕМЫ
        icon = '☀️' if theme_manager.is_dark() else '🌙'
        self.theme_btn = ctk.CTkButton(
            bottom, text=icon, width=36, height=30, corner_radius=6,
            fg_color=COLORS['bg_hover'],
            hover_color=COLORS['border'],
            text_color=COLORS['text_primary'],
            font=('Segoe UI', 16),
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side='left', padx=(6, 0))

        self.help_btn = ctk.CTkButton(
            bottom, text=t('btn.help'), height=30, corner_radius=6,
            fg_color=COLORS['bg_hover'],
            hover_color=COLORS['border'],
            text_color=COLORS['text_primary'],
            font=FONTS['small_bold'],
            command=lambda: self.on_help() if self.on_help else None,
        )
        self.help_btn.pack(side='right', fill='x', expand=True, padx=(8, 0))
        self._reg(self.help_btn, 'btn.help')

    def _toggle_multi_curve_btn(self):
        self.multi_curve_var.set(not self.multi_curve_var.get())

        if self.multi_curve_var.get():
            self.multi_curve_btn.configure(
                text=t('btn.multi_curve_on'),  # <--- ИЗМЕНИТЬ
                fg_color=COLORS['accent'],
                hover_color=COLORS['accent_hover'],
                text_color=COLORS['text_on_primary']
            )
            # Обновляем ключ в реестре, чтобы при смене языка
            # переводилось правильное состояние (ВКЛ)
            self._update_reg_key(self.multi_curve_btn, 'btn.multi_curve_on')
        else:
            self.multi_curve_btn.configure(
                text=t('btn.multi_curve_off'),  # <--- ИЗМЕНИТЬ
                fg_color=COLORS['bg_hover'],
                hover_color=COLORS['border'],
                text_color=COLORS['text_secondary']
            )
            self._update_reg_key(self.multi_curve_btn, 'btn.multi_curve_off')

        self.on_action('toggle_multi_curve')

    # ============================================================
    # ХЕЛПЕРЫ
    # ============================================================

    def _reg(self, widget, key):
        self._widgets_to_update.append((widget, key))

    def _update_reg_key(self, widget, new_key):
        """Обновляет ключ локализации для виджета в реестре."""
        for i, (w, key) in enumerate(self._widgets_to_update):
            if w == widget:
                self._widgets_to_update[i] = (widget, new_key)
                break

    # ============================================================
    # ПЕРЕКЛЮЧЕНИЕ ЯЗЫКА
    # ============================================================

    def _switch_lang(self, lang):
        if lang == i18n.lang:
            return
        i18n.set_lang(lang)
        self._update_lang_buttons()
        if self.on_language_change:
            self.on_language_change(lang)

    def _update_lang_buttons(self):
        self.lang_ru.configure(
            fg_color=COLORS['primary'] if i18n.lang == 'ru' else COLORS['bg_hover'],
            text_color=COLORS['text_on_primary'] if i18n.lang == 'ru' else COLORS['text_primary'],
        )
        self.lang_en.configure(
            fg_color=COLORS['primary'] if i18n.lang == 'en' else COLORS['bg_hover'],
            text_color=COLORS['text_on_primary'] if i18n.lang == 'en' else COLORS['text_primary'],
        )

    def _toggle_theme(self):
        from core.theme_manager import theme_manager
        theme_manager.toggle()

    def _retranslate(self):
        for widget, key in self._widgets_to_update:
            try:
                widget.configure(text=t(key))
            except Exception as e:
                print(f'[retranslate error] {key}: {e}')

    # ============================================================
    # ПУБЛИЧНЫЕ МЕТОДЫ
    # ============================================================

    def set_mode(self, mode):
        self.current_mode = mode

        self.btn_digitize.pack_forget()
        self.btn_assign.pack_forget()
        self.multi_curve_btn.pack_forget()

        if mode == '1d':
            self.btn_digitize.pack(fill='x')
        else:
            self.btn_assign.pack(fill='x')
            self.multi_curve_btn.pack(fill='x', pady=(4, 0))  # <--- Уменьшили отступ

    def set_status(self, text):
        self.status_label.configure(text=text)

    def set_info(self, text):
        self.info_label.configure(text=text)