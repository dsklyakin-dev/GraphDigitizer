import customtkinter as ctk
from config.settings import COLORS, FONTS
from utils.smoothing import smooth_moving_average, smooth_savgol


class SmoothingDialog(ctk.CTkToplevel):
    def __init__(self, parent, data_points, on_apply_callback):
        super().__init__(parent)
        self.title("Сглаживание данных")
        self.geometry("480x400")
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_main'])

        # Делаем окно модальным, но безопасно
        self.transient(parent)

        self.data_points = data_points
        self.on_apply = on_apply_callback

        # Флаг, чтобы не обрабатывать закрытие дважды
        self._is_closing = False

        self._build_ui()

        # Центрирование окна
        self.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()

        x = parent_x + (parent_w - 480) // 2
        y = parent_y + (parent_h - 400) // 2
        self.geometry(f'+{x}+{y}')

        # Перехватываем закрытие крестиком
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        # Ждем закрытия (без grab_set, чтобы не было глюков с фокусом)
        parent.wait_window(self)

    def _build_ui(self):
        # Основной контейнер с отступами
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=30, pady=20)

        ctk.CTkLabel(
            main_frame, text="Настройки сглаживания",
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        ).pack(pady=(0, 20))

        # --- Метод ---
        ctk.CTkLabel(
            main_frame, text="Метод:",
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(anchor='w', pady=(0, 4))

        self.method_var = ctk.StringVar(value="Скользящее среднее")
        self.method_menu = ctk.CTkOptionMenu(
            main_frame, values=["Скользящее среднее", "Савицкий-Голей (лучше для пиков)"],
            variable=self.method_var,
            fg_color=COLORS['bg_hover'],
            button_color=COLORS['border'],
            button_hover_color=COLORS['accent'],
            dropdown_fg_color=COLORS['bg_panel'],
            font=FONTS['small'],
        )
        self.method_menu.pack(fill='x', pady=(0, 15))

        # --- Сила сглаживания ---
        ctk.CTkLabel(
            main_frame, text="Окно сглаживания (чем больше, тем глаже):",
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(anchor='w', pady=(0, 4))

        self.window_var = ctk.IntVar(value=5)
        self.window_slider = ctk.CTkSlider(
            main_frame, from_=3, to=21, number_of_steps=9,
            variable=self.window_var,
            command=self._on_slider_change,
            progress_color=COLORS['accent'],
        )
        self.window_slider.pack(fill='x', pady=(0, 4))

        self.window_label = ctk.CTkLabel(
            main_frame, text="5",
            font=FONTS['small_bold'], text_color=COLORS['text_primary']
        )
        self.window_label.pack(anchor='e')

        # --- Кнопки (в самом низу, прижаты) ---
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(fill='x', padx=30, pady=(0, 20), side='bottom')

        ctk.CTkButton(
            btn_frame, text="Отмена", height=44, fg_color=COLORS['bg_hover'],
            hover_color=COLORS['border'], font=FONTS['button'],
            command=self._cancel
        ).pack(side='left', fill='x', expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Применить", height=44, fg_color=COLORS['success'],
            hover_color=COLORS['success_hover'], font=FONTS['button'],
            command=self._apply
        ).pack(side='left', fill='x', expand=True, padx=(8, 0))

    def _on_slider_change(self, value):
        # Делаем значение нечётным (для Савицкого-Голея это важно)
        val = int(value)
        if val % 2 == 0:
            val += 1
        self.window_var.set(val)
        self.window_label.configure(text=str(val))

    def _apply(self):
        if self._is_closing:
            return
        self._is_closing = True

        window = self.window_var.get()
        method = self.method_var.get()

        # Показываем, что идет расчет (курсор-часики)
        self.config(cursor='watch')
        self.update()

        try:
            if method == "Скользящее среднее":
                smoothed = smooth_moving_average(self.data_points, window)
            else:
                smoothed = smooth_savgol(self.data_points, window, polyorder=2)

            self.on_apply(smoothed)
        except Exception as e:
            print(f"[Smoothing Error] {e}")
        finally:
            self._close_window()

    def _cancel(self):
        if self._is_closing:
            return
        self._is_closing = True
        self._close_window()

    def _close_window(self):
        """Безопасное закрытие окна без ошибок фокуса (обход бага CustomTkinter)."""
        try:
            # 1. Снимаем фокус со всех виджетов окна
            self.focus_set()

            # 2. Прячем окно, чтобы пользователь не видел мерцания
            self.withdraw()

            # 3. Ждём 50 мс, чтобы все отложенные таймеры CTk отработали
            self.after(50, self._really_destroy)
        except Exception:
            self.destroy()

    def _really_destroy(self):
        """Реально уничтожает окно после того, как таймеры фокуса отработали."""
        try:
            self.destroy()
        except Exception:
            pass