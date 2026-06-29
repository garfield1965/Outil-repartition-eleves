"""
Point d'entrée unique de l'application.

Lance le serveur web embarqué et ouvre automatiquement le navigateur,
afin que l'enseignant n'ait qu'à double-cliquer sur l'exécutable.
"""
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
