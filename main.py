"""
Point d'entrée unique de l'application — à placer à la RACINE du projet.

Lancement :
    python main.py

Le serveur web embarqué démarre et le navigateur s'ouvre automatiquement.

Note PyInstaller (console=False) :
    Quand l'application tourne comme exécutable sans fenêtre console,
    sys.stdout et sys.stderr sont None. Uvicorn appelle .isatty() sur ces
    flux pour décider d'utiliser les couleurs ANSI → AttributeError.
    On les redirige vers un fichier log avant toute autre chose, et on
    passe une config logging minimaliste à uvicorn pour éviter le
    DefaultFormatter qui provoque le crash.
"""
import os
import sys
import threading
import webbrowser

# ---- Patch obligatoire avant tout import uvicorn ----
# Quand PyInstaller génère un exécutable sans console (console=False),
# sys.stdout et sys.stderr sont None. On les remplace par un vrai flux
# de fichier pour éviter les AttributeError dans uvicorn/logging.
if getattr(sys, "frozen", False) and sys.stdout is None:
    _log_path = os.path.join(os.path.dirname(sys.executable), "repartition_eleves.log")
    _log_file = open(_log_path, "w", encoding="utf-8", buffering=1)
    sys.stdout = _log_file
    sys.stderr = _log_file

import uvicorn
from app.config import settings

# Config logging sans le DefaultFormatter coloré d'uvicorn
# (celui-ci appelle .isatty() et plante en mode fenêtré sans console).
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s - %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
}


def _ouvrir_navigateur():
    webbrowser.open(f"http://{settings.host}:{settings.port}")


def main():
    threading.Timer(1.2, _ouvrir_navigateur).start()
    uvicorn.run(
        "app.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_config=LOG_CONFIG,
    )


if __name__ == "__main__":
    main()
