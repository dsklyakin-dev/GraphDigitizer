"""
Точка входа приложения Graph Digitizer v7.3
"""

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk
from config import settings


def main():
    # ============================================================
    # ИНИЦИАЛИЗАЦИЯ ТЕМЫ — ДО создания окна
    # ============================================================
    saved_theme = settings.load_saved_theme()
    print(f'[MAIN] загружена тема: {saved_theme}')

    settings.set_theme(saved_theme)
    ctk.set_appearance_mode(saved_theme)

    # ============================================================
    # СОЗДАНИЕ ОКНА
    # ============================================================
    from ui.app_window import AppWindow

    app = AppWindow()
    app.mainloop()


if __name__ == '__main__':
    main()