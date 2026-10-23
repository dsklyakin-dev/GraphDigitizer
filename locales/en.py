STRINGS = {
    # === Titles, common ===
    'app.title': 'Graph Digitizer',
    'app.help_title': 'Help',
    'app.help_btn': 'Help',

    # === Language ===
    'lang.label': 'Language',
    'lang.ru': 'Русский',
    'lang.en': 'English',

    # === Modes ===
    'mode.1d': '1D Graph',
    'mode.2d': '2D Graph',
    'mode.1d_short': '1D',
    'mode.2d_short': '2D',

    'poly.copy_excel': 'Copy for Excel',
    'poly.copy_tsv': 'Copy as TSV',
    'poly.copied_excel': 'Copied (for Excel, delimiter ";"',
    'poly.copied_tsv': 'Copied (TSV, delimiter TAB)',

    'poly.open_excel': 'Open in Excel',
    'poly.opened_excel': 'Opened in Excel',
    'poly.opened_excel_text': 'File saved and opened:\n{path}',


    # === Panel buttons ===
    'btn.open': 'Open',
    'btn.auto_calib': 'Auto-calib.',
    'btn.manual_calib': 'Calibrate',
    'btn.multi_curve': '2+ curves',
    'btn.digitize': 'Digitize',
    'btn.assign_curve': 'Assign curve',
    'btn.manual': 'Manual',
    'btn.drag': 'Drag',
    'btn.delete': 'Delete',
    'btn.pencil': 'Pencil',
    'btn.segment': 'Segment',
    'btn.show': 'Show',
    'btn.save': 'Save',
    'btn.undo': 'Undo',
    'btn.clear': 'Clear all',
    'btn.help': 'Help',
    'btn.close': 'Close',
    'btn.ok': 'OK',
    'btn.cancel': 'Cancel',
    'btn.copy_all': 'Copy all',
    'btn.smooth': 'Smooth',
    'btn.multi_curve_on': 'Multiple curves in one: ON',
    'btn.multi_curve_off': 'Multiple curves in one: OFF',

    # === Panel titles ===
    'panel.control': 'CONTROL',
    'panel.settings': 'SETTINGS',
    'panel.legend': 'Curves',
    'panel.canvas': 'Graph area',
    'panel.no_image': 'No image loaded',

    # === Alignment ===
    'btn.align': 'Align',
    'status.aligning': 'Aligning...',
    'status.align_done': 'Aligned by {angle}°',
    'status.align_failed': 'Failed to align',
    'status.align_undone': 'Alignment undone',
    'msg.align_failed_text': 'Could not find lines to align.\n'
                             'Try rotating the image manually in an editor.',

    'status.pick_origin': 'Click on the ORIGIN',
    'status.pick_origin_hint': 'This is the intersection of X and Y axes',

    # === Toast notifications ===
    'toast.click_curve': '👆 Click on a curve point',
    'toast.click_points_2d': '👆 Click 2+ points along the curve\nEnter — finish',
    'toast.click_origin': '🎯 Click on the ORIGIN\n(intersection of X and Y axes)',
    'toast.pick_origin': '🎯 Click on the ORIGIN\n\nThis is the axes intersection',
    'toast.click_points_esc': '👆 Click points\nEsc — exit',
    'toast.delete_mode': '🗑 Hover over points to delete\nEsc — exit',
    'toast.pencil_mode': '✏️ Draw a line\nEsc — save',
    'toast.segment_first': '📏 Click the FIRST point',
    'toast.segment_second': '📏 Click the SECOND point',
    'toast.drag_mode': '✋ Drag a point\nEsc — exit',
    'toast.calib_done': '✅ Calibration complete',
    'toast.digitize_done': '✅ Digitized {n} points',
    'toast.copied': '📋 Copied to clipboard',
    'toast.saved': '💾 Data saved',
    'toast.align_done': '✅ Aligned by {angle}°',

    # === Theme ===
    'theme.restart_question': 'Theme changed. Restart the application now?',
    'theme.dark': 'Dark theme',
    'theme.light': 'Light theme',

    # === Settings ===
    'settings.step': 'Point step:',
    'settings.radius': 'Cursor width:',
    'settings.step_dialog_title': 'Point step',
    'settings.step_dialog_text': 'Enter step (1-50):',
    'settings.radius_dialog_title': 'Cursor width',
    'settings.radius_dialog_text': 'Enter width (5-50):',

    # === Statuses ===
    'status.image_loaded': 'Image loaded',
    'status.image_loaded_calib': 'Image loaded, calibration restored',
    'status.mode': 'Mode: {mode}',
    'status.multi_curve_on': 'Multi-curve mode: ON',
    'status.multi_curve_off': 'Multi-curve mode: OFF',
    'status.searching_axes': 'Searching axes...',
    'status.axes_not_found': 'Axes not found',
    'status.calib_done': 'Calibration complete',
    'status.can_digitize': 'You can digitize',
    'status.click_origin': 'Click on ORIGIN',
    'status.click_x_end': 'Click on X-AXIS END',
    'status.click_y_end': 'Click on Y-AXIS END',
    'status.calib_cancelled': 'Calibration cancelled',
    'status.calib_finished': 'Calibration finished',
    'status.step_1_3': 'Step 1 of 3',
    'status.step_2_3': 'Step 2 of 3',
    'status.step_3_3': 'Step 3 of 3',
    'status.click_curve': 'Click on the curve to digitize',
    'status.auto_search': 'Auto-search points left and right',
    'status.click_points_enter': 'Click points along the curve (Enter — finish)',
    'status.click_points_esc': 'Click points (Esc — exit)',
    'status.drag_point': 'Drag point (Esc — exit)',
    'status.drag_point_now': 'Drag point',
    'status.delete_mode': 'Deleting: hover over points (Esc — exit)',
    'status.pencil_mode': 'Draw (Esc — save, Ctrl+Z — undo)',
    'status.pencil_done': 'Line drawn',
    'status.segment_first': 'Click the first segment point',
    'status.segment_second': 'Click the second point',
    'status.segment_done': 'Segment drawn',
    'status.curve_not_found': 'Curve not found',
    'status.digitized': 'Digitized points: {n}',
    'status.undo_hint': 'Ctrl+Z — undo',
    'status.curve_points': 'Curve {name}: {n} points',
    'status.curve_points_copied': 'Curve {name}: {n} points (copied)',
    'status.points_needed_2': 'At least 2 points needed',
    'status.cancelled': 'Cancelled',
    'status.nothing_to_undo': 'Nothing to undo',
    'status.delete_cancelled': 'Deletion cancelled',
    'status.drawing_cancelled': 'Drawing cancelled',
    'status.cleared': 'Cleared',
    'status.zoom_reset': 'Zoom reset',
    'status.zoom': 'Zoom: {percent}%',
    'status.points_count': 'Points: {n}. Click more or press Enter',
    'status.calib_restored': 'Calibration restored',

    # === Messages ===
    'msg.warning': 'Warning',
    'msg.error': 'Error',
    'msg.done': 'Done',
    'msg.confirm': 'Confirmation',
    'msg.load_image_first': 'Load an image first',
    'msg.calib_first': 'Calibrate first',
    'msg.no_data': 'No data',
    'msg.no_points': 'No points',
    'msg.no_points_to_delete': 'No points to delete',
    'msg.load_failed': 'Failed to load image',
    'msg.save_failed': 'Failed to save',
    'msg.saved': 'Data saved:\n{path}',
    'msg.clear_confirm': 'Delete all points?',
    'msg.x3_question': 'Add X3 column?',
    'msg.x3_title': 'X3',
    'msg.x3_prompt': 'X3 value:',
    'msg.axes_not_found_text': 'Could not auto-detect axes.\nUse "Manual" — click 3 points.',
    'msg.compat_coords': 'Shared coordinates',
    'msg.compat_found': 'Found similar curve "{name}" ({n} points).\n\nUse its coordinates for X2={new}?',
    'msg.copied': 'Copied',
    'msg.copied_text': 'Data copied to clipboard',
    'msg.enter_value': 'Enter a value',

    # === X2Dialog ===
    'x2.title': 'New curve',
    'x2.prompt': 'Enter X2 value',
    'x2.hint': 'Example: Qt=10, T=350',

    # === DataViewer ===
    'dv.title': 'Graph points',
    'dv.1d_info': '1D mode — {n} points',
    'dv.2d_info': '2D mode — {curves} curves, {points} points',
    'dv.col_x': 'X',
    'dv.col_x2': 'X2',
    'dv.col_x3': 'X3',
    'dv.col_y': 'Y',

    # === CalibrationDialog ===
    'calib.title': 'Calibration',
    'calib.x0': 'X start',
    'calib.y0': 'Y start',
    'calib.x1': 'X end',
    'calib.y1': 'Y end',

    # === Polynomial ===
    'mode.poly': 'Formula',
    'mode.poly_short': 'Formula',
    'poly.dialog_title': 'Build from Formula',
    'poly.dialog_hint': 'Paste an Excel formula (polynomial or macro call).',
    'poly.formula': 'Formula:',
    'poly.check': 'Check',
    'poly.macro_data': 'Macro data (paste from Excel):',
    'poly.macro_data_hint': 'Two columns — X and Y. Separator: tab or comma.',
    'poly.range': 'X range',
    'poly.x_start': 'Start:',
    'poly.x_end': 'End:',
    'poly.x_step': 'Step:',
    'poly.extra': 'Additional columns',
    'poly.x2': 'X2:',
    'poly.x3': 'X3:',
    'poly.optional': 'optional',
    'poly.build': 'Build',
    'poly.result_title': 'Points from Formula',
    'poly.result_info': 'Total points: {n}',
    'poly.graph_view': 'Graph View',
    'poly.graph_title': 'Graph from Formula',
    'poly.graph_label': 'Y(X)',
    'poly.done_status': 'Built points: {n}',
    'poly.copy_excel': 'Copy for Excel',
    'poly.copy_tsv': 'Copy as TSV',
    'poly.copied_excel': 'Copied (for Excel, delimiter ";")',
    'poly.copied_tsv': 'Copied (TSV, delimiter TAB)',
    'poly.error_empty': 'Enter a formula',
    'poly.error_range': 'Check X range (numbers)',
    'poly.error_macro_data': 'Paste macro data',
    'poly.error_no_points': 'Failed to build points',
    'poly.macro_found': 'Macro detected: "{name}"\nSheet: {sheet}\nRange: {rng}\nCopy data from Excel and paste below.',

    # === Polynomial errors ===
    'poly.error_empty': 'Enter a formula',
    'poly.error_range': 'Check X range (numbers)',
    'poly.error_macro_data': 'Paste macro data',
    'poly.error_no_points': 'Failed to build points',
    'poly.macro_found': 'Macro detected: "{name}"\nSheet: {sheet}\nRange: {rng}\nCopy data from Excel and paste below.',

    # === Help ===
    'help.title': 'Application Help',
    'help.content': '''GRAPH DIGITIZER — HELP

GENERAL
───────
The program digitizes graphs (converts an image
into a table of X, Y values).

1. OPENING AN IMAGE
───────────────────
• Click "Open" and select a graph file
  (.jpg, .png, .bmp, .tiff).
• The image will appear in the center.

2. CALIBRATION
──────────────
Calibration binds pixels to real values.

AUTO-CALIBRATION:
• Click "Auto-calib." — the program finds the axes.
• Enter X0 Y0 X1 Y1 (start and end of axes).

MANUAL CALIBRATION:
• Click "Calibrate" — enter axis values.
• Click 3 points:
  1) Origin
  2) End of X axis
  3) End of Y axis

3. MODE SELECTION
─────────────────
• 1D Graph — single curve (X, Y).
• 2D Graph — multiple curves (X, X2, Y),
  where X2 is the curve name (e.g., Qt=10).

4. 1D DIGITIZATION
──────────────────
• Click "Digitize".
• Click any point on the curve — the program
  automatically follows the curve left and right.

5. 2D DIGITIZATION
──────────────────
• Click "Assign curve".
• Click 2+ anchor points along the curve.
• Press Enter.
• Enter X2 (curve name) — the program builds
  the curve between anchor points.

6. TOOLS
────────
• "Manual" — manually place points.
• "Drag" — drag points.
• "Delete" — delete points (hover over them).
• "Pencil" — draw a line by hand.
• "Segment" — draw a straight line.

7. VIEW AND SAVE
────────────────
• "Show" — open the point table.
• "Save" — export to Excel or CSV.
• "Undo" — roll back the last action (Ctrl+Z).
• "Clear all" — delete all points.

HOTKEYS
───────
Ctrl+O — open image
Ctrl+S — save data
Ctrl+Z — undo action
Ctrl+0 — reset zoom
F1     — this help
Esc    — cancel current mode
Enter  — finish 2D digitization

NAVIGATION
──────────
LMB (hold) — pan
Ctrl + wheel — zoom
''',
}