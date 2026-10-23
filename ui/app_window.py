"""
Главное окно приложения с оцифровкой кривых.
v8.0 — Toast-уведомления, OCR, точка начала координат, авто-выравнивание
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
import numpy as np

from config.settings import COLORS, FONTS, WINDOW, APP_NAME, APP_VERSION, CURVE_COLORS
from ui.canvas_widget import GraphCanvas
from ui.control_panel import ControlPanel
from ui.dialogs import CalibrationDialog
from ui.data_dialogs import DataViewerDialog, X2Dialog
from ui.help_dialog import HelpDialog
from ui.poly_dialog import PolyDialog
from ui.poly_result_dialog import PolyResultDialog
from ui.toast import Toast
from core.image_loader import ImageLoader
from core.calibrator import Calibrator
from core.axis_detector import AxisDetector
from core.curve_detector import CurveDetector
from core.undo_manager import UndoManager
from core.aligner import auto_align
from core.ocr_reader import OCRReader, is_available as ocr_available
from core.i18n import i18n, t
from utils.image_utils import cv2_to_pil
from utils.export import export_1d_data, export_2d_data
from core.theme_manager import theme_manager


class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f'{t("app.title")} v{APP_VERSION}')
        self.geometry(f'{WINDOW["width"]}x{WINDOW["height"]}')
        self.minsize(WINDOW['min_width'], WINDOW['min_height'])
        self.configure(fg_color=COLORS['bg_main'])

        # Данные
        self.image_loader = ImageLoader()
        self.calibrator = Calibrator()
        self.undo_manager = UndoManager()
        self.graph_mode = '1d'
        self.multi_curve_mode = False

        # Режим работы
        self.mode = 'normal'

        # Точки
        self.data_points_1d = []
        self.data_points_2d = {}
        self.current_curve = None

        # Временное состояние
        self.temp_points = []

        # Рисование
        self._segment_points = []
        self._pencil_points = []
        self._pencil_old_image = None
        self._drag_index = None
        self._drag_curve = None
        self.delete_radius = 10

        self.curve_color_index = 0

        # UI
        self._build_ui()
        self._bind_hotkeys()
        self._update_legend()

        # Toast поверх canvas
        self.toast = Toast(self)  # ← от главного окна

        # Подписка на смену языка
        i18n.on_change(self._on_language_changed)
        theme_manager.on_change(self._on_theme_changed)

    # Устанавливаем тему из настроек (по умолчанию — light)
    import customtkinter as ctk
    ctk.set_appearance_mode(theme_manager.current)

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color='transparent', corner_radius=0)
        container.pack(fill='both', expand=True)

        # Правая панель управления
        self.panel = ControlPanel(
            container,
            on_action=self._handle_action,
            on_language_change=self._on_language_changed,
            on_help=self._open_help,
        )
        self.panel.pack(side='right', fill='y')

        # ========== ПАНЕЛЬ-ЛЕГЕНДА ==========
        self.legend_panel = ctk.CTkFrame(
            container,
            width=200,
            corner_radius=WINDOW['corner_radius'],
            fg_color=COLORS['bg_panel'],
            border_width=1,
            border_color=COLORS['border']
        )

        legend_header = ctk.CTkFrame(self.legend_panel, fg_color='transparent', height=44)
        legend_header.pack(fill='x', padx=14, pady=(14, 4))
        legend_header.pack_propagate(False)

        self.legend_title = ctk.CTkLabel(
            legend_header, text=t('panel.legend'),
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        )
        self.legend_title.pack(anchor='w', pady=8)

        self.legend_scroll = ctk.CTkScrollableFrame(
            self.legend_panel,
            fg_color='transparent',
            scrollbar_button_color=COLORS['border'],
        )
        self.legend_scroll.pack(fill='both', expand=True, padx=8, pady=(0, 12))

        # ========== CANVAS ==========
        canvas_container = ctk.CTkFrame(
            container,
            fg_color=COLORS['bg_panel'],
            corner_radius=WINDOW['corner_radius'],
            border_width=1,
            border_color=COLORS['border']
        )
        canvas_container.pack(side='left', fill='both', expand=True,
                              padx=(12, 6), pady=12)

        canvas_header = ctk.CTkFrame(canvas_container, fg_color='transparent', height=56)
        canvas_header.pack(fill='x', padx=14, pady=(10, 0))
        canvas_header.pack_propagate(False)

        self.canvas_title = ctk.CTkLabel(
            canvas_header, text=t('panel.canvas'),
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        )
        self.canvas_title.pack(side='left', pady=10)

        # Переключатель 1D / 2D / Формула
        mode_switch_frame = ctk.CTkFrame(
            canvas_header,
            fg_color=COLORS['bg_hover'],
            corner_radius=10,
            height=44
        )
        mode_switch_frame.pack(side='left', padx=(20, 0), pady=8)

        self.mode_btn_1d = ctk.CTkButton(
            mode_switch_frame,
            text=t('mode.1d'),
            width=140,
            height=38,
            corner_radius=8,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            font=FONTS['small_bold'],
            command=lambda: self._set_mode('1d')
        )
        self.mode_btn_1d.pack(side='left', padx=3, pady=3)

        self.mode_btn_2d = ctk.CTkButton(
            mode_switch_frame,
            text=t('mode.2d'),
            width=140,
            height=38,
            corner_radius=8,
            fg_color='transparent',
            hover_color=COLORS['border'],
            text_color=COLORS['text_secondary'],
            font=FONTS['small_bold'],
            command=lambda: self._set_mode('2d')
        )
        self.mode_btn_2d.pack(side='left', padx=3, pady=3)

        self.mode_btn_poly = ctk.CTkButton(
            mode_switch_frame,
            text=t('mode.poly'),
            width=140,
            height=38,
            corner_radius=8,
            fg_color='transparent',
            hover_color=COLORS['border'],
            text_color=COLORS['text_secondary'],
            font=FONTS['small_bold'],
            command=self._open_poly_dialog,
        )
        self.mode_btn_poly.pack(side='left', padx=3, pady=3)

        self.canvas_info = ctk.CTkLabel(
            canvas_header, text=t('panel.no_image'),
            font=FONTS['small'], text_color=COLORS['text_muted']
        )
        self.canvas_info.pack(side='right', pady=10)

        divider = ctk.CTkFrame(canvas_container, fg_color=COLORS['border'], height=1)
        divider.pack(fill='x', padx=14, pady=(6, 0))

        self.canvas_widget = GraphCanvas(
            canvas_container,
            on_click=self._on_canvas_click,
            on_drag=self._on_canvas_drag,
            on_release=self._on_canvas_release,
            on_motion=self._on_canvas_motion,
            on_right_click=self._on_canvas_right_click,
            on_zoom_change=self._on_zoom_change,
        )
        self.canvas_widget.pack(fill='both', expand=True, padx=10, pady=10)
        self.canvas_widget.set_calib_marks_callback(self._draw_calibration)


    def _bind_hotkeys(self):
        self.bind_all('<F1>', lambda e: self._show_help())
        self.bind_all('<Control-o>', lambda e: self._open_image())
        self.bind_all('<Control-s>', lambda e: self._save_data())
        self.bind_all('<Control-0>', lambda e: self._reset_zoom())
        self.bind_all('<Escape>', lambda e: self._cancel_mode())
        self.bind_all('<KeyPress>', self._on_key_press)
        self.bind_all('<KeyRelease>', self._on_key_release)

    def _on_theme_changed(self, theme_name):
        """Обновляет UI при смене темы."""
        # Меняем режим CustomTkinter
        import customtkinter as ctk
        ctk.set_appearance_mode(theme_name)

        # Обновляем иконку на кнопке темы
        try:
            icon = '☀️' if theme_name == 'dark' else '🌙'
            self.panel.theme_btn.configure(text=icon)
        except Exception:
            pass

        # Предлагаем перезапуск
        from tkinter import messagebox
        from core.i18n import t
        answer = messagebox.askyesno(
            t('msg.confirm'),
            t('theme.restart_question'),
        )
        if answer:
            self._restart_app()

    def _restart_app(self):
        """Перезапускает приложение."""
        import sys
        import os
        import subprocess

        python = sys.executable
        script = os.path.abspath(sys.argv[0])

        try:
            subprocess.Popen([python, script])
        except Exception as e:
            print(f'[restart error] {e}')
        finally:
            self.destroy()

    def _on_key_press(self, event):
        ctrl_pressed = bool(event.state & 0x4)

        if event.keysym in ('Control_L', 'Control_R'):
            self.canvas_widget._set_ctrl(True)

        if ctrl_pressed and event.keycode in self._get_z_keycodes():
            self._undo()
            return

        if event.keysym == 'Return' and self.mode == 'digitizing' and self.graph_mode == '2d':
            self._finish_digitize_2d()

    def _get_z_keycodes(self):
        return {90, 35, 44, 20}

    def _on_key_release(self, event):
        if event.keysym in ('Control_L', 'Control_R'):
            self.canvas_widget._set_ctrl(False)

    # ============================================================
    # СМЕНА ЯЗЫКА
    # ============================================================

    def _on_language_changed(self, lang):
        """Обновляет интерфейс при смене языка."""
        try:
            self.title(f'{t("app.title")} v{APP_VERSION}')
            self.legend_title.configure(text=t('panel.legend'))
            self.canvas_title.configure(text=t('panel.canvas'))
            self.mode_btn_1d.configure(text=t('mode.1d'))
            self.mode_btn_2d.configure(text=t('mode.2d'))
            self.mode_btn_poly.configure(text=t('mode.poly'))
            if not self.image_loader.is_loaded():
                self.canvas_info.configure(text=t('panel.no_image'))
            self._update_legend()
        except Exception as e:
            print(f'[lang change error] {e}')

    def _open_help(self):
        HelpDialog(self)

    # ============================================================
    # ОБРАБОТКА ДЕЙСТВИЙ
    # ============================================================

    def _handle_action(self, action):
        handlers = {
            'open_image': self._open_image,
            'mode_1d': lambda: self._set_mode('1d'),
            'mode_2d': lambda: self._set_mode('2d'),
            'auto_calib': self._auto_calibrate,
            'manual_calib': self._start_manual_calib,
            'toggle_multi_curve': self._toggle_multi_curve,
            'digitize_auto': self._start_digitize,
            'assign_curve': self._start_digitize,
            'tool_manual': self._start_manual_points,
            'tool_drag': self._start_drag,
            'tool_delete': self._start_delete,
            'tool_pencil': self._start_pencil,
            'tool_segment': self._start_segment,
            'undo': self._undo,
            'show_data': self._show_data,
            'clear_all': self._clear_all,
            'save_data': self._save_data,
            'smooth_data': self._open_smoothing_dialog,  # <--- ДОБАВИТЬ
            'clear_all': self._clear_all,
            'save_data': self._save_data,
        }

        if action in handlers:
            handlers[action]()

    def _open_image(self):
        path = filedialog.askopenfilename(
            title=t('btn.open'),
            filetypes=[
                ('Images', '*.jpg *.jpeg *.png *.bmp *.tiff'),
                ('All files', '*.*')
            ]
        )
        if not path:
            return

        if self.image_loader.load(path):
            pil_img = cv2_to_pil(self.image_loader.current)
            self.canvas_widget.set_image(pil_img)

            h, w = self.image_loader.current.shape[:2]
            self.canvas_info.configure(text=f'{w} × {h} px')

            self.calibrator.reset()
            self.canvas_widget.clear_overlay()
            self.data_points_1d = []
            self.data_points_2d = {}
            self.undo_manager.clear()

            self._update_legend()

            calib_file = Path(path).with_name(Path(path).stem + '_calib.json')
            if calib_file.exists():
                if self.calibrator.load(str(calib_file)):
                    self._draw_calibration()
                    self.panel.set_status(t('status.image_loaded_calib'))
                    self.panel.set_info(f'{Path(path).name}')
                    return

            self.panel.set_status(t('status.image_loaded'))
            self.panel.set_info(f'{Path(path).name}')
        else:
            messagebox.showerror(t('msg.error'), t('msg.load_failed'))

    def _set_mode(self, mode):
        self.graph_mode = mode
        self.panel.set_mode(mode)

        modes = {
            '1d': (self.mode_btn_1d, COLORS['primary']),
            '2d': (self.mode_btn_2d, COLORS['accent']),
            'poly': (self.mode_btn_poly, COLORS['success']),
        }

        for key, (btn, color) in modes.items():
            if key == mode:
                btn.configure(
                    fg_color=color,
                    text_color=COLORS['text_on_primary']
                )
            else:
                btn.configure(
                    fg_color='transparent',
                    text_color=COLORS['text_secondary']
                )

        mode_text = {
            '1d': t('mode.1d_short'),
            '2d': t('mode.2d_short'),
            'poly': t('mode.poly_short'),
        }.get(mode, mode)

        self.panel.set_status(t('status.mode', mode=mode_text))
        self._redraw_points()
        self._update_legend()

    def _toggle_multi_curve(self):
        self.multi_curve_mode = self.panel.multi_curve_var.get()
        if self.multi_curve_mode:
            self.panel.set_status(t('status.multi_curve_on'))
        else:
            self.panel.set_status(t('status.multi_curve_off'))

    # ============================================================
    # ЛЕГЕНДА
    # ============================================================

    def _update_legend(self):
        for widget in self.legend_scroll.winfo_children():
            widget.destroy()

        if self.graph_mode != '2d' or not self.data_points_2d:
            self.legend_panel.pack_forget()
            return

        try:
            self.legend_panel.pack(side='left', fill='y', padx=(6, 0), pady=12,
                                   before=self.canvas_widget.master)
        except Exception:
            self.legend_panel.pack(side='left', fill='y', padx=(6, 0), pady=12)

        for idx, (curve_name, points) in enumerate(self.data_points_2d.items()):
            color = CURVE_COLORS[idx % len(CURVE_COLORS)]
            count = len(points)

            item = ctk.CTkFrame(
                self.legend_scroll,
                fg_color=COLORS['bg_hover'],
                corner_radius=8
            )
            item.pack(fill='x', pady=3, padx=2)

            dot = ctk.CTkFrame(
                item, width=16, height=16,
                fg_color=color,
                corner_radius=8
            )
            dot.pack(side='left', padx=(10, 8), pady=10)
            dot.pack_propagate(False)

            text_frame = ctk.CTkFrame(item, fg_color='transparent')
            text_frame.pack(side='left', fill='x', expand=True, pady=6)

            ctk.CTkLabel(
                text_frame, text=f'X2 = {curve_name}',
                font=FONTS['small_bold'],
                text_color=COLORS['text_primary'],
                anchor='w'
            ).pack(anchor='w')

            ctk.CTkLabel(
                text_frame, text=f'{count}',
                font=FONTS['tiny'],
                text_color=COLORS['text_secondary'],
                anchor='w'
            ).pack(anchor='w')

    # ============================================================
    # КАЛИБРОВКА
    # ============================================================

    def _auto_calibrate(self):
        """Авто-выравнивание + клик по началу координат + поиск концов осей."""
        if not self.image_loader.is_loaded():
            messagebox.showwarning(t('msg.warning'), t('msg.load_image_first'))
            return

        # ============================================================
        # ШАГ 1. Выравнивание
        # ============================================================
        self.panel.set_status(t('status.aligning'))
        if hasattr(self, 'toast'):
            self.toast.show(t('status.aligning'), duration=2, color='info')
        self.update()

        old_image = self.image_loader.current.copy()
        self.undo_manager.push({
            'type': 'align',
            'data': old_image,
        })

        aligned, angle = auto_align(self.image_loader.current)

        if aligned is not None:
            self.image_loader.current = aligned
            self.image_loader.original = aligned.copy()
            pil = cv2_to_pil(self.image_loader.current)
            self.canvas_widget.set_image(pil)
            h, w = self.image_loader.current.shape[:2]
            self.canvas_info.configure(text=f'{w} × {h} px')
            self.calibrator.reset()
            self.canvas_widget.clear_overlay()
            self.data_points_1d = []
            self.data_points_2d = {}
            self.panel.set_status(t('status.align_done', angle=f'{angle:.2f}'))
            self.update()
        else:
            self.undo_manager.pop()

        # ============================================================
        # ШАГ 2. Автопоиск начала координат или клик
        # ============================================================
        # Сначала пробуем найти оси автоматически
        self.panel.set_status("Поиск начала координат...")
        self.update()

        detector = AxisDetector(self.image_loader.current)
        origin = detector.find_origin()

        if origin is not None:
            # Нашли автоматически — сразу запускаем обработку
            print(f'[AxisDetector] Автопоиск начала координат: {origin}')
            if hasattr(self, 'toast'):
                self.toast.show("Начало координат найдено автоматически", duration=3, color='success')
            self._handle_pick_origin(origin[0], origin[1])
        else:
            # Не нашли — просим кликнуть вручную
            self.mode = 'pick_origin'
            self.canvas_widget.canvas.configure(cursor='tcross')
            self.panel.set_status(t('status.pick_origin'))
            self.panel.set_info(t('status.pick_origin_hint'))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.pick_origin'), duration=8, color='warning')

    def _handle_pick_origin(self, img_x, img_y):
        """Обработка клика по началу координат."""
        if hasattr(self, 'toast'):
            self.toast.hide()

        detector = AxisDetector(self.image_loader.current)

        x_end = detector.find_x_end(img_x, img_y)
        y_end = detector.find_y_end(img_x, img_y)

        if x_end is None or y_end is None:
            self.panel.set_status(t('status.axes_not_found'))
            self.mode = 'normal'
            self.canvas_widget.canvas.configure(cursor='crosshair')
            return

        origin = (img_x, img_y)

        # Попытка OCR
        ocr_result = None
        if ocr_available():
            try:
                reader = OCRReader(self.image_loader.current)
                ocr_result = reader.read_axis_labels(origin, x_end, y_end)
                print(f'[OCR] результат: {ocr_result}')
            except Exception as e:
                print(f'[OCR] ошибка: {e}')

        self._draw_auto_detection(origin, x_end, y_end)

        self.mode = 'normal'
        self.canvas_widget.canvas.configure(cursor='crosshair')

        # Defaults с OCR
        defaults = dict(self.calibrator.field_values)
        if ocr_result:
            if 'x0' in ocr_result:
                defaults['X0'] = str(ocr_result['x0'])
            if 'y0' in ocr_result:
                defaults['Y0'] = str(ocr_result['y0'])
            if 'x1' in ocr_result:
                defaults['X1'] = str(ocr_result['x1'])
            if 'y1' in ocr_result:
                defaults['Y1'] = str(ocr_result['y1'])

        dialog = CalibrationDialog(
            self,
            defaults=defaults,
            title=t('btn.auto_calib')
        )

        if dialog.result is None:
            self.canvas_widget.clear_overlay()
            self._draw_calibration()
            return

        values = dialog.result
        self.calibrator.set_from_axis_detection(
            origin, x_end, y_end,
            values['X0'], values['Y0'], values['X1'], values['Y1']
        )

        self._save_calibration()
        self.canvas_widget.clear_overlay()
        self._draw_calibration()

        self.panel.set_status(t('status.calib_done'))
        self.panel.set_info(t('status.can_digitize'))

        if hasattr(self, 'toast'):
            self.toast.show(t('toast.calib_done'), duration=3, color='success')

    def _draw_auto_detection(self, origin, x_end, y_end):
        self.canvas_widget.clear_overlay()
        self.canvas_widget.draw_point(origin[0], origin[1],
                                      color='#F59E0B', size=8, shape='cross')
        self.canvas_widget.draw_point(x_end[0], x_end[1],
                                      color='#3B82F6', size=8, shape='cross')
        self.canvas_widget.draw_point(y_end[0], y_end[1],
                                      color='#10B981', size=8, shape='cross')
        self.canvas_widget.draw_line(origin[0], origin[1], x_end[0], x_end[1],
                                     color='#3B82F6', width=2)
        self.canvas_widget.draw_line(origin[0], origin[1], y_end[0], y_end[1],
                                     color='#10B981', width=2)

    def _start_manual_calib(self):
        if not self.image_loader.is_loaded():
            messagebox.showwarning(t('msg.warning'), t('msg.load_image_first'))
            return

        dialog = CalibrationDialog(
            self,
            defaults=self.calibrator.field_values,
            title=t('btn.manual_calib')
        )

        if dialog.result is None:
            return

        values = dialog.result
        self.calibrator.field_values = {k: str(v) for k, v in values.items()}
        self.calibrator.points = {}
        self.calibrator.step = 0
        self.mode = 'calibrating'

        self.canvas_widget.clear_overlay()
        self.canvas_widget.canvas.configure(cursor='tcross')

        self.panel.set_status(t('status.click_origin'))
        self.panel.set_info(t('status.step_1_3'))

        if hasattr(self, 'toast'):
            self.toast.show(t('toast.click_origin'), duration=8, color='warning')

    def _handle_calibration_click(self, img_x, img_y):
        step = self.calibrator.step

        if step == 0:
            self.calibrator.points['origin'] = {
                'pixel': (img_x, img_y),
                'value': (float(self.calibrator.field_values['X0']),
                          float(self.calibrator.field_values['Y0'])),
            }
            self.canvas_widget.draw_point(img_x, img_y,
                                          color='#F59E0B', size=10, shape='cross')
            self.panel.set_status(t('status.click_x_end'))
            self.panel.set_info(t('status.step_2_3'))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.click_x_end'), duration=6, color='warning')

        elif step == 1:
            self.calibrator.points['x_max'] = {
                'pixel': (img_x, img_y),
                'value': (float(self.calibrator.field_values['X1']),
                          float(self.calibrator.field_values['Y0'])),
            }
            self.canvas_widget.draw_point(img_x, img_y,
                                          color='#3B82F6', size=10, shape='cross')
            o = self.calibrator.points['origin']['pixel']
            self.canvas_widget.draw_line(o[0], o[1], img_x, img_y,
                                         color='#3B82F6', width=2)
            self.panel.set_status(t('status.click_y_end'))
            self.panel.set_info(t('status.step_3_3'))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.click_y_end'), duration=6, color='warning')

        elif step == 2:
            self.calibrator.points['y_max'] = {
                'pixel': (img_x, img_y),
                'value': (float(self.calibrator.field_values['X0']),
                          float(self.calibrator.field_values['Y1'])),
            }
            self.canvas_widget.draw_point(img_x, img_y,
                                          color='#10B981', size=10, shape='cross')
            o = self.calibrator.points['origin']['pixel']
            self.canvas_widget.draw_line(o[0], o[1], img_x, img_y,
                                         color='#10B981', width=2)

            self.calibrator._recalc()
            self._save_calibration()

            self.mode = 'normal'
            self.canvas_widget.canvas.configure(cursor='crosshair')
            self.canvas_widget.clear_overlay()
            self._draw_calibration()

            self.panel.set_status(t('status.calib_finished'))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.calib_done'), duration=3, color='success')
            return

        self.calibrator.step += 1

    def _draw_calibration(self):
        if not self.calibrator.is_calibrated():
            return
        self.canvas_widget.draw_calibration_marks(self.calibrator)

    def _save_calibration(self):
        if not self.image_loader.path:
            return
        if not self.calibrator.is_calibrated():
            return
        calib_file = Path(self.image_loader.path).with_name(
            Path(self.image_loader.path).stem + '_calib.json'
        )
        self.calibrator.save(str(calib_file))

    # ============================================================
    # ОЦИФРОВКА
    # ============================================================

    def _start_digitize(self):
        if not self.calibrator.is_calibrated():
            messagebox.showwarning(t('msg.warning'), t('msg.calib_first'))
            return

        self.mode = 'digitizing'
        self.temp_points = []
        self.canvas_widget.canvas.configure(cursor='tcross')

        self._draw_existing_points()

        if self.graph_mode == '1d':
            self.panel.set_status(t('status.click_curve'))
            self.panel.set_info(t('status.auto_search'))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.click_curve'), duration=6, color='info')
        else:
            self.panel.set_status(t('status.click_points_enter'))
            self.panel.set_info(t('status.auto_search'))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.click_points_2d'), duration=8, color='info')

    def _handle_digitize_click(self, img_x, img_y):
        if hasattr(self, 'toast'):
            self.toast.hide()

        if self.graph_mode == '1d':
            self._digitize_1d(img_x, img_y)
        else:
            self._digitize_2d_click(img_x, img_y)

    def _digitize_1d(self, img_x, img_y):
        """Оцифровка 1D — водяной поток от точки."""
        if not self.calibrator.is_calibrated():
            self.panel.set_status(t('msg.calib_first'))
            return

        detector = CurveDetector(self.image_loader.current, self.calibrator)

        step = int(self.panel.step_entry.get() or 8)
        radius = int(self.panel.radius_entry.get() or 10)

        path = detector.water_flow(
            img_x, img_y,
            step_pixels=step,
            search_window=radius,
        )

        if len(path) < 3:
            self.panel.set_status(t('status.curve_not_found'))
            if hasattr(self, 'toast'):
                self.toast.show(t('status.curve_not_found'), duration=3, color='danger')
            return

        thinned = detector.thin_path(path, step_values=step)
        values = detector.pixels_to_values(thinned)
        values = sorted(values, key=lambda p: p[0])

        if values:
            dedup = [values[0]]
            for pt in values[1:]:
                if abs(pt[0] - dedup[-1][0]) > 1e-4 or abs(pt[1] - dedup[-1][1]) > 1e-4:
                    dedup.append(pt)
            values = dedup

        self.undo_manager.push({
            'type': '1d_points',
            'data': list(self.data_points_1d),
        })

        self.data_points_1d = values
        self._draw_existing_points()

        self.mode = 'normal'
        self.canvas_widget.canvas.configure(cursor='crosshair')
        self.panel.set_status(t('status.digitized', n=len(values)))
        self.panel.set_info(t('status.undo_hint'))

        if hasattr(self, 'toast'):
            self.toast.show(
                t('toast.digitize_done', n=len(values)),
                duration=3, color='success'
            )

    def _digitize_2d_click(self, img_x, img_y):
        self.temp_points.append((img_x, img_y))
        idx = len(self.temp_points)

        if idx == 1:
            color = '#10B981'
        else:
            color = '#F59E0B'

        self.canvas_widget.draw_point(img_x, img_y, color=color, size=8, shape='cross')

        if idx >= 2:
            p1 = self.temp_points[-2]
            p2 = self.temp_points[-1]
            self.canvas_widget.draw_line(p1[0], p1[1], p2[0], p2[1],
                                         color='#3B82F6', width=2, dash=(4, 4))

        self.panel.set_status(t('status.points_count', n=idx))

    def _finish_digitize_2d(self):
        if len(self.temp_points) < 2:
            self.panel.set_status(t('status.points_needed_2'))
            return

        dlg = X2Dialog(self)
        if dlg.result is None:
            self.temp_points = []
            self._draw_existing_points()
            self.panel.set_status(t('status.cancelled'))
            return

        x2_value = dlg.result

        if self.multi_curve_mode:
            best_match = self._find_matching_curve(x2_value)
            if best_match:
                count = len(self.data_points_2d[best_match])
                answer = messagebox.askyesno(
                    t('msg.compat_coords'),
                    t('msg.compat_found', name=best_match, n=count, new=x2_value)
                )
                if answer:
                    old = self.data_points_2d.get(x2_value, []).copy()
                    self.undo_manager.push({
                        'type': '2d_points',
                        'data': {'curve': x2_value, 'old_points': old},
                    })

                    new_vals = [list(p) for p in self.data_points_2d[best_match]]
                    self.data_points_2d[x2_value] = sorted(new_vals, key=lambda p: p[0])
                    self.current_curve = x2_value

                    self.temp_points = []
                    self._draw_existing_points()
                    self.canvas_widget.canvas.configure(cursor='crosshair')
                    self.mode = 'normal'
                    self._update_legend()
                    self.panel.set_status(
                        t('status.curve_points_copied', name=x2_value, n=len(new_vals))
                    )
                    return

        detector = CurveDetector(self.image_loader.current, self.calibrator)
        step = int(self.panel.step_entry.get() or 8)
        radius = int(self.panel.radius_entry.get() or 14)

        all_paths = []

        for i in range(len(self.temp_points) - 1):
            p1 = self.temp_points[i]
            p2 = self.temp_points[i + 1]

            path = detector.water_flow(
                p1[0], p1[1],
                end_x=p2[0], end_y=p2[1],
                step_pixels=step,
                search_window=max(5, radius // 2),
            )

            if len(path) >= 2:
                if i > 0 and all_paths:
                    path = path[1:]
                all_paths.extend(path)

        if len(all_paths) < 3:
            self.panel.set_status(t('status.curve_not_found'))
            self.temp_points = []
            return

        thinned = detector.thin_path(all_paths, step_values=step)
        values = detector.pixels_to_values(thinned)
        values = sorted(values, key=lambda p: p[0])

        old = self.data_points_2d.get(x2_value, []).copy()
        self.undo_manager.push({
            'type': '2d_points',
            'data': {'curve': x2_value, 'old_points': old},
        })

        all_vals = old + values
        all_vals.sort(key=lambda p: p[0])
        if all_vals:
            dedup = [all_vals[0]]
            for pt in all_vals[1:]:
                if abs(pt[0] - dedup[-1][0]) > 1e-4 or abs(pt[1] - dedup[-1][1]) > 1e-4:
                    dedup.append(pt)
            self.data_points_2d[x2_value] = dedup
        else:
            self.data_points_2d[x2_value] = values

        self.current_curve = x2_value
        self.temp_points = []

        self._draw_existing_points()
        self.canvas_widget.canvas.configure(cursor='crosshair')
        self.mode = 'normal'
        self._update_legend()
        self.panel.set_status(t('status.curve_points', name=x2_value, n=len(values)))

        if hasattr(self, 'toast'):
            self.toast.show(
                t('toast.digitize_done', n=len(values)),
                duration=3, color='success'
            )

    def _find_matching_curve(self, exclude_curve):
        if not self.temp_points:
            return None

        best_match = None
        best_score = 0
        threshold = 10

        for curve_name, points in self.data_points_2d.items():
            if curve_name == exclude_curve or not points:
                continue

            matched = 0
            for tx, ty in self.temp_points:
                min_dist = float('inf')
                for px_val, py_val in points:
                    px, py = self.calibrator.val_to_px(px_val, py_val)
                    dist = np.sqrt((px - tx) ** 2 + (py - ty) ** 2)
                    if dist < min_dist:
                        min_dist = dist

                if min_dist < threshold:
                    matched += 1

            score = matched / len(self.temp_points)
            if score > best_score and score >= 0.5:
                best_score = score
                best_match = curve_name

        return best_match

    def _draw_existing_points(self):
        self.canvas_widget.clear_overlay()

        if self.graph_mode == '1d':
            if self.calibrator.is_calibrated():
                for x, y in self.data_points_1d:
                    px, py = self.calibrator.val_to_px(x, y)
                    self.canvas_widget.draw_point(px, py,
                                                  color='#EF4444', size=3,
                                                  outline='white')
        else:
            for idx, (curve_name, points) in enumerate(self.data_points_2d.items()):
                color = CURVE_COLORS[idx % len(CURVE_COLORS)]
                for x, y in points:
                    px, py = self.calibrator.val_to_px(x, y)
                    self.canvas_widget.draw_point(px, py,
                                                  color=color, size=3,
                                                  outline='white')

        self._draw_calibration()

    def _redraw_points(self):
        self._draw_existing_points()

    # ============================================================
    # ИНСТРУМЕНТЫ
    # ============================================================

    def _start_manual_points(self):
        if not self.calibrator.is_calibrated():
            messagebox.showwarning(t('msg.warning'), t('msg.calib_first'))
            return
        self.mode = 'manual_point'
        self.canvas_widget.canvas.configure(cursor='tcross')
        self.panel.set_status(t('status.click_points_esc'))
        if hasattr(self, 'toast'):
            self.toast.show(t('toast.click_points_esc'), duration=6, color='info')

    def _handle_manual_point(self, img_x, img_y):
        if not self.calibrator.is_calibrated():
            return
        x_val, y_val = self.calibrator.px_to_val(img_x, img_y)

        if self.graph_mode == '1d':
            old = list(self.data_points_1d)
            self.undo_manager.push({'type': '1d_points', 'data': old})

            self.data_points_1d.append([x_val, y_val])
            self.data_points_1d.sort(key=lambda p: p[0])
        else:
            if self.current_curve is None:
                dlg = X2Dialog(self)
                if dlg.result is None:
                    return
                self.current_curve = dlg.result
                self.data_points_2d.setdefault(self.current_curve, [])

            old = list(self.data_points_2d.get(self.current_curve, []))
            self.undo_manager.push({
                'type': '2d_points',
                'data': {'curve': self.current_curve, 'old_points': old},
            })

            self.data_points_2d[self.current_curve].append([x_val, y_val])
            self.data_points_2d[self.current_curve].sort(key=lambda p: p[0])

        self._draw_existing_points()
        self._update_legend()

    def _start_drag(self):
        if not self._has_points():
            messagebox.showinfo(t('msg.warning'), t('msg.no_points'))
            return
        self.mode = 'dragging'
        self.canvas_widget.canvas.configure(cursor='hand2')
        self.panel.set_status(t('status.drag_point'))
        if hasattr(self, 'toast'):
            self.toast.show(t('toast.drag_mode'), duration=6, color='info')
        self._drag_index = None
        self._drag_curve = None

    def _has_points(self):
        if self.graph_mode == '1d':
            return len(self.data_points_1d) > 0
        return any(len(p) > 0 for p in self.data_points_2d.values())

    def _start_delete(self):
        if not self._has_points():
            messagebox.showinfo(t('msg.warning'), t('msg.no_points_to_delete'))
            return

        self.mode = 'deleting'
        self.delete_radius = 10
        self._deleted_count = 0

        self.undo_manager.push({
            'type': 'delete',
            'data': {
                'graph_mode': self.graph_mode,
                '1d': list(self.data_points_1d),
                '2d': {k: list(v) for k, v in self.data_points_2d.items()},
            }
        })

        self.canvas_widget.canvas.configure(cursor='circle')
        self.panel.set_status(t('status.delete_mode'))
        if hasattr(self, 'toast'):
            self.toast.show(t('toast.delete_mode'), duration=6, color='danger')

    def _handle_delete(self, img_x, img_y):
        radius = self.delete_radius

        if self.graph_mode == '1d':
            new_points = []
            for x, y in self.data_points_1d:
                px, py = self.calibrator.val_to_px(x, y)
                dist = np.sqrt((px - img_x) ** 2 + (py - img_y) ** 2)
                if dist > radius:
                    new_points.append([x, y])
            self._deleted_count += len(self.data_points_1d) - len(new_points)
            self.data_points_1d = new_points
        else:
            for curve_name, points in self.data_points_2d.items():
                new_points = []
                for x, y in points:
                    px, py = self.calibrator.val_to_px(x, y)
                    dist = np.sqrt((px - img_x) ** 2 + (py - img_y) ** 2)
                    if dist > radius:
                        new_points.append([x, y])
                self._deleted_count += len(points) - len(new_points)
                self.data_points_2d[curve_name] = new_points

        self._draw_existing_points()
        self._update_legend()

    def _start_pencil(self):
        self.mode = 'pencil'
        self._pencil_points = []
        self.canvas_widget.canvas.configure(cursor='pencil')
        self.panel.set_status(t('status.pencil_mode'))
        if hasattr(self, 'toast'):
            self.toast.show(t('toast.pencil_mode'), duration=6, color='info')

    def _handle_pencil(self, img_x, img_y):
        if not self._pencil_points:
            old_copy = self.image_loader.current.copy()
            self.undo_manager.push({
                'type': 'segment',
                'data': old_copy,
            })

        self._pencil_points.append((img_x, img_y))
        if len(self._pencil_points) >= 2:
            import cv2
            p1 = self._pencil_points[-2]
            p2 = self._pencil_points[-1]
            cv2.line(self.image_loader.current, p1, p2, (0, 0, 0), 2)

            pil = cv2_to_pil(self.image_loader.current)
            self.canvas_widget.set_image(pil)
            self._draw_existing_points()

    def _finish_pencil(self):
        if not self._pencil_points:
            self._pencil_points = []
            self._pencil_old_image = None
            return

        self.image_loader.original = self.image_loader.current.copy()

        self._pencil_points = []
        self._pencil_old_image = None

        self.panel.set_status(t('status.pencil_done'))

    def _start_segment(self):
        self.mode = 'segment'
        self._segment_points = []
        self.canvas_widget.canvas.configure(cursor='tcross')
        self.panel.set_status(t('status.segment_first'))
        if hasattr(self, 'toast'):
            self.toast.show(t('toast.segment_first'), duration=6, color='info')

    def _handle_segment(self, img_x, img_y):
        self._segment_points.append((img_x, img_y))

        if len(self._segment_points) == 1:
            self.canvas_widget.draw_point(img_x, img_y,
                                          color='#8B5CF6', size=6, shape='circle')
            self.panel.set_status(t('status.segment_second'))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.segment_second'), duration=6, color='info')
        else:
            import cv2
            old_image = self.image_loader.current.copy()

            p1 = self._segment_points[0]
            p2 = self._segment_points[1]
            cv2.line(self.image_loader.current, p1, p2, (0, 0, 0), 2)

            self.image_loader.original = self.image_loader.current.copy()

            self.undo_manager.push({
                'type': 'segment',
                'data': old_image,
            })

            pil = cv2_to_pil(self.image_loader.current)
            self.canvas_widget.set_image(pil)
            self._draw_existing_points()

            self._segment_points = []
            self.panel.set_status(t('status.segment_done'))

    def _open_smoothing_dialog(self):
        """Открывает диалог сглаживания для активного режима."""
        if self.graph_mode == '1d':
            if len(self.data_points_1d) < 5:
                messagebox.showwarning(t('msg.warning'), "Слишком мало точек для сглаживания (нужно минимум 5).")
                return
            data = self.data_points_1d
        else:
            if not any(len(p) >= 5 for p in self.data_points_2d.values()):
                messagebox.showwarning(t('msg.warning'),
                                       "Слишком мало точек для сглаживания (нужно минимум 5 в кривой).")
                return
            # Для 2D сглаживаем только выбранную кривую
            if self.current_curve is None or self.current_curve not in self.data_points_2d:
                messagebox.showwarning(t('msg.warning'), "Выберите кривую в легенде или кликните по ней.")
                return
            data = self.data_points_2d[self.current_curve]

        from ui.smoothing_dialog import SmoothingDialog
        SmoothingDialog(self, data, self._apply_smoothed_data)

    def _apply_smoothed_data(self, smoothed_points):
        """Применяет сглаженные точки к текущему режиму."""
        # Сохраняем в Undo
        if self.graph_mode == '1d':
            self.undo_manager.push({
                'type': '1d_points',
                'data': list(self.data_points_1d),
            })
            self.data_points_1d = smoothed_points
        else:
            curve = self.current_curve
            old = list(self.data_points_2d.get(curve, []))
            self.undo_manager.push({
                'type': '2d_points',
                'data': {'curve': curve, 'old_points': old},
            })
            self.data_points_2d[curve] = smoothed_points

        # Перерисовываем график
        self._draw_existing_points()
        self._update_legend()

        self.panel.set_status(f"Сглаживание применено. Точек: {len(smoothed_points)}")
        if hasattr(self, 'toast'):
            self.toast.show("Сглаживание применено", duration=3, color='success')

    # ============================================================
    # ОТМЕНА / ОЧИСТКА / ЭКСПОРТ
    # ============================================================

    def _undo(self):
        action = self.undo_manager.pop()
        if action is None:
            self.panel.set_status(t('status.nothing_to_undo'))
            return

        t_type = action['type']
        if t_type == '1d_points':
            self.data_points_1d = action['data']
            self._draw_existing_points()
            self.panel.set_status(t('status.cancelled'))
        elif t_type == '2d_points':
            curve = action['data']['curve']
            old = action['data']['old_points']
            if old:
                self.data_points_2d[curve] = old
            elif curve in self.data_points_2d:
                del self.data_points_2d[curve]
            self._draw_existing_points()
            self._update_legend()
            self.panel.set_status(t('status.cancelled') + f': {curve}')
        elif t_type == 'delete':
            self.data_points_1d = action['data']['1d']
            self.data_points_2d = action['data']['2d']
            self._draw_existing_points()
            self._update_legend()
            self.panel.set_status(t('status.delete_cancelled'))
        elif t_type == 'segment':
            if action['data'] is not None:
                self.image_loader.current = action['data'].copy()
                self.image_loader.original = action['data'].copy()
                pil = cv2_to_pil(self.image_loader.current)
                self.canvas_widget.set_image(pil)
                self._draw_existing_points()
                self.panel.set_status(t('status.drawing_cancelled'))
            else:
                self.panel.set_status(t('status.nothing_to_undo'))
        elif t_type == 'align':
            if action['data'] is not None:
                self.image_loader.current = action['data'].copy()
                self.image_loader.original = action['data'].copy()
                pil = cv2_to_pil(self.image_loader.current)
                self.canvas_widget.set_image(pil)
                h, w = self.image_loader.current.shape[:2]
                self.canvas_info.configure(text=f'{w} × {h} px')
                self.calibrator.reset()
                self.canvas_widget.clear_overlay()
                self.data_points_1d = []
                self.data_points_2d = {}
                self._draw_existing_points()
                self._update_legend()
                self.panel.set_status(t('status.align_undone'))
            else:
                self.panel.set_status(t('status.nothing_to_undo'))
        else:
            self.panel.set_status(t('status.cancelled'))

    def _show_data(self):
        if self.graph_mode == '1d':
            if not self.data_points_1d:
                messagebox.showinfo(t('msg.warning'), t('msg.no_data'))
                return
            data = self.data_points_1d
        else:
            if not any(self.data_points_2d.values()):
                messagebox.showinfo(t('msg.warning'), t('msg.no_data'))
                return
            data = self.data_points_2d

        # X3 только для 2D
        x3_value = None
        if self.graph_mode == '2d':
            need_x3 = messagebox.askyesno(t('msg.x3_title'), t('msg.x3_question'))
            if need_x3:
                x3_value = simpledialog.askstring(t('msg.x3_title'), t('msg.x3_prompt'))

        DataViewerDialog(self, data, self.graph_mode, x3_value)

    def _save_data(self):
        if self.graph_mode == '1d':
            if not self.data_points_1d:
                messagebox.showinfo(t('msg.warning'), t('msg.no_data'))
                return
        else:
            if not any(self.data_points_2d.values()):
                messagebox.showinfo(t('msg.warning'), t('msg.no_data'))
                return

        # X3 только для 2D
        x3_value = None
        if self.graph_mode == '2d':
            need_x3 = messagebox.askyesno(t('msg.x3_title'), t('msg.x3_question'))
            if need_x3:
                x3_value = simpledialog.askstring(t('msg.x3_title'), t('msg.x3_prompt'))
                if not x3_value:
                    need_x3 = False

        path = filedialog.asksaveasfilename(
            title=t('btn.save'),
            defaultextension='.xlsx',
            filetypes=[('Excel', '*.xlsx'), ('CSV', '*.csv')]
        )
        if not path:
            return

        if self.graph_mode == '1d':
            ok = export_1d_data(self.data_points_1d, x3_value, path)
        else:
            ok = export_2d_data(self.data_points_2d, x3_value, path)

        if ok:
            messagebox.showinfo(t('msg.done'), t('msg.saved', path=path))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.saved'), duration=3, color='success')
        else:
            messagebox.showerror(t('msg.error'), t('msg.save_failed'))

    def _clear_all(self):
        if not messagebox.askyesno(t('msg.confirm'), t('msg.clear_confirm')):
            return
        self.data_points_1d = []
        self.data_points_2d = {}
        self.current_curve = None
        self.undo_manager.clear()
        self._draw_existing_points()
        self._update_legend()
        self.panel.set_status(t('status.cleared'))

    # ============================================================
    # CANVAS EVENTS
    # ============================================================

    def _on_canvas_click(self, cx, cy, img_x, img_y):
        # Скрываем текущий toast, если он есть
        if hasattr(self, 'toast'):
            self.toast.hide()

        if self.mode == 'pick_origin':
            self._handle_pick_origin(img_x, img_y)
            return True
        elif self.mode == 'calibrating':
            self._handle_calibration_click(img_x, img_y)
            return True
        elif self.mode == 'digitizing':
            self._handle_digitize_click(img_x, img_y)
            return True
        elif self.mode == 'manual_point':
            self._handle_manual_point(img_x, img_y)
            return True
        elif self.mode == 'dragging':
            self._find_drag_point(img_x, img_y)
            return True
        elif self.mode == 'deleting':
            self._handle_delete(img_x, img_y)
            return True
        elif self.mode == 'segment':
            self._handle_segment(img_x, img_y)
            return True
        elif self.mode == 'pencil':
            self._pencil_points = []
            return True
        return False

    def _find_drag_point(self, img_x, img_y):
        min_dist = 15
        self._drag_index = None
        self._drag_curve = None

        if self.graph_mode == '1d':
            for i, (x, y) in enumerate(self.data_points_1d):
                px, py = self.calibrator.val_to_px(x, y)
                d = np.sqrt((px - img_x) ** 2 + (py - img_y) ** 2)
                if d < min_dist:
                    min_dist = d
                    self._drag_index = i
        else:
            for cn, points in self.data_points_2d.items():
                for i, (x, y) in enumerate(points):
                    px, py = self.calibrator.val_to_px(x, y)
                    d = np.sqrt((px - img_x) ** 2 + (py - img_y) ** 2)
                    if d < min_dist:
                        min_dist = d
                        self._drag_index = i
                        self._drag_curve = cn

        if self._drag_index is not None:
            self.panel.set_status(t('status.drag_point_now'))

    def _on_canvas_drag(self, cx, cy, img_x, img_y):
        if self.mode == 'dragging' and getattr(self, '_drag_index', None) is not None:
            if self.graph_mode == '1d':
                x_val, y_val = self.calibrator.px_to_val(img_x, img_y)
                self.data_points_1d[self._drag_index] = [x_val, y_val]
            else:
                x_val, y_val = self.calibrator.px_to_val(img_x, img_y)
                self.data_points_2d[self._drag_curve][self._drag_index] = [x_val, y_val]
            self._draw_existing_points()
        elif self.mode == 'deleting':
            self._handle_delete(img_x, img_y)
        elif self.mode == 'pencil':
            self._handle_pencil(img_x, img_y)

    def _on_canvas_release(self, cx, cy, img_x, img_y):
        if self.mode == 'dragging':
            self._drag_index = None
            self._drag_curve = None

    def _on_canvas_motion(self, cx, cy, img_x, img_y):
        if not self.image_loader.is_loaded():
            return

        if self.calibrator.is_calibrated():
            vx, vy = self.calibrator.px_to_val(img_x, img_y)
            self.canvas_info.configure(text=f'X = {vx:.3f}   Y = {vy:.3f}')
        else:
            self.canvas_info.configure(text=f'px: {img_x}, {img_y}')

    def _on_canvas_right_click(self, cx, cy):
        self._cancel_mode()

    def _on_zoom_change(self, scale, user_zoom):
        if user_zoom != 1.0:
            self.panel.set_info(t('status.zoom', percent=f'{user_zoom * 100:.0f}'))

    def _cancel_mode(self):
        if self.mode == 'pick_origin':
            self.mode = 'normal'
            self.canvas_widget.canvas.configure(cursor='crosshair')
            self.panel.set_status(t('status.cancelled'))
            if hasattr(self, 'toast'):
                self.toast.hide()
            # Убираем из undo, потому что картинку уже выровняли, но калибровка отменена
            if self.undo_manager.stack:
                self.undo_manager.pop()
        elif self.mode == 'calibrating':
            self.mode = 'normal'
            self.calibrator.step = 0
            self.calibrator.points = {}
            self.canvas_widget.clear_overlay()
            self.canvas_widget.canvas.configure(cursor='crosshair')
            self.panel.set_status(t('status.calib_cancelled'))
            self._draw_calibration()
        elif self.mode == 'digitizing':
            self.mode = 'normal'
            self.temp_points = []
            self.canvas_widget.canvas.configure(cursor='crosshair')
            self._draw_existing_points()
            self.panel.set_status(t('status.cancelled'))
        elif self.mode == 'pencil':
            self._finish_pencil()
            self.mode = 'normal'
            self.canvas_widget.canvas.configure(cursor='crosshair')
        elif self.mode in ('dragging', 'deleting', 'manual_point', 'segment'):
            self.mode = 'normal'
            self._segment_points = []
            self._pencil_points = []
            self.canvas_widget.canvas.configure(cursor='crosshair')
            self._draw_existing_points()
            self.panel.set_status(t('status.cancelled'))

        if hasattr(self, 'toast'):
            self.toast.hide()

    def _reset_zoom(self):
        self.canvas_widget.reset_zoom()
        self.panel.set_status(t('status.zoom_reset'))

    def _show_help(self):
        HelpDialog(self)

    # ============================================================
    # ФОРМУЛА / ПОЛИНОМ
    # ============================================================

    def _open_poly_dialog(self):
        dlg = PolyDialog(self)
        if dlg.result is None:
            return

        points = dlg.result['points']
        x2 = dlg.result.get('x2')
        x3 = dlg.result.get('x3')
        formula = dlg.result.get('formula', '')
        var_name = dlg.result.get('var_name')

        PolyResultDialog(
            self, points,
            x2=x2, x3=x3,
            formula=formula,
            var_name=var_name,
        )

        self.panel.set_status(t('poly.done_status', n=len(points)))