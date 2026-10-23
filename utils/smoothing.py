import numpy as np

# В самом верху файла (вне функции) добавим попытку импорта
try:
    from scipy.signal import savgol_filter

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("[Smoothing] scipy не установлен, будет использоваться скользящее среднее.")


def smooth_savgol(points, window_size=5, polyorder=2, max_deviation_ratio=0.05):
    """Фильтр Савицкого-Голея с защитой от выбросов."""
    try:
        from scipy.signal import savgol_filter
    except ImportError:
        print("[Smoothing] scipy не установлен, используется скользящее среднее.")
        return smooth_moving_average(points, window_size)

    if window_size < 3 or len(points) < window_size:
        return points

    sorted_pts = sorted(points, key=lambda p: p[0])
    x_vals = np.array([p[0] for p in sorted_pts])
    y_vals = np.array([p[1] for p in sorted_pts])

    if window_size % 2 == 0:
        window_size += 1
    if window_size <= polyorder:
        window_size = polyorder + 2 if polyorder % 2 == 0 else polyorder + 1

    y_smooth = savgol_filter(y_vals, window_length=window_size, polyorder=polyorder)

    # ЗАЩИТА ОТ ВЫБРОСОВ
    y_range = np.max(y_vals) - np.min(y_vals)
    max_dev = y_range * max_deviation_ratio if y_range > 0 else 0

    for i in range(len(y_vals)):
        if abs(y_smooth[i] - y_vals[i]) > max_dev:
            y_smooth[i] = y_vals[i]  # Откат к оригиналу

    return [(float(x), float(y)) for x, y in zip(x_vals, y_smooth)]


def smooth_moving_average(points, window_size=5, max_deviation_ratio=0.05):
    """Скользящее среднее с защитой от резких выбросов."""
    if window_size < 3 or len(points) < window_size:
        return points

    sorted_pts = sorted(points, key=lambda p: p[0])
    x_vals = np.array([p[0] for p in sorted_pts])
    y_vals = np.array([p[1] for p in sorted_pts])

    if window_size % 2 == 0:
        window_size += 1

    kernel = np.ones(window_size) / window_size
    y_smooth = np.convolve(y_vals, kernel, mode='same')

    # Края convolve портит, возвращаем там оригинал
    half = window_size // 2
    y_smooth[:half] = y_vals[:half]
    y_smooth[-half:] = y_vals[-half:]

    # ЗАЩИТА ОТ ВЫБРОСОВ: если сглаженное значение ушло слишком далеко,
    # возвращаем оригинал
    y_range = np.max(y_vals) - np.min(y_vals)
    max_dev = y_range * max_deviation_ratio if y_range > 0 else 0

    for i in range(len(y_vals)):
        if abs(y_smooth[i] - y_vals[i]) > max_dev:
            y_smooth[i] = y_vals[i]  # Откат к оригиналу

    return [(float(x), float(y)) for x, y in zip(x_vals, y_smooth)]


def smooth_savgol(points, window_size=5, polyorder=2):
    """
    Фильтр Савицкого-Голея. Лучше сохраняет форму пиков.
    Если scipy не установлен — откатывается на скользящее среднее.
    """
    try:
        from scipy.signal import savgol_filter
    except ImportError:
        print("[Smoothing] scipy не установлен, используется скользящее среднее.")
        return smooth_moving_average(points, window_size)

    if window_size < 3 or len(points) < window_size:
        return points

    sorted_pts = sorted(points, key=lambda p: p[0])
    x_vals = np.array([p[0] for p in sorted_pts])
    y_vals = np.array([p[1] for p in sorted_pts])

    if window_size % 2 == 0:
        window_size += 1
    if window_size <= polyorder:
        window_size = polyorder + 2 if polyorder % 2 == 0 else polyorder + 1

    y_smooth = savgol_filter(y_vals, window_length=window_size, polyorder=polyorder)

    return [(float(x), float(y)) for x, y in zip(x_vals, y_smooth)]