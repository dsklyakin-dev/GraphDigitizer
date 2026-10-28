# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('tesseract', 'tesseract'),        # Папка с портативным Tesseract (exe + DLL + tessdata)
        ('locales', 'locales'),            # Файлы локализации (ru.py, en.py)
        # Если у вас есть иконка, раскомментируйте и укажите путь:
        # ('icon.ico', '.'),
    ],
    hiddenimports=[
        'unicodedata',                     # Фикс для Python 3.11
        'scipy',                           # Для сглаживания (Savitzky-Golay)
        'scipy.signal',
        'scipy.special',
        'numpy',
        'pytesseract',
        'PIL',
        'PIL._tkinter_finder',
        'customtkinter',
        'openpyxl',
        'pandas',
        'win32clipboard',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.simpledialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GraphDigitizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                         # False = без черного окна консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                             # Если есть иконка, укажите путь: 'icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GraphDigitizer',                 # Имя итоговой папки в dist/
)