# -*- mode: python ; coding: utf-8 -*-
# Run from repo root: pyinstaller packaging/reskiosk-hub.spec
# pathex so the tracer finds the hub package (avoids ModuleNotFoundError: No module named 'hub' when frozen)
import os
from PyInstaller.utils.hooks import collect_submodules, collect_all

# SPECPATH is a built-in variable provided by PyInstaller for the spec file's directory
_specdir = SPECPATH
_reskiosk_root = os.path.normpath(os.path.join(_specdir, '..'))

block_cipher = None

# Collect all numpy submodules (NumPy 2.x _core._exceptions etc.)
_hidden = collect_submodules('numpy')
_hidden += collect_submodules('numpy._core')
# Collect scipy and sklearn fully (including cython binaries and datas)
_scipy_datas, _scipy_binaries, _scipy_hidden = collect_all('scipy')
_sklearn_datas, _sklearn_binaries, _sklearn_hidden = collect_all('sklearn')
_hidden += _scipy_hidden
_hidden += _sklearn_hidden

from PyInstaller.utils.hooks import copy_metadata, get_package_paths

# Collect sentence_transformers and transformers fully
_st_datas, _st_binaries, _st_hidden = collect_all('sentence_transformers')
_tr_datas, _tr_binaries, _tr_hidden = collect_all('transformers')
_hidden += _st_hidden
_hidden += _tr_hidden

# Transformers often requires its top-level directory present for lazy imports (models/__init__.py)
_tr_pkg_path = get_package_paths('transformers')[1]
_tr_datas += copy_metadata('transformers')
_tr_datas.append((_tr_pkg_path, 'transformers'))
_hidden += [
    'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.lifespan', 'uvicorn.lifespan.on',
    'fastapi', 'huggingface_hub',
]

# Build datas list conditionally — only include dirs that exist
_datas = list(_st_datas) + list(_tr_datas) + list(_scipy_datas) + list(_sklearn_datas)
if os.path.isdir(os.path.join(_specdir, 'ollama_portable')):
    _datas.append(('ollama_portable', 'ollama_portable'))
if os.path.isdir(os.path.join(_specdir, 'hub_models')):
    _datas.append(('hub_models', 'hub_models'))
_console_dist = os.path.normpath(os.path.join(_specdir, '..', 'console', 'dist'))
if os.path.isdir(_console_dist):
    _datas.append(('../console/dist', 'console_static'))

# Combine binaries
_binaries = list(_st_binaries) + list(_tr_binaries) + list(_scipy_binaries) + list(_sklearn_binaries)

a = Analysis(
    ['../hub/launcher.py'],
    pathex=[_reskiosk_root],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'ipython', 'notebook'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True,  # Keep .pyc on disk so transformers os.listdir() works
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ResKiosk-Hub',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Keep console for debugging in Phase 0
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ResKiosk-Hub',
)
