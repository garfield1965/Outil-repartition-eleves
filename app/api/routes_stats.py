"""
Endpoint JSON pur (utile pour un futur tableau de bord ou export).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import Classe
from app.services.stats import calculer_stats_classe

router = APIRouter()


@router.get("/api/stats/{classe_id}")
def stats_classe(classe_id: int, origine: bool = True, db: Session = Depends(get_db)):
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise HTTPException(404, "Classe introuvable")

    eleves = classe.eleves_origine if origine else classe.eleves_destination
    if origine:
        eleves = [e for e in eleves if e.classe_destination_id is None]

    return calculer_stats_classe(db, classe, eleves)
