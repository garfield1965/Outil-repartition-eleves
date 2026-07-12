"""
Endpoints JSON de statistiques.
Les routes avec segments fixes (/ecole/global, /cycles) sont déclarées
AVANT la route paramétrique /{classe_id} pour éviter qu'elles soient
capturées par cette dernière.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import Classe, Annee, Eleve, Propriete
from app.services.stats import calculer_stats_classe

router = APIRouter()


@router.get("/api/stats/ecole/global")
def stats_ecole(db: Session = Depends(get_db)):
    """Statistiques globales de l'école pour l'année N et N+1."""
    annee_n = db.query(Annee).filter_by(est_annee_origine=True).first()
    annee_n1 = db.query(Annee).filter_by(est_annee_cible=True).first()
    toutes_proprietes = db.query(Propriete).order_by(Propriete.libelle).all()

    def stats_pour_annee(annee):
        if annee is None:
            return None
        classes = db.query(Classe).filter_by(annee_id=annee.id).all()
        if annee.est_annee_origine:
            eleves = db.query(Eleve).filter(
                Eleve.classe_origine_id.in_([c.id for c in classes])
            ).all()
        else:
            eleves = db.query(Eleve).filter(
                Eleve.classe_destination_id.in_([c.id for c in classes])
            ).all()

        total = len(eleves)
        filles = sum(1 for e in eleves if e.sexe == "F")
        garcons = total - filles

        par_propriete = []
        for p in toutes_proprietes:
            nb = sum(1 for e in eleves if any(ep.id == p.id for ep in e.proprietes))
            par_propriete.append({
                "id": p.id, "libelle": p.libelle, "couleur": p.couleur,
                "nombre": nb,
                "pourcentage": round(nb / total * 100, 1) if total > 0 else 0.0,
            })

        return {
            "libelle": annee.libelle, "total": total,
            "filles": filles, "garcons": garcons,
            "pct_filles": round(filles / total * 100, 1) if total > 0 else 0.0,
            "pct_garcons": round(garcons / total * 100, 1) if total > 0 else 0.0,
            "par_propriete": par_propriete,
        }

    return {"annee_n": stats_pour_annee(annee_n), "annee_n1": stats_pour_annee(annee_n1)}


@router.get("/api/stats/cycles")
def stats_cycles_route(db: Session = Depends(get_db)):
    """Statistiques par cycle pédagogique."""
    from app.services.gestion_cycles import stats_cycles
    return stats_cycles(db)


@router.get("/api/stats/{classe_id}")
def stats_classe(classe_id: int, origine: bool = True, db: Session = Depends(get_db)):
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise HTTPException(404, "Classe introuvable")
    eleves = classe.eleves_origine if origine else classe.eleves_destination
    if origine:
        eleves = [e for e in eleves if e.classe_destination_id is None]
    return calculer_stats_classe(db, classe, eleves)
