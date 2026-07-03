# -*- mode: python ; coding: utf-8 -*-
"""
Fichier .spec PyInstaller pour "Répartition des élèves".

Générer l'exécutable (depuis la racine, venv activé) :
    pyinstaller repartition_eleves.spec

Pourquoi un .spec plutôt que des arguments CLI ?
    Le .spec donne un contrôle total sur la collecte des packages locaux.
    Avec --collect-all app en CLI, PyInstaller collecte les sources mais
    peut rater les sous-packages sur Windows si le chemin courant n'est
    pas dans sys.path au moment de l'analyse.
    Ici on force explicitement tout le package `app` ET ses données.
"""
import os
from pathlib import Path

RACINE = Path(SPECPATH)   # répertoire contenant ce .spec = racine du projet

# ---- Collecte explicite de TOUS les sous-modules du package `app` ----
# hiddenimports liste chaque module séparément : PyInstaller inclut ainsi
# les fichiers .pyc même si aucun autre module ne les importe directement.
HIDDEN_IMPORTS = [
    # Package local -- tous les sous-modules listés explicitement
    "app",
    "app.config",
    "app.api",
    "app.api.app",
    "app.api.routes_admin",
    "app.api.routes_classes",
    "app.api.routes_classes_gestion",
    "app.api.routes_eleves",
    "app.api.routes_export",
    "app.api.routes_import",
    "app.api.routes_stats",
    "app.core",
    "app.core.database",
    "app.core.models",
    "app.core.palette",
    "app.core.schemas",
    "app.services",
    "app.services.export_pdf",
    "app.services.gestion_classes",
    "app.services.gestion_referentiel",
    "app.services.import_onde",
    "app.services.regles",
    "app.services.repartition",
    "app.services.seed",
    "app.services.stats",
    # uvicorn (chargements dynamiques non détectés par l'analyse statique)
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.loops.uvloop",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    # SQLAlchemy dialects
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.pysqlite",
    # anyio backends
    "anyio",
    "anyio._backends._asyncio",
    "anyio._backends._trio",
    # Starlette
    "starlette.routing",
    "starlette.staticfiles",
    "starlette.templating",
    # Encodeurs email utilisés par certaines dépendances
    "email.mime.multipart",
    "email.mime.text",
]

# ---- Données statiques à embarquer ----
DATAS = [
    (str(RACINE / "app" / "static"),    "app/static"),
    (str(RACINE / "app" / "templates"), "app/templates"),
]

a = Analysis(
    [str(RACINE / "main.py")],
    pathex=[str(RACINE)],   # ← crucial : ajoute la RACINE à sys.path
                             #   pendant l'analyse, ce qui permet à
                             #   PyInstaller de trouver le package `app`
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="repartition_eleves",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # pas de fenêtre console noire au lancement
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
