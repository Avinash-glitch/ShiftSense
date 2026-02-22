# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Collect Streamlit's data files
streamlit_datas = collect_data_files('streamlit')

a = Analysis(
    ['main.py'],
    pathex=[r'C:\Users\avikann\rota'],
    binaries=[],
    datas=[
        ('streamlit_new.py', '.'),
        ('parse_json.py', '.'),
        ('test_dataextraction_holiday.py', '.'),
        ('coverage.py', '.'),
        ('daily_assignment.py', '.'),
        ('debugger.py', '.'),
        ('create_shift_lists.py', '.'),
        ('get_eligible_employees.py', '.'),
        ('holiday_tracker.xlsx', '.'),
        ('logo1.png','.'),
        ('icon.png','.'),

       
    ] + streamlit_datas,  # ✅ Add Streamlit's static files
    hiddenimports=[
        'streamlit',
        'streamlit.web.cli',
        'streamlit.runtime.scriptrunner.magic_funcs',
        'streamlit.runtime.scriptrunner.script_runner',
        'pandas',
        'openpyxl',
        'altair',
        'watchdog',
        'tornado',
        'validators',
        'packaging',
        'pympler',
        'pillow',
        'pyarrow',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Shift Sense',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep this True for now
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo1.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Shift Sense',
)

