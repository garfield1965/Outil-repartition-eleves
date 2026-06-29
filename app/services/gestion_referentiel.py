"""
Gestion administrative du "référentiel" partagé (niveaux, propriétés) et
réinitialisation des données de l'année. Séparé de gestion_classes.py car
ce ne sont pas les mêmes objets ni les mêmes règles de suppression.
"""
from sqlalchemy.orm import Session

from app.core.models import (
    Niveau, Propriete, Eleve, Classe, Annee, HistoriqueAffectation,
    classe_niveau, eleve_propriete, RegleGestion,
)


# ---------- Niveaux ----------

def creer_niveau(db: Session, libelle: str, couleur: str, ordre: int) -> Niveau:
    niveau = Niveau(libelle=libelle, couleur=couleur, ordre=ordre)
    db.add(niveau)
    db.commit()
    db.refresh(niveau)
    return niveau


def modifier_niveau(
    db: Session, niveau_id: int, libelle: str | None, couleur: str | None, ordre: int | None
) -> Niveau:
    niveau = db.get(Niveau, niveau_id)
    if niveau is None:
        raise ValueError(f"Niveau {niveau_id} introuvable")
    if libelle is not None:
        niveau.libelle = libelle
    if couleur is not None:
        niveau.couleur = couleur
    if ordre is not None:
        niveau.ordre = ordre
    db.commit()
    db.refresh(niveau)
    return niveau


def supprimer_niveau(db: Session, niveau_id: int) -> None:
    """
    Supprime un niveau. Refusé si des élèves y sont rattachés (le niveau
    d'un élève est une information obligatoire, on ne peut pas la mettre à
    vide) ; dans ce cas l'enseignant doit d'abord réaffecter ces élèves à
    un autre niveau, ou les supprimer.
    """
    niveau = db.get(Niveau, niveau_id)
    if niveau is None:
        raise ValueError(f"Niveau {niveau_id} introuvable")

    nb_eleves = db.query(Eleve).filter_by(niveau_id=niveau_id).count()
    if nb_eleves > 0:
        raise ValueError(
            f"Ce niveau est utilisé par {nb_eleves} élève(s) et ne peut pas être supprimé."
        )

    # Retire le niveau des classes qui le référencent (simple ligne d'association,
    # sans risque de donnée orpheline contrairement aux élèves).
    db.execute(classe_niveau.delete().where(classe_niveau.c.niveau_id == niveau_id))
    db.delete(niveau)
    db.commit()


# ---------- Propriétés ----------

def creer_propriete(db: Session, libelle: str, couleur: str, icone: str) -> Propriete:
    propriete = Propriete(libelle=libelle, couleur=couleur, icone=icone)
    db.add(propriete)
    db.commit()
    db.refresh(propriete)
    return propriete


def modifier_propriete(
    db: Session, propriete_id: int, libelle: str | None, couleur: str | None, icone: str | None
) -> Propriete:
    propriete = db.get(Propriete, propriete_id)
    if propriete is None:
        raise ValueError(f"Propriété {propriete_id} introuvable")
    if libelle is not None:
        propriete.libelle = libelle
    if couleur is not None:
        propriete.couleur = couleur
    if icone is not None:
        propriete.icone = icone
    db.commit()
    db.refresh(propriete)
    return propriete


def supprimer_propriete(db: Session, propriete_id: int) -> dict:
    """
    Supprime une propriété. Contrairement aux niveaux, ce n'est jamais
    bloquant : une propriété est une simple étiquette optionnelle, on retire
    simplement le badge des élèves qui l'avaient. Les règles de gestion qui
    référencent cette propriété (type "propriete_max") sont supprimées avec
    elle, faute de quoi elles n'auraient plus de sens.
    Retourne le nombre d'élèves et de règles concernés (pour informer
    l'enseignant).
    """
    propriete = db.get(Propriete, propriete_id)
    if propriete is None:
        raise ValueError(f"Propriété {propriete_id} introuvable")

    resultat = db.execute(
        eleve_propriete.delete().where(eleve_propriete.c.propriete_id == propriete_id)
    )
    nb_eleves_concernes = resultat.rowcount or 0

    regles_liees = db.query(RegleGestion).filter_by(propriete_id=propriete_id).all()
    nb_regles_concernees = len(regles_liees)
    for regle in regles_liees:
        db.delete(regle)

    db.delete(propriete)
    db.commit()
    return {"eleves": nb_eleves_concernes, "regles": nb_regles_concernees}


# ---------- Réinitialisation ----------

def reinitialiser_donnees(db: Session) -> dict:
    """
    Repart d'une page blanche pour les classes/élèves/années, EN CONSERVANT
    les niveaux et propriétés actuellement définis (c'est tout l'intérêt :
    l'enseignant ne re-paramètre pas son référentiel à chaque rentrée).
    Recrée ensuite deux années vides (origine / cible) pour que
    l'application reste immédiatement utilisable (création de classes,
    import ONDE...).
    """
    nb_eleves = db.query(Eleve).count()
    nb_classes = db.query(Classe).count()

    db.query(HistoriqueAffectation).delete()
    db.execute(eleve_propriete.delete())
    db.query(Eleve).delete()
    db.execute(classe_niveau.delete())
    db.query(Classe).delete()
    db.query(Annee).delete()

    annee_n = Annee(libelle="Année en cours", est_annee_origine=True)
    annee_n1 = Annee(libelle="Année suivante", est_annee_cible=True)
    db.add_all([annee_n, annee_n1])

    db.commit()

    return {"eleves_supprimes": nb_eleves, "classes_supprimees": nb_classes}
