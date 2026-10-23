"""
Универсальные привязки клавиш для tk.Text,
работающие в русской и английской раскладках.

Используется event.keycode (физический код клавиши),
который одинаков для обеих раскладок.
"""


# Физические keycode клавиш на Windows
KEYCODES = {
    'v': 86,
    'c': 67,
    'x': 88,
    'a': 65,
    'z': 90,
    'y': 89,
}


def bind_text_clipboard(text_widget):
    """
    Привязывает Ctrl+C / Ctrl+V / Ctrl+X / Ctrl+A / Ctrl+Z / Ctrl+Y
    к текстовому виджету tk.Text, поддерживая русскую раскладку.
    """

    def _make_handler(action):
        def handler(event):
            # Проверяем, что нажат именно Ctrl (state & 0x4)
            if not (event.state & 0x4):
                return None
            try:
                action()
            except Exception as e:
                print(f'[text binding error] {e}')
            return 'break'
        return handler

    def _paste():
        text_widget.event_generate('<<Paste>>')

    def _copy():
        text_widget.event_generate('<<Copy>>')

    def _cut():
        text_widget.event_generate('<<Cut>>')

    def _select_all():
        text_widget.tag_add('sel', '1.0', 'end-1c')
        text_widget.mark_set('insert', '1.0')
        text_widget.see('insert')

    def _undo():
        try:
            text_widget.edit_undo()
        except Exception:
            pass

    def _redo():
        try:
            text_widget.edit_redo()
        except Exception:
            pass

    # Словарь: keycode → действие
    handlers = {
        KEYCODES['v']: _make_handler(_paste),
        KEYCODES['c']: _make_handler(_copy),
        KEYCODES['x']: _make_handler(_cut),
        KEYCODES['a']: _make_handler(_select_all),
        KEYCODES['z']: _make_handler(_undo),
        KEYCODES['y']: _make_handler(_redo),
    }

    def _on_key(event):
        # Проверяем Ctrl
        if not (event.state & 0x4):
            return None
        handler = handlers.get(event.keycode)
        if handler:
            return handler(event)
        return None

    # Одна универсальная привязка на все клавиши
    text_widget.bind('<KeyPress>', _on_key, add='+')