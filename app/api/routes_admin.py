"""
Routes de la section "Administration" : page dédiée (hors du tableau
principal) pour gérer le référentiel (niveaux, propriétés) et réinitialiser
les données d'une année sur l'autre.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings, version_assets
from app.core.database import get_db
from app.core.models import Niveau, Propriete
from app.core.schemas import (
    NiveauCreateIn, NiveauUpdateIn, ProprieteCreateIn, ProprieteUpdateIn,
    RegleCreateIn, RegleUpdateIn,
)
from app.services import gestion_referentiel, regles as service_regles

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.templates_dir))


@router.get("/admin")
def page_admin(request: Request, db: Session = Depends(get_db)):
    niveaux = db.query(Niveau).order_by(Niveau.ordre, Niveau.libelle).all()
    proprietes = db.query(Propriete).order_by(Propriete.libelle).all()
    regles = service_regles.lister_regles(db)
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "niveaux": niveaux,
            "proprietes": proprietes,
            "regles": regles,
            "types_regle": service_regles.TYPES_REGLE,
            "asset_version": version_assets("css/theme.css", "js/admin.js"),
        },
    )


# ---------- Niveaux ----------

@router.post("/api/niveaux")
def creer_niveau(payload: NiveauCreateIn, db: Session = Depends(get_db)):
    niveau = gestion_referentiel.creer_niveau(db, payload.libelle, payload.couleur, payload.ordre)
    return {"ok": True, "niveau_id": niveau.id}


@router.patch("/api/niveaux/{niveau_id}")
def modifier_niveau(niveau_id: int, payload: NiveauUpdateIn, db: Session = Depends(get_db)):
    try:
        gestion_referentiel.modifier_niveau(
            db, niveau_id, payload.libelle, payload.couleur, payload.ordre
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@router.delete("/api/niveaux/{niveau_id}")
def supprimer_niveau(niveau_id: int, db: Session = Depends(get_db)):
    try:
        gestion_referentiel.supprimer_niveau(db, niveau_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


# ---------- Propriétés ----------

@router.post("/api/proprietes")
def creer_propriete(payload: ProprieteCreateIn, db: Session = Depends(get_db)):
    propriete = gestion_referentiel.creer_propriete(db, payload.libelle, payload.couleur, payload.icone)
    return {"ok": True, "propriete_id": propriete.id}


@router.patch("/api/proprietes/{propriete_id}")
def modifier_propriete(propriete_id: int, payload: ProprieteUpdateIn, db: Session = Depends(get_db)):
    try:
        gestion_referentiel.modifier_propriete(
            db, propriete_id, payload.libelle, payload.couleur, payload.icone
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@router.delete("/api/proprietes/{propriete_id}")
def supprimer_propriete(propriete_id: int, db: Session = Depends(get_db)):
    try:
        resultat = gestion_referentiel.supprimer_propriete(db, propriete_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True, "eleves_concernes": resultat["eleves"], "regles_concernees": resultat["regles"]}


# ---------- Règles de gestion ----------

@router.post("/api/regles")
def creer_regle(payload: RegleCreateIn, db: Session = Depends(get_db)):
    try:
        regle = service_regles.creer_regle(
            db, payload.libelle, payload.type_regle, payload.seuil,
            payload.propriete_id, payload.actif,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "regle_id": regle.id}


@router.patch("/api/regles/{regle_id}")
def modifier_regle(regle_id: int, payload: RegleUpdateIn, db: Session = Depends(get_db)):
    try:
        service_regles.modifier_regle(
            db, regle_id, payload.libelle, payload.type_regle,
            payload.seuil, payload.propriete_id, payload.actif,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@router.delete("/api/regles/{regle_id}")
def supprimer_regle(regle_id: int, db: Session = Depends(get_db)):
    try:
        service_regles.supprimer_regle(db, regle_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


# ---------- Bascule d'année scolaire ----------

@router.get("/api/admin/bascule/bilan")
def bilan_bascule(db: Session = Depends(get_db)):
    from app.services.bascule_annee import bilan_bascule as _bilan
    return _bilan(db)


@router.post("/api/admin/bascule/executer")
def executer_bascule(db: Session = Depends(get_db)):
    from app.services.bascule_annee import executer_bascule as _executer
    try:
        return _executer(db)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


# ---------- Réinitialisation ----------

@router.post("/api/admin/reinitialiser")
def reinitialiser(db: Session = Depends(get_db)):
    """
    Repart d'une page blanche pour les classes/élèves/années EN CONSERVANT
    les niveaux et propriétés. Action destructive : la confirmation est
    gérée côté interface (double confirmation avant l'appel).
    """
    resultat = gestion_referentiel.reinitialiser_donnees(db)
    return {"ok": True, **resultat}
