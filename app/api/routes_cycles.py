"""
Routes de gestion des cycles pédagogiques et de leurs statistiques.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.schemas import CycleCreateIn, CycleUpdateIn
from app.services.gestion_cycles import (
    lister_cycles, creer_cycle, modifier_cycle,
    supprimer_cycle, affecter_niveau_a_cycle,
)

router = APIRouter()


@router.get("/api/cycles")
def get_cycles(db: Session = Depends(get_db)):
    cycles = lister_cycles(db)
    return [
        {
            "id": c.id, "libelle": c.libelle,
            "description": c.description, "ordre": c.ordre,
            "niveaux": [
                {"id": n.id, "libelle": n.libelle, "couleur": n.couleur, "ordre": n.ordre}
                for n in sorted(c.niveaux, key=lambda n: n.ordre)
            ],
        }
        for c in cycles
    ]


@router.post("/api/cycles")
def post_cycle(payload: CycleCreateIn, db: Session = Depends(get_db)):
    cycle = creer_cycle(db, payload.libelle, payload.description, payload.ordre)
    return {"ok": True, "cycle_id": cycle.id}


@router.patch("/api/cycles/{cycle_id}")
def patch_cycle(cycle_id: int, payload: CycleUpdateIn, db: Session = Depends(get_db)):
    try:
        modifier_cycle(db, cycle_id, payload.libelle, payload.description, payload.ordre)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@router.delete("/api/cycles/{cycle_id}")
def delete_cycle(cycle_id: int, db: Session = Depends(get_db)):
    try:
        nb = supprimer_cycle(db, cycle_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True, "niveaux_delies": nb}


@router.patch("/api/niveaux/{niveau_id}/cycle")
def patch_niveau_cycle(
    niveau_id: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Rattache ou détache un niveau d'un cycle (payload: {cycle_id: int|null})."""
    cycle_id = payload.get("cycle_id")
    try:
        affecter_niveau_a_cycle(db, niveau_id, cycle_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}
