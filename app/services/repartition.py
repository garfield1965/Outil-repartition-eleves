"""
Logique métier du déplacement d'un élève d'une classe vers une autre
(c'est le coeur de l'action de drag & drop).
"""
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.models import Eleve, Classe, HistoriqueAffectation, Propriete


def affecter_eleve(db: Session, eleve_id: int, classe_destination_id: int | None) -> Eleve:
    """
    Place `eleve_id` dans `classe_destination_id` (classe N+1).
    Si classe_destination_id est None, l'élève est retiré de sa classe cible
    (utile pour annuler un déplacement / le remettre "non affecté").
    """
    eleve = db.get(Eleve, eleve_id)
    if eleve is None:
        raise ValueError(f"Élève {eleve_id} introuvable")

    if classe_destination_id is not None:
        classe = db.get(Classe, classe_destination_id)
        if classe is None:
            raise ValueError(f"Classe destination {classe_destination_id} introuvable")

    ancienne_classe_id = eleve.classe_destination_id
    eleve.classe_destination_id = classe_destination_id

    db.add(HistoriqueAffectation(
        eleve_id=eleve.id,
        classe_avant_id=ancienne_classe_id,
        classe_apres_id=classe_destination_id,
        horodatage=datetime.utcnow(),
    ))

    db.commit()
    db.refresh(eleve)
    return eleve


def affecter_plusieurs_eleves(
    db: Session, eleve_ids: list[int], classe_destination_id: int | None
) -> list[Eleve]:
    """
    Déplace plusieurs élèves en une seule fois (sélection multiple côté
    interface). Toutes les affectations sont commises ensemble : soit tout
    réussit, soit rien n'est modifié.
    """
    eleves_deplaces = []
    try:
        for eleve_id in eleve_ids:
            eleve = db.get(Eleve, eleve_id)
            if eleve is None:
                continue
            if classe_destination_id is not None and db.get(Classe, classe_destination_id) is None:
                raise ValueError(f"Classe destination {classe_destination_id} introuvable")

            ancienne_classe_id = eleve.classe_destination_id
            eleve.classe_destination_id = classe_destination_id
            db.add(HistoriqueAffectation(
                eleve_id=eleve.id,
                classe_avant_id=ancienne_classe_id,
                classe_apres_id=classe_destination_id,
                horodatage=datetime.utcnow(),
            ))
            eleves_deplaces.append(eleve)

        db.commit()
    except Exception:
        db.rollback()
        raise

    for eleve in eleves_deplaces:
        db.refresh(eleve)
    return eleves_deplaces


def definir_proprietes_eleve(db: Session, eleve_id: int, propriete_ids: list[int]) -> Eleve:
    """
    Remplace l'ensemble des propriétés (ULIS, TDAH...) d'un élève par celles
    fournies. Permet d'ajouter ET de retirer une propriété en un seul appel :
    le front envoie systématiquement la liste complète des propriétés
    cochées.
    """
    eleve = db.get(Eleve, eleve_id)
    if eleve is None:
        raise ValueError(f"Élève {eleve_id} introuvable")

    if propriete_ids:
        eleve.proprietes = db.query(Propriete).filter(Propriete.id.in_(propriete_ids)).all()
    else:
        eleve.proprietes = []

    db.commit()
    db.refresh(eleve)
    return eleve


def classes_impactees(db: Session, eleve: Eleve, ancienne_classe_id: int | None) -> list[int]:
    """Retourne les ids de classes dont les stats doivent être recalculées côté front."""
    ids = set()
    if ancienne_classe_id:
        ids.add(ancienne_classe_id)
    if eleve.classe_destination_id:
        ids.add(eleve.classe_destination_id)
    return list(ids)
