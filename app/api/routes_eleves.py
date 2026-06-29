"""
Route appelée par le JavaScript à chaque "drop" d'un élève sur une classe.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.core.models import Eleve
from app.core.schemas import AffectationIn, AffectationGroupeIn, ProprietesEleveIn
from app.services.repartition import affecter_eleve, affecter_plusieurs_eleves, definir_proprietes_eleve

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.templates_dir))


@router.get("/api/eleves/{eleve_id}")
def detail_eleve(eleve_id: int, db: Session = Depends(get_db)):
    """Renvoie les informations d'un élève, dont ses propriétés actuelles
    (ULIS, TDAH...), pour alimenter la fiche d'édition côté interface."""
    eleve = db.get(Eleve, eleve_id)
    if eleve is None:
        raise HTTPException(404, "Élève introuvable")
    return {
        "id": eleve.id,
        "nom": eleve.nom,
        "prenom": eleve.prenom,
        "sexe": eleve.sexe,
        "niveau_libelle": eleve.niveau.libelle if eleve.niveau else "",
        "propriete_ids": [p.id for p in eleve.proprietes],
    }


@router.patch("/api/eleves/{eleve_id}/proprietes")
def modifier_proprietes_eleve(
    eleve_id: int, payload: ProprietesEleveIn, db: Session = Depends(get_db)
):
    """Remplace la liste des propriétés d'un élève (ajout ET retrait en un
    seul appel : le front envoie la liste complète des propriétés cochées)."""
    try:
        definir_proprietes_eleve(db, eleve_id, payload.propriete_ids)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@router.patch("/api/eleves/{eleve_id}/affecter")
def affecter(eleve_id: int, payload: AffectationIn, db: Session = Depends(get_db)):
    """
    Déplace un élève vers sa classe destination (ou le retire si null).
    Le front (app.js) déclenche ensuite le rafraîchissement des 2 cartes
    concernées via une requête sur /fragments/classe/{id}.
    """
    eleve_avant = affecter_eleve(db, eleve_id, payload.classe_destination_id)
    return {
        "ok": True,
        "eleve_id": eleve_avant.id,
        "classe_origine_id": eleve_avant.classe_origine_id,
        "classe_destination_id": eleve_avant.classe_destination_id,
    }


@router.patch("/api/eleves/affecter-groupe")
def affecter_groupe(payload: AffectationGroupeIn, db: Session = Depends(get_db)):
    """
    Déplace plusieurs élèves sélectionnés ensemble (sélection multiple,
    Ctrl/Cmd + clic côté interface) vers la même classe destination.
    """
    eleves = affecter_plusieurs_eleves(db, payload.eleve_ids, payload.classe_destination_id)
    return {
        "ok": True,
        "eleves_deplaces": [e.id for e in eleves],
        "classe_destination_id": payload.classe_destination_id,
    }


@router.get("/api/eleves/{eleve_id}/icone")
def icone_eleve(eleve_id: int, request: Request, db: Session = Depends(get_db)):
    """Renvoie le fragment HTML de l'icône d'un seul élève (réutilisable)."""
    eleve = db.get(Eleve, eleve_id)
    return templates.TemplateResponse(
        "partials/eleve_icon.html", {"request": request, "eleve": eleve}
    )
