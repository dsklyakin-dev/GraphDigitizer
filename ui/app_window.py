"""
Главное окно приложения с оцифровкой кривых.
v8.0 — Toast-уведомления, OCR, точка начала координат, авто-выравнивание
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
import numpy as np
import cv2
import threading

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
from core.predictive_detector import PredictiveDetector


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
        self.supermode = False
        self.backup_before_super = None

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
        self.toast = Toast(self)

        self.dashed_mask = None
        self._dashed_points = []

        # Подписка на смену языка
        i18n.on_change(self._on_language_changed)
        theme_manager.on_change(self._on_theme_changed)

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

        self.mode_btn_super = ctk.CTkButton(
            mode_switch_frame,
            text="Супермод",  # или t('mode.super')
            width=140,
            height=38,
            corner_radius=8,
            fg_color='transparent',
            hover_color=COLORS['border'],
            text_color=COLORS['text_secondary'],
            font=FONTS['small_bold'],
            command=lambda: self._set_mode('super'),
        )
        self.mode_btn_super.pack(side='left', padx=3, pady=3)

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
        self.canvas_widget.canvas.bind('<Control-z>', lambda e: self._undo())
        self.canvas_widget.canvas.bind('<Control-Z>', lambda e: self._undo())


    def _bind_hotkeys(self):
        self.bind_all('<F12>', lambda e: self._show_help())
        self.bind_all('<Control-o>', lambda e: self._open_image())
        self.bind_all('<Control-s>', lambda e: self._save_data())
        self.bind_all('<Control-0>', lambda e: self._reset_zoom())
        self.bind_all('<Escape>', lambda e: self._cancel_mode())
        self.bind_all('<KeyPress>', self._on_key_press)
        self.bind_all('<KeyRelease>', self._on_key_release)

    def _on_theme_changed(self, theme_name):
        import customtkinter as ctk
        ctk.set_appearance_mode(theme_name)
        try:
            icon = '☀️' if theme_name == 'dark' else '🌙'
            self.panel.theme_btn.configure(text=icon)
        except Exception:
            pass

        from tkinter import messagebox
        from core.i18n import t
        answer = messagebox.askyesno(
            t('msg.confirm'),
            t('theme.restart_question'),
        )
        if answer:
            self._restart_app()

    def _restart_app(self):
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

    def _on_language_changed(self, lang):
        try:
            self.title(f'{t("app.title")} v{APP_VERSION}')
            self.legend_title.configure(text=t('panel.legend'))
            self.canvas_title.configure(text=t('panel.canvas'))
            self.mode_btn_1d.configure(text=t('mode.1d'))
            self.mode_btn_2d.configure(text=t('mode.2d'))
            self.mode_btn_poly.configure(text=t('mode.poly'))
            self.mode_btn_super.configure(text=t('mode.super'))
            if not self.image_loader.is_loaded():
                self.canvas_info.configure(text=t('panel.no_image'))
            self._update_legend()
        except Exception as e:
            print(f'[lang change error] {e}')

    def _open_help(self):
        HelpDialog(self)

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
            'smooth_data': self._open_smoothing_dialog,
            'mark_dashed': self._start_mark_dashed,
        }

        if action in handlers:
            handlers[action]()

    def _start_mark_dashed(self):
        self.mode = 'mark_dashed'
        self.canvas_widget.canvas.configure(cursor='pencil')
        self.panel.set_status("Зажмите мышь и обведите пунктир (он будет проигнорирован).")

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
            self.super_found_curves = None

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
            'super': (self.mode_btn_super, COLORS['warning']),  # <--- ДОБАВИТЬ
        }

        for key, (btn, color) in modes.items():
            if key == mode:
                btn.configure(fg_color=color, text_color=COLORS['text_on_primary'])
            else:
                btn.configure(fg_color='transparent', text_color=COLORS['text_secondary'])

        mode_text = {
            '1d': t('mode.1d_short'),
            '2d': t('mode.2d_short'),
            'poly': t('mode.poly_short'),
            'super': t('mode.super_short'),
        }.get(mode, mode)

        self.panel.set_status(t('status.mode', mode=mode_text))
        self._redraw_points()
        self._update_legend()

        # Если переключились на Супермод — сбрасываем старые данные
        if mode == 'super':
            self.supermode = True
            self.data_points_1d = []
            self.data_points_2d = {}
            self.super_found_curves = None  # <--- СБРОС
            self.super_curve_names = {}
            self._draw_existing_points()
            self._update_legend()
            self.panel.set_status(t('super.click_graph'))
        else:
            self.supermode = False

    def _toggle_multi_curve(self):
        self.multi_curve_mode = self.panel.multi_curve_var.get()
        if self.multi_curve_mode:
            self.panel.set_status(t('status.multi_curve_on'))
        else:
            self.panel.set_status(t('status.multi_curve_off'))

    def _update_legend(self):
        for widget in self.legend_scroll.winfo_children():
            widget.destroy()

        # Показываем легенду для 2D и Супермода
        if self.graph_mode not in ('2d', 'super') or not self.data_points_2d:
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
            item.bind('<Button-1>', lambda e, cn=curve_name: self._highlight_curve(cn))

            dot = ctk.CTkFrame(
                item, width=16, height=16,
                fg_color=color,
                corner_radius=8
            )
            dot.pack(side='left', padx=(10, 8), pady=10)
            dot.pack_propagate(False)
            dot.bind('<Button-1>', lambda e, cn=curve_name: self._highlight_curve(cn))

            text_frame = ctk.CTkFrame(item, fg_color='transparent')
            text_frame.pack(side='left', fill='x', expand=True, pady=6)
            text_frame.bind('<Button-1>', lambda e, cn=curve_name: self._highlight_curve(cn))

            label1 = ctk.CTkLabel(
                text_frame, text=f'X2 = {curve_name}',
                font=FONTS['small_bold'],
                text_color=COLORS['text_primary'],
                anchor='w'
            )
            label1.pack(anchor='w')
            label1.bind('<Button-1>', lambda e, cn=curve_name: self._highlight_curve(cn))

            label2 = ctk.CTkLabel(
                text_frame, text=f'{count}',
                font=FONTS['tiny'],
                text_color=COLORS['text_secondary'],
                anchor='w'
            )
            label2.pack(anchor='w')
            label2.bind('<Button-1>', lambda e, cn=curve_name: self._highlight_curve(cn))

    def _highlight_curve(self, curve_name):
        if self.graph_mode not in ('2d', 'super') or curve_name not in self.data_points_2d:
            return

        self.current_curve = curve_name
        self.canvas_widget.clear_overlay()

        for cid, points in self.data_points_2d.items():
            color = CURVE_COLORS[list(self.data_points_2d.keys()).index(cid) % len(CURVE_COLORS)]
            if cid == curve_name:
                size = 5
                outline = 'yellow'
            else:
                size = 2
                outline = 'white'

            for x, y in points:
                px, py = self.calibrator.val_to_px(x, y)
                self.canvas_widget.draw_point(px, py, color=color, size=size, outline=outline)

        self._draw_calibration()
        self.panel.set_status(f"Выбрана кривая X2 = {curve_name}")

    def _auto_calibrate(self):
        if not self.image_loader.is_loaded():
            messagebox.showwarning(t('msg.warning'), t('msg.load_image_first'))
            return

        self.panel.set_status(t('status.aligning'))
        if hasattr(self, 'toast'):
            self.toast.show(t('status.aligning'), duration=2, color='info')
        self.update()

        old_image = self.image_loader.current.copy()
        self.undo_manager.push({'type': 'align', 'data': old_image})

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

        self.panel.set_status("Поиск начала координат...")
        self.update()

        detector = AxisDetector(self.image_loader.current)
        origin = detector.find_origin()

        if origin is not None:
            print(f'[AxisDetector] Автопоиск начала координат: {origin}')
            if hasattr(self, 'toast'):
                self.toast.show("Начало координат найдено автоматически", duration=3, color='success')
            self._handle_pick_origin(origin[0], origin[1])
        else:
            self.mode = 'pick_origin'
            self.canvas_widget.canvas.configure(cursor='tcross')
            self.panel.set_status(t('status.pick_origin'))
            self.panel.set_info(t('status.pick_origin_hint'))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.pick_origin'), duration=8, color='warning')

    def _handle_pick_origin(self, img_x, img_y):
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

        dialog = CalibrationDialog(self, defaults=defaults, title=t('btn.auto_calib'))
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
        self.canvas_widget.draw_point(origin[0], origin[1], color='#F59E0B', size=8, shape='cross')
        self.canvas_widget.draw_point(x_end[0], x_end[1], color='#3B82F6', size=8, shape='cross')
        self.canvas_widget.draw_point(y_end[0], y_end[1], color='#10B981', size=8, shape='cross')
        self.canvas_widget.draw_line(origin[0], origin[1], x_end[0], x_end[1], color='#3B82F6', width=2)
        self.canvas_widget.draw_line(origin[0], origin[1], y_end[0], y_end[1], color='#10B981', width=2)

    def _start_manual_calib(self):
        if not self.image_loader.is_loaded():
            messagebox.showwarning(t('msg.warning'), t('msg.load_image_first'))
            return

        dialog = CalibrationDialog(self, defaults=self.calibrator.field_values, title=t('btn.manual_calib'))
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
                'value': (float(self.calibrator.field_values['X0']), float(self.calibrator.field_values['Y0'])),
            }
            self.canvas_widget.draw_point(img_x, img_y, color='#F59E0B', size=10, shape='cross')
            self.panel.set_status(t('status.click_x_end'))
            self.panel.set_info(t('status.step_2_3'))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.click_x_end'), duration=6, color='warning')

        elif step == 1:
            self.calibrator.points['x_max'] = {
                'pixel': (img_x, img_y),
                'value': (float(self.calibrator.field_values['X1']), float(self.calibrator.field_values['Y0'])),
            }
            self.canvas_widget.draw_point(img_x, img_y, color='#3B82F6', size=10, shape='cross')
            o = self.calibrator.points['origin']['pixel']
            self.canvas_widget.draw_line(o[0], o[1], img_x, img_y, color='#3B82F6', width=2)
            self.panel.set_status(t('status.click_y_end'))
            self.panel.set_info(t('status.step_3_3'))
            if hasattr(self, 'toast'):
                self.toast.show(t('toast.click_y_end'), duration=6, color='warning')

        elif step == 2:
            self.calibrator.points['y_max'] = {
                'pixel': (img_x, img_y),
                'value': (float(self.calibrator.field_values['X0']), float(self.calibrator.field_values['Y1'])),
            }
            self.canvas_widget.draw_point(img_x, img_y, color='#10B981', size=10, shape='cross')
            o = self.calibrator.points['origin']['pixel']
            self.canvas_widget.draw_line(o[0], o[1], img_x, img_y, color='#10B981', width=2)

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
        calib_file = Path(self.image_loader.path).with_name(Path(self.image_loader.path).stem + '_calib.json')
        self.calibrator.save(str(calib_file))

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
        if not self.calibrator.is_calibrated():
            self.panel.set_status(t('msg.calib_first'))
            return

        detector = CurveDetector(self.image_loader.current, self.calibrator)
        step = int(self.panel.step_entry.get() or 8)
        radius = int(self.panel.radius_entry.get() or 10)

        path = detector.water_flow(img_x, img_y, step_pixels=step, search_window=radius)
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

        self.undo_manager.push({'type': '1d_points', 'data': list(self.data_points_1d)})
        self.data_points_1d = values
        self._draw_existing_points()

        self.mode = 'normal'
        self.canvas_widget.canvas.configure(cursor='crosshair')
        self.panel.set_status(t('status.digitized', n=len(values)))
        self.panel.set_info(t('status.undo_hint'))

        if hasattr(self, 'toast'):
            self.toast.show(t('toast.digitize_done', n=len(values)), duration=3, color='success')

    def _digitize_2d_click(self, img_x, img_y):
        self.temp_points.append((img_x, img_y))
        idx = len(self.temp_points)

        color = '#10B981' if idx == 1 else '#F59E0B'
        self.canvas_widget.draw_point(img_x, img_y, color=color, size=8, shape='cross')

        if idx >= 2:
            p1 = self.temp_points[-2]
            p2 = self.temp_points[-1]
            self.canvas_widget.draw_line(p1[0], p1[1], p2[0], p2[1], color='#3B82F6', width=2, dash=(4, 4))

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
                    self.panel.set_status(t('status.curve_points_copied', name=x2_value, n=len(new_vals)))
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
            self.toast.show(t('toast.digitize_done', n=len(values)), duration=3, color='success')

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
                    self.canvas_widget.draw_point(px, py, color='#EF4444', size=3, outline='white')
        else:
            # Рисуем все кривые из data_points_2d (для 2d и super)
            for idx, (curve_name, points) in enumerate(self.data_points_2d.items()):
                color = CURVE_COLORS[idx % len(CURVE_COLORS)]
                for x, y in points:
                    px, py = self.calibrator.val_to_px(x, y)
                    self.canvas_widget.draw_point(px, py, color=color, size=3, outline='white')

        self._draw_calibration()

    def _redraw_points(self):
        self._draw_existing_points()

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
            self.undo_manager.push({'type': 'segment', 'data': old_copy})

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
            self.canvas_widget.draw_point(img_x, img_y, color='#8B5CF6', size=6, shape='circle')
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
            self.undo_manager.push({'type': 'segment', 'data': old_image})

            pil = cv2_to_pil(self.image_loader.current)
            self.canvas_widget.set_image(pil)
            self._draw_existing_points()

            self._segment_points = []
            self.panel.set_status(t('status.segment_done'))

    def _open_smoothing_dialog(self):
        if self.graph_mode == '1d':
            if len(self.data_points_1d) < 5:
                messagebox.showwarning(t('msg.warning'), "Слишком мало точек для сглаживания (нужно минимум 5).")
                return
            data = self.data_points_1d
        else:
            if not any(len(p) >= 5 for p in self.data_points_2d.values()):
                messagebox.showwarning(t('msg.warning'), "Слишком мало точек для сглаживания (нужно минимум 5 в кривой).")
                return

            if self.graph_mode == 'super':
                all_curves = list(self.data_points_2d.values())
                from ui.smoothing_dialog import SmoothingDialog
                SmoothingDialog(self, all_curves, self._apply_smoothed_all)
                return

            if self.current_curve is None or self.current_curve not in self.data_points_2d:
                messagebox.showwarning(t('msg.warning'), "Выберите кривую в легенде или кликните по ней.")
                return
            data = self.data_points_2d[self.current_curve]

        from ui.smoothing_dialog import SmoothingDialog
        SmoothingDialog(self, data, self._apply_smoothed_data)

    def _apply_smoothed_all(self, smoothed_curves):
        keys = list(self.data_points_2d.keys())
        for i, key in enumerate(keys):
            if i < len(smoothed_curves):
                self.data_points_2d[key] = smoothed_curves[i]

        self._draw_existing_points()
        self._update_legend()
        self.panel.set_status("Сглаживание применено ко всем кривым.")
        if hasattr(self, 'toast'):
            self.toast.show("Все кривые сглажены", duration=3, color='success')

    def _apply_smoothed_data(self, smoothed_points):
        if self.graph_mode == '1d':
            self.undo_manager.push({'type': '1d_points', 'data': list(self.data_points_1d)})
            self.data_points_1d = smoothed_points
        else:
            curve = self.current_curve
            old = list(self.data_points_2d.get(curve, []))
            self.undo_manager.push({
                'type': '2d_points',
                'data': {'curve': curve, 'old_points': old},
            })
            self.data_points_2d[curve] = smoothed_points

        self._draw_existing_points()
        self._update_legend()
        self.panel.set_status(f"Сглаживание применено. Точек: {len(smoothed_points)}")
        if hasattr(self, 'toast'):
            self.toast.show("Сглаживание применено", duration=3, color='success')

    def _undo(self):
        if getattr(self, 'supermode', False) and hasattr(self, 'backup_before_super'):
            if self.backup_before_super:
                self.data_points_1d = list(self.backup_before_super['1d'])
                self.data_points_2d = {k: list(v) for k, v in self.backup_before_super['2d'].items()}
                self._draw_existing_points()
                self._update_legend()
                self.panel.set_status("Супермод: изменения отменены.")
                if hasattr(self, 'toast'):
                    self.toast.show("Отменено", duration=2, color='success')
                return

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
        elif t_type == 'super_assign':
            self.data_points_2d = action['data']
            self.super_curve_names = {}
            self._draw_existing_points()
            self._update_legend()
            self.panel.set_status("Назначение X2 отменено")
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
        # Если мы в Супермоде — определяем, что показывать
        if self.graph_mode == 'super':
            if self.super_found_curves:
                if len(self.super_found_curves) == 1:
                    # Одна кривая — показываем как 1D
                    data = list(self.super_found_curves.values())[0]
                    graph_mode_for_dialog = '1d'
                else:
                    # Несколько кривых — как 2D
                    data = {}
                    for cid, pts in self.super_found_curves.items():
                        name = self.super_curve_names.get(cid, str(cid))
                        data[name] = pts
                    graph_mode_for_dialog = '2d'
            else:
                messagebox.showinfo(t('msg.warning'), t('super.need_find'))
                return
        else:
            if self.graph_mode == '1d':
                if not self.data_points_1d:
                    messagebox.showinfo(t('msg.warning'), t('msg.no_data'))
                    return
                data = self.data_points_1d
                graph_mode_for_dialog = '1d'
            else:
                if not any(self.data_points_2d.values()):
                    messagebox.showinfo(t('msg.warning'), t('msg.no_data'))
                    return
                data = self.data_points_2d
                graph_mode_for_dialog = '2d'

        x3_value = None
        if graph_mode_for_dialog == '2d':
            need_x3 = messagebox.askyesno(t('msg.x3_title'), t('msg.x3_question'))
            if need_x3:
                x3_value = simpledialog.askstring(t('msg.x3_title'), t('msg.x3_prompt'))

        dlg = DataViewerDialog(self, data, graph_mode_for_dialog, x3_value)

        if dlg.updated_data is not None:
            if graph_mode_for_dialog == '1d':
                self.data_points_1d = dlg.updated_data
            else:
                self.data_points_2d = dlg.updated_data
            self._draw_existing_points()
            self._update_legend()
            self.panel.set_status(t('dv.data_updated'))

    def _save_data(self):
        if self.graph_mode == '1d':
            if not self.data_points_1d:
                messagebox.showinfo(t('msg.warning'), t('msg.no_data'))
                return
        else:
            if not any(self.data_points_2d.values()):
                messagebox.showinfo(t('msg.warning'), t('msg.no_data'))
                return

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

    def _on_canvas_click(self, cx, cy, img_x, img_y):
        if hasattr(self, 'toast'):
            self.toast.hide()

        if self.mode == 'mark_dashed':
            self._dashed_points = [(img_x, img_y)]
            return True

        if getattr(self, 'supermode', False) and self.mode == 'normal':
            if not self.calibrator.is_calibrated():
                messagebox.showwarning("Ошибка", "Сначала откалибруйте график!")
                return True

            if not getattr(self, 'super_found_curves', None):
                self.panel.set_status(t('super.scanning'))
                self.update()

                detector = PredictiveDetector(self.image_loader.current, self.calibrator)
                all_curves = detector.find_all_curves(
                    step_pixels=int(self.panel.step_entry.get() or 5),
                    ignore_mask=getattr(self, 'dashed_mask', None)
                )

                if all_curves:
                    filtered_curves = {}
                    idx = 1
                    for cid, pts in all_curves.items():
                        if len(pts) < 30:
                            continue

                        min_x = min(p[0] for p in pts)
                        max_x = max(p[0] for p in pts)
                        x_range = self.calibrator.points['x_max']['value'][0] - self.calibrator.points['origin']['value'][0]
                        if (max_x - min_x) < x_range * 0.15:
                            continue

                        filtered_curves[idx] = pts
                        idx += 1

                    self.super_found_curves = filtered_curves
                    self.super_curve_names = {}
                    self._update_super_curves_visual()
                    self.panel.set_status(t('super.found_curves', n=len(filtered_curves)))
                else:
                    self.panel.set_status(t('super.not_found'))
                return True

            clicked_curve_id = None
            min_dist = 20

            for cid, points in self.super_found_curves.items():
                for vx, vy in points:
                    px, py = self.calibrator.val_to_px(vx, vy)
                    dist = np.sqrt((px - img_x) ** 2 + (py - img_y) ** 2)
                    if dist < min_dist:
                        min_dist = dist
                        clicked_curve_id = cid

            if clicked_curve_id is not None:
                # ЕСЛИ НАЙДЕНА ВСЕГО 1 КРИВАЯ — НЕ СПРАШИВАЕМ X2
                if len(self.super_found_curves) == 1:
                    self.data_points_1d = self.super_found_curves[clicked_curve_id]
                    self.graph_mode = '1d'  # Временно переключаемся для отображения
                    self._draw_existing_points()
                    self.panel.set_status(t('super.one_curve'))
                else:
                    # Если 2+ кривых — спрашиваем X2
                    dlg = X2Dialog(self)
                    if dlg.result is not None:
                        new_x2 = dlg.result
                        old_data = {k: list(v) for k, v in self.data_points_2d.items()}
                        self.undo_manager.push({
                            'type': 'super_assign',
                            'data': old_data
                        })
                        self.super_curve_names[clicked_curve_id] = new_x2
                        self.current_curve = new_x2
                        self._update_super_curves_visual()
                        self.panel.set_status(t('super.x2_assigned', x2=new_x2))
            else:
                self.panel.set_status(t('super.click_closer'))

            return True

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

    def _update_super_curves_visual(self):
        self.data_points_2d = {}
        for cid, pts in self.super_found_curves.items():
            name = self.super_curve_names.get(cid, str(cid))  # <--- УБРАЛИ проверку
            self.data_points_2d[name] = pts

        self._draw_existing_points()
        self._update_legend()

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
        if self.mode == 'mark_dashed':
            self._dashed_points.append((img_x, img_y))
            if len(self._dashed_points) >= 2:
                p1 = self._dashed_points[-2]
                p2 = self._dashed_points[-1]
                self.canvas_widget.draw_line(p1[0], p1[1], p2[0], p2[1], color='#FF0000', width=4)
            return True
        elif self.mode == 'deleting':
            self._handle_delete(img_x, img_y)
        elif self.mode == 'pencil':
            self._handle_pencil(img_x, img_y)

    def _on_canvas_release(self, cx, cy, img_x, img_y):
        if self.mode == 'dragging':
            self._drag_index = None
            self._drag_curve = None
        if self.mode == 'mark_dashed':
            if len(self._dashed_points) > 1:
                self.dashed_mask = np.zeros(self.image_loader.current.shape[:2], dtype=np.uint8)
                pts = np.array(self._dashed_points, dtype=np.int32)
                cv2.polylines(self.dashed_mask, [pts], False, 255, thickness=12)
                self.panel.set_status("Пунктир обведен. Кликните по графику для поиска.")
            self.mode = 'normal'
            self.canvas_widget.canvas.configure(cursor='crosshair')
            return True

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

    def _open_poly_dialog(self):
        dlg = PolyDialog(self)
        if dlg.result is None:
            return

        points = dlg.result['points']
        x2 = dlg.result.get('x2')
        x3 = dlg.result.get('x3')
        formula = dlg.result.get('formula', '')
        var_name = dlg.result.get('var_name')

        PolyResultDialog(self, points, x2=x2, x3=x3, formula=formula, var_name=var_name)
        self.panel.set_status(t('poly.done_status', n=len(points)))