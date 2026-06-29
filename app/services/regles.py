"""
Moteur de règles de gestion : permet de définir, depuis l'administration,
des contraintes que l'enseignant souhaite surveiller (effectif maximum,
nombre maximum d'élèves porteurs d'une propriété donnée, équilibre
filles/garçons...), puis de les évaluer automatiquement pour chaque classe
afin d'afficher une alerte visuelle en cas de dépassement.

Ajouter un nouveau type de règle ne demande qu'un nouveau bloc dans
`evaluer_regles` (et, côté interface, une nouvelle option dans le select du
formulaire) — pas de migration de schéma tant que le nouveau type n'a pas
besoin d'un paramètre supplémentaire.
"""
from sqlalchemy.orm import Session

from app.core.models import RegleGestion, Eleve, Propriete

TYPES_REGLE = {
    "effectif_max": "Effectif maximum de la classe",
    "propriete_max": "Nombre maximum pour une propriété",
    "ecart_sexe_max": "Écart filles / garçons maximum (%)",
}


def lister_regles(db: Session) -> list[RegleGestion]:
    return db.query(RegleGestion).order_by(RegleGestion.id).all()


def creer_regle(
    db: Session, libelle: str, type_regle: str, seuil: int,
    propriete_id: int | None, actif: bool,
) -> RegleGestion:
    if type_regle not in TYPES_REGLE:
        raise ValueError(f"Type de règle inconnu : {type_regle}")
    if type_regle == "propriete_max" and propriete_id is None:
        raise ValueError("Une propriété doit être choisie pour ce type de règle")

    regle = RegleGestion(
        libelle=libelle, type_regle=type_regle, seuil=seuil,
        propriete_id=propriete_id if type_regle == "propriete_max" else None,
        actif=actif,
    )
    db.add(regle)
    db.commit()
    db.refresh(regle)
    return regle


def modifier_regle(
    db: Session, regle_id: int, libelle: str | None, type_regle: str | None,
    seuil: int | None, propriete_id: int | None, actif: bool | None,
) -> RegleGestion:
    regle = db.get(RegleGestion, regle_id)
    if regle is None:
        raise LookupError(f"Règle {regle_id} introuvable")

    if type_regle is not None:
        if type_regle not in TYPES_REGLE:
            raise ValueError(f"Type de règle inconnu : {type_regle}")
        regle.type_regle = type_regle
    if libelle is not None:
        regle.libelle = libelle
    if seuil is not None:
        regle.seuil = seuil
    if propriete_id is not None:
        regle.propriete_id = propriete_id
    if actif is not None:
        regle.actif = actif

    if regle.type_regle == "propriete_max" and regle.propriete_id is None:
        raise ValueError("Une propriété doit être choisie pour ce type de règle")
    if regle.type_regle != "propriete_max":
        regle.propriete_id = None

    db.commit()
    db.refresh(regle)
    return regle


def supprimer_regle(db: Session, regle_id: int) -> None:
    regle = db.get(RegleGestion, regle_id)
    if regle is None:
        raise LookupError(f"Règle {regle_id} introuvable")
    db.delete(regle)
    db.commit()


def evaluer_regles(db: Session, eleves: list[Eleve]) -> list[dict]:
    """
    Évalue toutes les règles actives pour la liste d'élèves d'une classe
    donnée, et retourne la liste des règles dépassées (libellé + message
    prêt à afficher). Une classe sans dépassement renvoie une liste vide.
    """
    regles = db.query(RegleGestion).filter_by(actif=True).all()
    if not regles:
        return []

    alertes = []
    total = len(eleves)
    nb_filles = sum(1 for e in eleves if e.sexe == "F")
    nb_garcons = total - nb_filles

    for regle in regles:
        if regle.type_regle == "effectif_max":
            if total > regle.seuil:
                alertes.append({
                    "libelle": regle.libelle,
                    "message": f"Effectif {total}/{regle.seuil}",
                })

        elif regle.type_regle == "propriete_max":
            if regle.propriete_id is None:
                continue
            nb = sum(
                1 for e in eleves
                if any(p.id == regle.propriete_id for p in e.proprietes)
            )
            if nb > regle.seuil:
                libelle_propriete = regle.propriete.libelle if regle.propriete else "?"
                alertes.append({
                    "libelle": regle.libelle,
                    "message": f"{libelle_propriete} {nb}/{regle.seuil}",
                })

        elif regle.type_regle == "ecart_sexe_max":
            if total == 0:
                continue
            pourcentage_majoritaire = max(nb_filles, nb_garcons) / total * 100
            if pourcentage_majoritaire > regle.seuil:
                alertes.append({
                    "libelle": regle.libelle,
                    "message": f"{round(pourcentage_majoritaire)}% > {regle.seuil}%",
                })

    return alertes
