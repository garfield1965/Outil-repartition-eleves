from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config import settings
from app.core.database import get_db
from app.core.models import Eleve, HistoriqueAffectation, eleve_propriete
from app.core.schemas import AffectationIn, AffectationGroupeIn, ProprietesEleveIn
from app.services.repartition import affecter_eleve, affecter_plusieurs_eleves, definir_proprietes_eleve

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.templates_dir))


class NouvelEleveIn(BaseModel):
    nom: str
    prenom: str
    sexe: str         # "F" ou "M"
    niveau_id: int
    classe_id: int    # classe d'origine


@router.post("/api/eleves")
def creer_eleve(payload: NouvelEleveIn, db: Session = Depends(get_db)):
    """Crée un élève manuellement (inscription en cours d'année)."""
    from app.core.models import Niveau, Classe as ClasseModel
    if db.get(Niveau, payload.niveau_id) is None:
        raise HTTPException(400, "Niveau introuvable")
    if db.get(ClasseModel, payload.classe_id) is None:
        raise HTTPException(400, "Classe introuvable")
    if payload.sexe not in ("F", "M"):
        raise HTTPException(400, "Sexe invalide (F ou M)")

    eleve = Eleve(
        nom=payload.nom.strip().upper(),
        prenom=payload.prenom.strip(),
        sexe=payload.sexe,
        niveau_id=payload.niveau_id,
        classe_origine_id=payload.classe_id,
    )
    db.add(eleve)
    db.commit()
    db.refresh(eleve)
    return {"id": eleve.id, "nom": eleve.nom, "prenom": eleve.prenom}


class DepartEleveIn(BaseModel):
    eleve_ids: list[int]


@router.delete("/api/eleves/quitter-ecole")
def quitter_ecole(payload: DepartEleveIn, db: Session = Depends(get_db)):
    """
    Supprime définitivement les élèves dont les ids sont fournis.
    N'est appelé QU'APRÈS confirmation explicite de l'utilisateur côté
    interface. Retourne les classes impactées pour que le front puisse
    les rafraîchir.
    """
    classes_impactees = set()
    noms_supprimes = []

    for eleve_id in payload.eleve_ids:
        eleve = db.get(Eleve, eleve_id)
        if eleve is None:
            continue
        if eleve.classe_origine_id:
            classes_impactees.add((eleve.classe_origine_id, True))
        if eleve.classe_destination_id:
            classes_impactees.add((eleve.classe_destination_id, False))
        noms_supprimes.append(f"{eleve.prenom} {eleve.nom}")

        # Nettoyage des tables d'association avant suppression
        db.execute(
            eleve_propriete.delete().where(eleve_propriete.c.eleve_id == eleve_id)
        )
        db.query(HistoriqueAffectation).filter_by(eleve_id=eleve_id).delete()
        db.delete(eleve)

    db.commit()
    return {
        "ok": True,
        "supprimes": noms_supprimes,
        "classes_impactees": [
            {"classe_id": cid, "origine": orig}
            for cid, orig in classes_impactees
        ],
    }



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
