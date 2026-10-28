"""
Точка входа приложения Graph Digitizer v7.3
"""

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk
from config import settings
import threading


def _preload_scipy():
    """Тихо загружает SciPy в фоне, чтобы не было зависаний."""
    try:
        from scipy.signal import savgol_filter
        print("[Preload] SciPy успешно загружен в фоне.")
    except ImportError:
        print("[Preload] SciPy не установлен, сглаживание будет использовать Moving Average.")


# ...

def main():
    # ============================================================
    # ИНИЦИАЛИЗАЦИЯ ТЕМЫ — ДО создания окна
    # ============================================================
    saved_theme = settings.load_saved_theme()
    print(f'[MAIN] загружена тема: {saved_theme}')

    settings.set_theme(saved_theme)
    ctk.set_appearance_mode(saved_theme)

    # Запускаем предзагрузку SciPy в фоновом потоке
    threading.Thread(target=_preload_scipy, daemon=True).start()

    # ============================================================
    # СОЗДАНИЕ ОКНА
    # ============================================================
    from ui.app_window import AppWindow

    app = AppWindow()
    app.mainloop()


if __name__ == '__main__':
    main()