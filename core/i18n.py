"""
Менеджер локализации. Хранит текущий язык и предоставляет строки.
"""

from locales import ru, en

_LANGUAGES = {
    'ru': ru.STRINGS,
    'en': en.STRINGS,
}


class I18n:
    def __init__(self, default='ru'):
        self._lang = default
        self._listeners = []

    @property
    def lang(self):
        return self._lang

    def set_lang(self, lang):
        if lang not in _LANGUAGES:
            return
        if lang == self._lang:
            return
        self._lang = lang
        for cb in self._listeners:
            try:
                cb(lang)
            except Exception as e:
                print(f'[i18n listener error] {e}')

    def on_change(self, callback):
        """Регистрирует callback, вызываемый при смене языка."""
        self._listeners.append(callback)

    def t(self, key, **kwargs):
        """Возвращает строку по ключу. Поддерживает {placeholder}.format."""
        s = _LANGUAGES[self._lang].get(key)
        if s is None:
            # fallback на русский
            s = _LANGUAGES['ru'].get(key, key)
        if kwargs:
            try:
                return s.format(**kwargs)
            except Exception:
                return s
        return s


# Глобальный экземпляр
i18n = I18n('ru')


def t(key, **kwargs):
    return i18n.t(key, **kwargs)