"""
Утилита для копирования табличных данных в буфер обмена Windows
так, чтобы Excel разбивал их по столбцам.

Использует win32clipboard (pywin32) — нативный Windows API.
Кладёт в буфер:
  - text/html (Excel парсит как таблицу)
  - text/plain (на случай вставки в блокнот)
"""

import html as html_module


def copy_table_to_clipboard(widget, headers, rows):
    """
    Копирует таблицу в буфер обмена Windows с HTML-форматом.

    Если headers пустой ([] или None) — строка заголовков НЕ добавляется.
    """
    try:
        import win32clipboard
        import win32con
    except ImportError:
        _fallback_clipboard(widget, headers, rows)
        return

    has_headers = bool(headers)

    # --- HTML ---
    html_parts = [
        '<html><head><meta charset="utf-8"></head><body>',
        '<table border="1" cellspacing="0" cellpadding="2">'
    ]

    if has_headers:
        html_parts.append('<tr>')
        for h in headers:
            html_parts.append(f'<th>{html_module.escape(str(h))}</th>')
        html_parts.append('</tr>')

    for row in rows:
        html_parts.append('<tr>')
        for cell in row:
            html_parts.append(f'<td>{html_module.escape(str(cell))}</td>')
        html_parts.append('</tr>')

    html_parts.append('</table></body></html>')
    html_data = ''.join(html_parts)

    # --- Plain text (TSV) ---
    if has_headers:
        all_rows = [headers] + rows
    else:
        all_rows = rows
    text_data = '\r\n'.join('\t'.join(str(c) for c in row) for row in all_rows)

    # --- В буфер ---
    CF_HTML = win32clipboard.RegisterClipboardFormat('HTML Format')
    html_payload = _make_html_payload(html_data)

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text_data)
        win32clipboard.SetClipboardData(CF_HTML, html_payload.encode('utf-8'))
    finally:
        win32clipboard.CloseClipboard()


def _fallback_clipboard(widget, headers, rows):
    """Если pywin32 не установлен — обычное копирование текста."""
    has_headers = bool(headers)
    if has_headers:
        all_rows = [headers] + rows
    else:
        all_rows = rows
    text_data = '\r\n'.join('\t'.join(str(c) for c in row) for row in all_rows)

    widget.clipboard_clear()
    widget.clipboard_append(text_data)
    try:
        widget.update()
    except Exception:
        pass


def _make_html_payload(html_body):
    """
    Оборачивает HTML в формат Windows Clipboard HTML Format.
    См. https://docs.microsoft.com/en-us/windows/win32/dataxchg/html-clipboard-format
    """
    header_template = (
        "Version:0.9\r\n"
        "StartHTML:{start_html:010d}\r\n"
        "EndHTML:{end_html:010d}\r\n"
        "StartFragment:{start_frag:010d}\r\n"
        "EndFragment:{end_frag:010d}\r\n"
    )

    # Находим фрагмент (всё между <body> и </body>)
    body_start = html_body.find('<body>')
    if body_start < 0:
        body_start = 0
        fragment_start = 0
    else:
        fragment_start = body_start + len('<body>')

    body_end = html_body.find('</body>')
    if body_end < 0:
        body_end = len(html_body)
        fragment_end = body_end
    else:
        fragment_end = body_end

    # Собираем с временными плейсхолдерами, чтобы посчитать offset
    placeholder = header_template.format(
        start_html=0, end_html=0, start_frag=0, end_frag=0
    )
    header_len = len(placeholder)

    # Реальные offset
    start_html = header_len
    end_html = header_len + len(html_body)
    start_frag = header_len + fragment_start
    end_frag = header_len + fragment_end

    header = header_template.format(
        start_html=start_html,
        end_html=end_html,
        start_frag=start_frag,
        end_frag=end_frag,
    )

    return header + html_body


def _fallback_clipboard(widget, headers, rows):
    """Если pywin32 не установлен — обычное копирование текста."""
    all_rows = [headers] + rows
    text_data = '\r\n'.join('\t'.join(str(c) for c in row) for row in all_rows)

    widget.clipboard_clear()
    widget.clipboard_append(text_data)
    try:
        widget.update()
    except Exception:
        pass