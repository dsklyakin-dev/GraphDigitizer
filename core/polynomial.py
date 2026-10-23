"""
Парсер формул Excel → точки (X, Y).
Поддерживает:
  - Полиномы: 0.5*x^2 - 3*x + 1
  - Обёртки =ЕСЛИ(переменная; формула; )
  - Вызовы макросов: ИмяМакроса('Лист'!$A$35:$B$44; переменная; 0)
    → для макросов используется линейная интерполяция по вставленным данным
v1.1 — исправлен поиск макроса и переменной
"""

import re
import math
import numpy as np


# ============================================================
# ИСКЛЮЧЕНИЯ
# ============================================================

class FormulaError(Exception):
    """Ошибка разбора или вычисления формулы."""
    pass


class MacroDetectedError(FormulaError):
    """Обнаружен вызов макроса — нужны данные для интерполяции."""
    def __init__(self, message, macro_name=None, sheet=None, cell_range=None,
                 var_name=None):
        super().__init__(message)
        self.macro_name = macro_name
        self.sheet = sheet
        self.cell_range = cell_range
        self.var_name = var_name


# ============================================================
# РЕГУЛЯРНЫЕ ВЫРАЖЕНИЯ
# ============================================================

# Excel-ссылка на ячейку: F94, A1, $E$14, $E14, E$14
CELL_REF_PATTERN = re.compile(r'\$?([A-Za-z]{1,3})\$?(\d+)')

# Диапазон: $A$35:$B$44 или A35:B44
CELL_RANGE_PATTERN = re.compile(
    r'\$?([A-Za-z]{1,3})\$?(\d+)\s*:\s*\$?([A-Za-z]{1,3})\$?(\d+)'
)

# Вызов макроса: ИмяМакроса(...)
# Ищем любое имя функции (латиница, кириллица, цифры, подчёркивания),
# которое НЕ является стандартной Excel-функцией.
MACRO_CALL_PATTERN = re.compile(
    r'([A-Za-zА-Яа-я_][A-Za-zА-Яа-я0-9_]*)\s*\(',
    re.UNICODE
)

# Стандартные Excel-функции — их не считаем макросами
EXCEL_FUNCTIONS = {
    'ЕСЛИ', 'IF', 'И', 'AND', 'ИЛИ', 'OR', 'НЕ', 'NOT',
    'СУММ', 'SUM', 'СРЗНАЧ', 'AVERAGE', 'МИН', 'MIN', 'МАКС', 'MAX',
    'ABS', 'КОРЕНЬ', 'SQRT', 'СТЕПЕНЬ', 'POWER', 'EXP', 'LN', 'LOG',
    'SIN', 'COS', 'TAN', 'ASIN', 'ACOS', 'ATAN',
    'ОКРУГЛ', 'ROUND', 'ОКРУГЛВНИЗ', 'FLOOR', 'ОКРУГЛВВЕРХ', 'CEILING',
    'ЦЕЛОЕ', 'INT', 'ОСТАТ', 'MOD', 'ЗНАК', 'SIGN',
    'ПИ', 'PI', 'СЛЧИС', 'RAND', 'СЛУЧМЕЖДУ', 'RANDBETWEEN',
    'ВПР', 'VLOOKUP', 'ГПР', 'HLOOKUP', 'ИНДЕКС', 'INDEX', 'ПОИСКПОЗ', 'MATCH',
    'ЕСЛИОШИБКА', 'IFERROR', 'ЕСНД', 'IFNA',
    'ТЕКСТ', 'TEXT', 'СЦЕПИТЬ', 'CONCATENATE', 'СЦЕП', 'CONCAT',
    'ЛЕВСИМВ', 'LEFT', 'ПРАВСИМВ', 'RIGHT', 'ПСТР', 'MID', 'ДЛСТР', 'LEN',
}

# Переменная x / X
VAR_X_PATTERN = re.compile(r'\b[xX]\b')


# ============================================================
# ОПРЕДЕЛЕНИЕ МАКРОСА
# ============================================================

def detect_macro(formula):
    """
    Ищет в формуле вызов макроса (не стандартной Excel-функции).

    Возвращает dict:
      - macro_name: имя макроса
      - sheet: имя листа (может быть None)
      - cell_range: диапазон (A35:B44) или None
      - var_cell: имя переменной (E14) или None
      - raw_match: полное совпадение вызова
    или None.
    """
    # Ищем все вызовы функций
    for m in MACRO_CALL_PATTERN.finditer(formula):
        func_name = m.group(1)
        func_upper = func_name.upper()

        # Пропускаем стандартные функции Excel
        if func_upper in EXCEL_FUNCTIONS:
            continue

        # Нашли потенциальный макрос
        macro_name = func_name

        # Теперь анализируем аргументы макроса.
        # Берём содержимое между этой '(' и соответствующей ')'.
        start = m.end()  # позиция сразу после '('
        depth = 1
        i = start
        while i < len(formula) and depth > 0:
            if formula[i] == '(':
                depth += 1
            elif formula[i] == ')':
                depth -= 1
            i += 1
        args_str = formula[start:i-1]

        # Ищем диапазон: 'Лист'!$A$35:$B$44
        sheet = None
        cell_range = None

        # Паттерн: 'Лист'!$A$35:$B$44  или  "Лист"!$A$35:$B$44  или  Лист!$A$35:$B$44
        sheet_range_match = re.search(
            r"[\'\"]([^\'\"]+)[\'\"]\s*!\s*" + CELL_RANGE_PATTERN.pattern,
            args_str
        )
        if sheet_range_match:
            sheet = sheet_range_match.group(1)
            col1, row1, col2, row2 = (sheet_range_match.group(2),
                                       sheet_range_match.group(3),
                                       sheet_range_match.group(4),
                                       sheet_range_match.group(5))
            cell_range = f"{col1}{row1}:{col2}{row2}"
        else:
            # Без листа: A35:B44
            range_match = CELL_RANGE_PATTERN.search(args_str)
            if range_match:
                col1, row1, col2, row2 = range_match.groups()
                cell_range = f"{col1}{row1}:{col2}{row2}"

        # Ищем переменную — первую одиночную ячейку в аргументах
        # (не входящую в диапазон).
        # Убираем диапазон из строки аргументов, чтобы он не попал в поиск.
        args_clean = args_str
        if cell_range:
            args_clean = args_clean.replace(cell_range, ' ')
            args_clean = re.sub(r'\$?[A-Za-z]+\$?\d+\s*:\s*\$?[A-Za-z]+\$?\d+', ' ', args_clean)

        # Ищем одиночные ссылки
        cell_refs = CELL_REF_PATTERN.findall(args_clean)
        var_cell = None
        if cell_refs:
            # Берём первую
            col, row = cell_refs[0]
            var_cell = f"{col}{row}"

        return {
            'macro_name': macro_name,
            'sheet': sheet,
            'cell_range': cell_range,
            'var_cell': var_cell,
            'raw_match': formula[m.start():i],
        }

    return None


# ============================================================
# ОПРЕДЕЛЕНИЕ ПЕРЕМЕННОЙ
# ============================================================

def detect_variable(formula, macro=None):
    """
    Определяет переменную X в формуле.

    Приоритет:
      1. Если есть макрос и у него есть var_cell — берём его.
      2. Ищем в условии =ЕСЛИ(<условие>; ...) — первую ячейку.
      3. Ищем во всей формуле самую частую Excel-ссылку
         (исключая диапазоны и var_cell уже учтён).
      4. Иначе — x / X.
    """
    # 1. Макрос
    if macro and macro.get('var_cell'):
        return macro['var_cell']

    # Убираем диапазоны из формулы, чтобы они не попали в поиск
    f_clean = re.sub(r'\$?[A-Za-z]+\$?\d+\s*:\s*\$?[A-Za-z]+\$?\d+', ' ', formula)

    # 2. Ищем в условии ЕСЛИ
    cond_match = re.match(
        r'\s*=?\s*(?:ЕСЛИ|IF)\s*\(\s*([^;,\)]+)',
        f_clean, re.IGNORECASE
    )
    if cond_match:
        cond = cond_match.group(1)
        refs = CELL_REF_PATTERN.findall(cond)
        if refs:
            col, row = refs[0]
            return f"{col}{row}"

    # 3. Самая частая ссылка во всей формуле
    refs = CELL_REF_PATTERN.findall(f_clean)
    if refs:
        from collections import Counter
        counter = Counter(f"{c}{r}" for c, r in refs)
        var, _ = counter.most_common(1)[0]
        return var

    # 4. x / X
    if VAR_X_PATTERN.search(formula):
        return 'x'

    return None


# ============================================================
# ИЗВЛЕЧЕНИЕ ТЕЛА ФОРМУЛЫ
# ============================================================

def extract_formula_body(formula):
    """
    Убирает обёртку =ЕСЛИ(условие; тело; ) и оставляет тело.
    Если обёртки нет — возвращает формулу как есть.
    Возвращает (body, condition, else_part).
    """
    f = formula.strip()
    if f.startswith('='):
        f = f[1:].strip()

    # ЕСЛИ / IF
    m = re.match(
        r'^(?:ЕСЛИ|IF)\s*\(\s*(.+?)\s*;\s*(.+?)\s*;\s*(.*?)\s*\)\s*$',
        f, re.IGNORECASE | re.DOTALL
    )
    if m:
        condition = m.group(1).strip()
        body = m.group(2).strip()
        else_part = m.group(3).strip()
        return body, condition, else_part

    return f, None, None


# ============================================================
# НОРМАЛИЗАЦИЯ И ВЫЧИСЛЕНИЕ
# ============================================================

def normalize_numbers(formula):
    """Заменяет десятичные запятые на точки."""
    f = formula.replace(';', ',')
    f = re.sub(r'(\d),(\d)', r'\1.\2', f)
    return f


def clean_polynomial(body):
    """Приводит тело формулы к Python-синтаксису."""
    f = body.strip()
    f = f.replace('^', '**')
    f = f.replace('$', '')
    f = normalize_numbers(f)
    return f


def evaluate_polynomial(body, var_name, x_value):
    """
    Вычисляет значение полинома для конкретного x.
    Поддерживает как обычные имена (x), так и Excel-ссылки (E14, $E$14).
    """
    f = clean_polynomial(body)

    # Заменяем переменную
    if var_name == 'x':
        expr = re.sub(r'\bx\b', str(x_value), f)
    else:
        expr = re.sub(r'\b' + re.escape(var_name) + r'\b', str(x_value), f)

    allowed = {
        'abs': abs, 'min': min, 'max': max, 'round': round,
        'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
        'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
        'exp': math.exp, 'log': math.log, 'log10': math.log10,
        'sqrt': math.sqrt, 'pi': math.pi, 'e': math.e,
        'pow': pow,
    }

    try:
        result = eval(expr, {'__builtins__': {}}, allowed)
    except ZeroDivisionError:
        raise FormulaError(f"Деление на ноль при x = {x_value}")
    except Exception as e:
        raise FormulaError(f"Ошибка вычисления: {e}\nВыражение: {expr}")

    if not isinstance(result, (int, float)) or math.isnan(result) or math.isinf(result):
        raise FormulaError(f"Результат не число при x = {x_value}: {result}")

    return float(result)


# ============================================================
# ИНТЕРПОЛЯЦИЯ ДЛЯ МАКРОСОВ
# ============================================================

class LinearInterpolator:
    """Линейная интерполяция по вставленным из Excel данным."""

    def __init__(self, x_data, y_data):
        if len(x_data) != len(y_data):
            raise FormulaError("Количество X и Y не совпадает")
        if len(x_data) < 2:
            raise FormulaError("Нужно минимум 2 точки для интерполяции")

        pairs = sorted(zip(x_data, y_data), key=lambda p: p[0])
        self.x = np.array([p[0] for p in pairs], dtype=float)
        self.y = np.array([p[1] for p in pairs], dtype=float)

    def __call__(self, x):
        return float(np.interp(x, self.x, self.y))


def parse_data_paste(text):
    """
    Разбирает вставленные из Excel данные.
    Поддерживает:
      - два столбца, разделённые табуляцией, запятой или точкой с запятой
      - десятичные запятые
    Возвращает (x_list, y_list).
    """
    x_list, y_list = [], []

    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        # Разделители: табуляция, точка с запятой, запятая
        parts = re.split(r'[\t;]', line, maxsplit=1)
        if len(parts) < 2:
            # Пробуем запятую (осторожно: десятичная тоже запятая)
            # Если в строке ровно одна запятая — это либо разделитель,
            # либо десятичный разделитель. Проверяем по контексту.
            comma_parts = line.split(',')
            if len(comma_parts) == 2:
                parts = comma_parts
            elif len(comma_parts) > 2:
                # Несколько запятых — вероятно, десятичные в одном числе
                # Берём первую как разделитель
                parts = [comma_parts[0], ','.join(comma_parts[1:])]
            else:
                continue

        if len(parts) < 2:
            continue

        try:
            x_str = parts[0].strip().replace(',', '.')
            y_str = parts[1].strip().replace(',', '.')
            x = float(x_str)
            y = float(y_str)
            x_list.append(x)
            y_list.append(y)
        except ValueError:
            continue

    if not x_list:
        raise FormulaError("Не удалось распознать данные. Нужно 2 столбца: X и Y")

    return x_list, y_list


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def build_points(
    formula,
    x_start,
    x_end,
    x_step,
    interpolator=None,
    max_points=10000,
):
    """
    Строит список точек (X, Y) по формуле.
    """
    if x_step <= 0:
        raise FormulaError("Шаг должен быть больше нуля")

    if x_end <= x_start:
        raise FormulaError("Конец X должен быть больше начала X")

    n_points = int((x_end - x_start) / x_step) + 1
    if n_points > max_points:
        raise FormulaError(
            f"Слишком много точек: {n_points} (максимум {max_points})."
        )

    # 1. Ищем макрос
    macro = detect_macro(formula)

    # 2. Определяем переменную
    var_name = detect_variable(formula, macro=macro)

    if var_name is None:
        raise FormulaError(
            "Не удалось определить переменную X.\n"
            "Ожидается Excel-ссылка (E14, F94) или x."
        )

    # 3. Если есть макрос — нужен интерполятор
    if macro is not None:
        if interpolator is None:
            raise MacroDetectedError(
                f"Обнаружен макрос «{macro['macro_name']}».\n"
                f"Лист: {macro['sheet'] or '—'}, "
                f"диапазон: {macro['cell_range'] or '—'}.\n"
                f"Переменная: {var_name}.\n"
                f"Скопируйте данные из диапазона и вставьте ниже.",
                macro_name=macro['macro_name'],
                sheet=macro['sheet'],
                cell_range=macro['cell_range'],
                var_name=var_name,
            )
        points = []
        x = x_start
        while x <= x_end + 1e-9:
            y = interpolator(x)
            points.append((round(x, 10), round(y, 10)))
            x += x_step
        return points

    # 4. Обычный полином
    body, condition, else_part = extract_formula_body(formula)

    if var_name != 'x' and var_name not in body:
        raise FormulaError(
            f"Переменная «{var_name}» не найдена в теле формулы.\n"
            f"Тело: {body[:150]}..."
        )

    points = []
    x = x_start
    while x <= x_end + 1e-9:
        y = evaluate_polynomial(body, var_name, x)
        points.append((round(x, 10), round(y, 10)))
        x += x_step

    return points


def validate_formula(formula):
    """
    Быстрая проверка формулы без вычисления.
    Возвращает (ok, message, is_macro).
    """
    try:
        macro = detect_macro(formula)
        if macro:
            var = macro.get('var_cell') or '—'
            return True, (
                f"Обнаружен макрос: {macro['macro_name']}\n"
                f"Лист: {macro.get('sheet') or '—'}\n"
                f"Диапазон: {macro.get('cell_range') or '—'}\n"
                f"Переменная: {var}"
            ), True

        var_name = detect_variable(formula)
        if var_name is None:
            return False, "Не найдена переменная (x, X или Excel-ссылка)", False

        body, _, _ = extract_formula_body(formula)
        evaluate_polynomial(body, var_name, 1.0)
        return True, f"Формула OK, переменная: {var_name}", False
    except FormulaError as e:
        return False, str(e), False
    except Exception as e:
        return False, f"Ошибка: {e}", False