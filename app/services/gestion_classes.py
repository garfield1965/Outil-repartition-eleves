"""
Gestion administrative des classes (essentiellement les classes cibles N+1) :
création, modification, suppression, déplacement libre sur le tableau et
repli en bandeau. Logique isolée des routes pour rester testable simplement.
"""
from sqlalchemy.orm import Session

from app.core.models import Classe, Niveau


def creer_classe(
    db: Session, annee_id: int, nom: str, niveau_ids: list[int],
    effectif_cible: int | None, couleur: str,
) -> Classe:
    # Empile la nouvelle carte un peu plus bas que les précédentes pour
    # qu'elle n'arrive pas exactement superposée aux autres.
    nb_classes_annee = db.query(Classe).filter_by(annee_id=annee_id).count()
    classe = Classe(
        nom=nom,
        annee_id=annee_id,
        effectif_cible=effectif_cible,
        couleur=couleur,
        position_x=20 + (nb_classes_annee % 3) * 320,
        position_y=20 + (nb_classes_annee // 3) * 260,
    )
    if niveau_ids:
        classe.niveaux = db.query(Niveau).filter(Niveau.id.in_(niveau_ids)).all()

    db.add(classe)
    db.commit()
    db.refresh(classe)
    return classe


def modifier_classe(
    db: Session, classe_id: int, nom: str | None, niveau_ids: list[int] | None,
    effectif_cible: int | None, couleur: str | None,
) -> Classe:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise ValueError(f"Classe {classe_id} introuvable")

    if nom is not None:
        classe.nom = nom
    if couleur is not None:
        classe.couleur = couleur
    if effectif_cible is not None:
        classe.effectif_cible = effectif_cible
    if niveau_ids is not None:
        classe.niveaux = db.query(Niveau).filter(Niveau.id.in_(niveau_ids)).all()

    db.commit()
    db.refresh(classe)
    return classe


def supprimer_classe(db: Session, classe_id: int) -> int:
    """
    Supprime une classe (origine ou cible).
    - Si c'est une classe d'origine contenant encore des élèves, la
      suppression est refusée : le niveau/la classe d'origine d'un élève
      est une donnée obligatoire, on ne peut pas l'orpheliner.
    - Si c'est une classe cible, les élèves qui y étaient affectés sont
      simplement remis en attente (classe_destination_id = None).
    Retourne le nombre d'élèves remis en attente (classe cible uniquement).
    """
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise LookupError(f"Classe {classe_id} introuvable")

    if classe.eleves_origine:
        raise ValueError(
            f"Cette classe contient encore {len(classe.eleves_origine)} élève(s) "
            "en tant que classe d'origine et ne peut pas être supprimée."
        )

    nb_eleves_desaffectes = len(classe.eleves_destination)
    for eleve in list(classe.eleves_destination):
        eleve.classe_destination_id = None

    db.delete(classe)
    db.commit()
    return nb_eleves_desaffectes


def deplacer_classe(db: Session, classe_id: int, position_x: int, position_y: int) -> Classe:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise ValueError(f"Classe {classe_id} introuvable")
    classe.position_x = position_x
    classe.position_y = position_y
    db.commit()
    return classe


def basculer_repli(db: Session, classe_id: int, repliee: bool) -> Classe:
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise ValueError(f"Classe {classe_id} introuvable")
    classe.repliee = repliee
    db.commit()
    return classe
