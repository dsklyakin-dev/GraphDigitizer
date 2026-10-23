"""
Менеджер темы с поддержкой подписки.
Позволяет уведомлять виджеты о смене темы.
v1.0
"""

from config import settings


class ThemeManager:
    def __init__(self):
        self._listeners = []

    @property
    def current(self):
        return settings.get_theme()

    def is_dark(self):
        return self.current == 'dark'

    def toggle(self):
        """Переключает тему и уведомляет слушателей."""
        new_theme = 'light' if self.is_dark() else 'dark'
        self.set(new_theme)

    def set(self, theme_name):
        """Устанавливает тему и уведомляет слушателей."""
        if theme_name not in ('light', 'dark'):
            return
        if theme_name == self.current:
            return

        settings.set_theme(theme_name)

        # Уведомляем всех
        for cb in self._listeners:
            try:
                cb(theme_name)
            except Exception as e:
                print(f'[theme listener error] {e}')

    def on_change(self, callback):
        """Регистрирует колбэк, вызываемый при смене темы."""
        self._listeners.append(callback)


# Глобальный экземпляр
theme_manager = ThemeManager()