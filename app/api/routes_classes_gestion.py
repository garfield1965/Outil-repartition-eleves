"""
Routes d'administration des classes : créer/modifier/supprimer une classe
cible (N+1), déplacer librement une carte sur le tableau, la replier en
bandeau. Séparé de routes_classes.py (qui ne fait que de l'affichage) pour
garder chaque fichier focalisé sur une responsabilité.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import Annee, Niveau
from app.core.schemas import ClasseCreateIn, ClasseUpdateIn, ClassePositionIn, ClasseReplieeIn
from app.services import gestion_classes

router = APIRouter()


@router.get("/api/niveaux")
def lister_niveaux(db: Session = Depends(get_db)):
    niveaux = db.query(Niveau).order_by(Niveau.ordre, Niveau.libelle).all()
    return [{"id": n.id, "libelle": n.libelle, "couleur": n.couleur} for n in niveaux]


@router.post("/api/classes")
def creer_classe(payload: ClasseCreateIn, db: Session = Depends(get_db)):
    annee = db.query(Annee).filter_by(
        est_annee_cible=payload.cible, est_annee_origine=not payload.cible
    ).first()
    if annee is None:
        raise HTTPException(400, "Année introuvable (origine ou cible selon le cas)")

    classe = gestion_classes.creer_classe(
        db, annee.id, payload.nom, payload.niveau_ids,
        payload.effectif_cible, payload.couleur,
    )
    return {"ok": True, "classe_id": classe.id}


@router.patch("/api/classes/{classe_id}")
def modifier_classe(classe_id: int, payload: ClasseUpdateIn, db: Session = Depends(get_db)):
    try:
        gestion_classes.modifier_classe(
            db, classe_id, payload.nom, payload.niveau_ids,
            payload.effectif_cible, payload.couleur,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@router.delete("/api/classes/{classe_id}")
def supprimer_classe(classe_id: int, db: Session = Depends(get_db)):
    try:
        nb_desaffectes = gestion_classes.supprimer_classe(db, classe_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "eleves_desaffectes": nb_desaffectes}


@router.patch("/api/classes/{classe_id}/position")
def deplacer_classe(classe_id: int, payload: ClassePositionIn, db: Session = Depends(get_db)):
    try:
        gestion_classes.deplacer_classe(db, classe_id, payload.position_x, payload.position_y)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@router.patch("/api/classes/{classe_id}/repli")
def basculer_repli(classe_id: int, payload: ClasseReplieeIn, db: Session = Depends(get_db)):
    try:
        gestion_classes.basculer_repli(db, classe_id, payload.repliee)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}
