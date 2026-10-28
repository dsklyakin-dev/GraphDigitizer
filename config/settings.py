"""
Настройки приложения: цвета, шрифты, размеры, константы.
v2.0 — поддержка светлой и тёмной темы
"""
import os
import json
# ============================================================
# ЦВЕТА — СВЕТЛАЯ ТЕМА
# ============================================================
COLORS_LIGHT = {
    'bg_main': '#F5F7FA',
    'bg_panel': '#FFFFFF',
    'bg_canvas': '#EEF1F6',
    'bg_hover': '#E8EEF7',

    'primary': '#3B82F6',
    'primary_hover': '#2563EB',
    'primary_light': '#DBEAFE',

    'success': '#10B981',
    'success_hover': '#059669',

    'warning': '#F59E0B',
    'warning_hover': '#D97706',

    'danger': '#EF4444',
    'danger_hover': '#DC2626',

    'accent': '#8B5CF6',
    'accent_hover': '#7C3AED',

    'text_primary': '#1F2937',
    'text_secondary': '#4B5563',
    'text_muted': '#6B7280',
    'text_on_primary': '#FFFFFF',

    'border': '#E5E7EB',
    'border_focus': '#3B82F6',
    'divider': '#F3F4F6',

    'point_red': '#EF4444',
    'start_green': '#10B981',
    'end_orange': '#F59E0B',
    'grid_line': '#CBD5E1',
}

# ============================================================
# ЦВЕТА — ТЁМНАЯ ТЕМА
# ============================================================
COLORS_DARK = {
    'bg_main': '#1a1a1a',
    'bg_panel': '#252525',
    'bg_canvas': '#1f1f1f',
    'bg_hover': '#333333',

    'primary': '#3B82F6',
    'primary_hover': '#2563EB',
    'primary_light': '#1e3a8a',

    'success': '#10B981',
    'success_hover': '#059669',

    'warning': '#F59E0B',
    'warning_hover': '#D97706',

    'danger': '#EF4444',
    'danger_hover': '#DC2626',

    'accent': '#8B5CF6',
    'accent_hover': '#7C3AED',

    'text_primary': '#E5E7EB',
    'text_secondary': '#9CA3AF',
    'text_muted': '#6B7280',
    'text_on_primary': '#FFFFFF',

    'border': '#3a3a3a',
    'border_focus': '#3B82F6',
    'divider': '#2a2a2a',

    'point_red': '#EF4444',
    'start_green': '#10B981',
    'end_orange': '#F59E0B',
    'grid_line': '#4a4a4a',
}

# ============================================================
# АКТИВНАЯ ПАЛИТРА
# ============================================================
COLORS = COLORS_LIGHT.copy()

_current_theme = 'light'


def get_theme():
    return _current_theme


def set_theme(theme_name):
    """Переключает палитру И сохраняет выбор в файл."""
    global _current_theme

    if theme_name not in ('light', 'dark'):
        return

    _current_theme = theme_name

    COLORS.clear()
    if theme_name == 'dark':
        COLORS.update(COLORS_DARK)
    else:
        COLORS.update(COLORS_LIGHT)

    # Сохраняем в файл
    save_theme(theme_name)


# ============================================================
# ШРИФТЫ
# ============================================================
FONTS = {
    'title': ('Segoe UI', 20, 'bold'),
    'subtitle': ('Segoe UI', 14, 'bold'),
    'section': ('Segoe UI', 11, 'bold'),
    'normal': ('Segoe UI', 12),
    'normal_bold': ('Segoe UI', 12, 'bold'),
    'button': ('Segoe UI', 12, 'bold'),
    'small': ('Segoe UI', 11),
    'small_bold': ('Segoe UI', 11, 'bold'),
    'tiny': ('Segoe UI', 10),
    'mono': ('Consolas', 11),
}

# ============================================================
# РАЗМЕРЫ ОКНА
# ============================================================
WINDOW = {
    'width': 1500,
    'height': 900,
    'min_width': 1200,
    'min_height': 700,
    'panel_width': 360,
    'corner_radius': 10,
    'button_height': 44,
}

# ============================================================
# НАСТРОЙКИ ОЦИФРОВКИ
# ============================================================
DIGITIZER_DEFAULTS = {
    'step_pixels': 8,
    'brush_radius': 14,
    'delete_radius': 8,
    'pencil_radius': 3,
    'snap_distance': 15,
}

# ============================================================
# ЦВЕТА КРИВЫХ (для 2D режима)
# ============================================================
CURVE_COLORS = [
    '#EF4444', '#10B981', '#3B82F6', '#F59E0B', '#8B5CF6',
    '#06B6D4', '#EC4899', '#84CC16', '#F97316', '#6366F1',
]

# ============================================================
# МЕТАДАННЫЕ
# ============================================================
APP_NAME = 'Graph Digitizer'
APP_VERSION = '8.0'

# Путь к файлу настроек (рядом с программой)
_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'theme.json'
)

# ============================================================
# ФЛАГИ ФУНКЦИЙ (Feature Flags)
# Если False — фича отключена, программа работает как раньше.
# ============================================================
ENABLE_OUTLIER_DETECTION = False


def load_saved_theme():
    """Загружает сохранённую тему из файла. По умолчанию — 'light'."""
    try:
        if os.path.exists(_SETTINGS_FILE):
            with open(_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                theme = data.get('theme', 'light')
                if theme in ('light', 'dark'):
                    return theme
    except Exception as e:
        print(f'[settings] ошибка загрузки темы: {e}')
    return 'light'


def save_theme(theme_name):
    """Сохраняет тему в файл."""
    try:
        with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'theme': theme_name}, f)
    except Exception as e:
        print(f'[settings] ошибка сохранения темы: {e}')

