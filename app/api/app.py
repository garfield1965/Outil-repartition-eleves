"""
Point d'assemblage : crée l'app FastAPI, branche les routeurs, les fichiers
statiques, initialise la base et insère les données de démo si besoin.

Ajouter une nouvelle fonctionnalité plus tard = créer un nouveau routes_*.py
puis l'inclure ici avec app.include_router(...). Le reste du code n'est pas
à toucher.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.database import init_db, SessionLocal
from app.services.seed import seed_si_vide

from app.api import (
    routes_classes, routes_eleves, routes_import, routes_stats,
    routes_classes_gestion, routes_admin, routes_export, routes_cycles,
)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    init_db()
    with SessionLocal() as db:
        seed_si_vide(db)

    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

    app.include_router(routes_classes.router)
    app.include_router(routes_eleves.router)
    app.include_router(routes_import.router)
    app.include_router(routes_stats.router)
    app.include_router(routes_classes_gestion.router)
    app.include_router(routes_admin.router)
    app.include_router(routes_export.router)
    app.include_router(routes_cycles.router)

    return app


app = create_app()
