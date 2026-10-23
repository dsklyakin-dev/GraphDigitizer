"""
Окно с инструкцией по программе.
"""

import tkinter as tk
import customtkinter as ctk
from config.settings import COLORS, FONTS
from core.i18n import t, i18n
from utils.text_bindings import bind_text_clipboard


class HelpDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title(t('app.help_title'))
        self.geometry('780x720')
        self.configure(fg_color=COLORS['bg_main'])
        self.transient(parent)

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 780) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 720) // 2
        self.geometry(f'+{x}+{y}')

        self._build_ui()

        self.after(50, self._focus_window)
        self.grab_set()

    def _focus_window(self):
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _build_ui(self):
        self.header = ctk.CTkLabel(
            self, text=t('help.title'),
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        )
        self.header.pack(pady=(18, 10))

        frame = ctk.CTkFrame(self, fg_color=COLORS['bg_panel'], corner_radius=8)
        frame.pack(fill='both', expand=True, padx=16, pady=(0, 10))

        self.text_widget = tk.Text(
            frame,
            wrap='word',
            font=('Consolas', 10),
            bg=COLORS['bg_panel'],
            fg=COLORS['text_primary'],
            relief='flat',
            borderwidth=0,
            padx=14,
            pady=14,
        )
        bind_text_clipboard(self.text_widget)
        self.text_widget.pack(side='left', fill='both', expand=True)

        scroll = ctk.CTkScrollbar(frame, command=self.text_widget.yview)
        scroll.pack(side='right', fill='y', padx=(0, 4), pady=4)
        self.text_widget.configure(yscrollcommand=scroll.set)

        self._fill_content()

        self.close_btn = ctk.CTkButton(
            self, text=t('btn.close'), height=42, corner_radius=8,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_hover'],
            font=FONTS['button'],
            command=self._close
        )
        self.close_btn.pack(pady=(0, 16), padx=16, fill='x')

        self.bind('<Escape>', lambda e: self._close())

    def _fill_content(self):
        self.text_widget.config(state='normal')
        self.text_widget.delete('1.0', 'end')
        self.text_widget.insert('1.0', t('help.content'))
        self.text_widget.config(state='disabled')

    def _close(self):
        self.grab_release()
        self.destroy()