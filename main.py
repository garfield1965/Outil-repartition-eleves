"""
Point d'entrée unique de l'application — à placer à la RACINE du projet.

Lancement :
    python main.py
    # ou
    python -m main

Le serveur web embarqué démarre et le navigateur s'ouvre automatiquement.

Pourquoi main.py est à la racine et non dans app/ ?
    Python résout les imports relatifs à partir du répertoire courant.
    Avec main.py dans app/, `import app.config` cherche un sous-package
    `app/app/` qui n'existe pas → erreur "app n'est pas un module".
    En restant à la racine, `app/` est bien vu comme un package du projet.
"""
import importlib
import threading
import webbrowser

import uvicorn


from app.config import settings


def _ouvrir_navigateur():
    webbrowser.open(f"http://{settings.host}:{settings.port}")


def main():
    threading.Timer(1.2, _ouvrir_navigateur).start()
    uvicorn.run(
        "app.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
