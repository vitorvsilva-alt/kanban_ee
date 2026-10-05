# kanban_build.spec
# Arquivo de configuração do PyInstaller para o Sistema Kanban Estratégico

import os
import sys
from pathlib import Path
# 1. Adicione 'collect_submodules' nos imports abaixo:
from PyInstaller.utils.hooks import copy_metadata, collect_data_files, collect_submodules

# ── Caminhos base ────────────────────────────────────────────────────────────
SITE_PACKAGES = Path(sys.executable).parent / "Lib" / "site-packages"
PROJECT_DIR   = os.path.abspath(".")

# ── Dados adicionais a incluir no bundle ─────────────────────────────────────
added_files = [
    # Código-fonte da aplicação
    (os.path.join(PROJECT_DIR, "app.py"),           "."),
    (os.path.join(PROJECT_DIR, "database.py"),       "."),
    (os.path.join(PROJECT_DIR, "business_logic.py"), "."),

    # Planilha original
    (os.path.join(PROJECT_DIR, "Planilha de controle - Planejamento.xlsx"), "."),

    # Metadados do Streamlit
    *copy_metadata("streamlit"),

    # Arquivos estáticos do Streamlit
    *collect_data_files("streamlit"),

    # Altair: schemas Vega-Lite embutidos
    (str(SITE_PACKAGES / "altair" / "vegalite" / "schema"), "altair/vegalite/schema"),

    # Pandas: tabelas de fuso horário (tzdata)
    *[(str(p), str(p.relative_to(SITE_PACKAGES))) for p in (SITE_PACKAGES / "pandas").rglob("*.json") if "tests" not in str(p)],
]

added_files = [(src, dst) for src, dst in added_files if os.path.exists(src)]

# ── Módulos ocultos (Importa TODOS os submódulos do Streamlit) ────────────────
hidden_imports = [
    # 2. Coleta automaticamente todos os submódulos do Streamlit (incluindo magic_funcs e scriptrunner)
    *collect_submodules("streamlit"),
    
    # DuckDB
    "duckdb",
    # Pandas / numpy
    "pandas",
    "pandas._libs.tslibs.nattype",
    "pandas._libs.tslibs.np_datetime",
    "pandas._libs.reduction",
    "numpy",
    # Openpyxl
    "openpyxl",
    "openpyxl.workbook",
    # Altair / jsonschema
    "altair",
    "altair.vegalite",
    "altair.vegalite.core",
    "jsonschema",
    "jsonschema.validators",
    # Typing e stdlib
    "typing_extensions",
    "click",
    "packaging",
    "importlib.metadata",
    "importlib.resources",
    "email.mime",
    "email.mime.text",
    "email.mime.multipart",
    "tornado",
    "tornado.web",
    "tornado.websocket",
    "tornado.httpserver",
    "tornado.ioloop",
    "watchdog",
    "rich",
    "pyarrow",
]

a = Analysis(
    ["launcher.py"],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PyQt6", "wx", "matplotlib", "scipy", "sklearn"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KanbanEstrategico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="KanbanEstrategico",
)