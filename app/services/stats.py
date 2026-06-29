"""
Calcul des effectifs d'une classe : total, par niveau, par sexe, par
propriété, et alertes de dépassement des règles de gestion configurées
dans l'administration. Centralisé ici pour qu'une seule fonction serve à
la fois l'affichage de la classe d'origine et celui de la classe de
destination.
"""
from sqlalchemy.orm import Session

from app.core.models import Classe, Eleve
from app.services.regles import evaluer_regles


def calculer_stats_classe(db: Session, classe: Classe, eleves: list[Eleve]) -> dict:
    """
    `eleves` est la liste déjà filtrée des élèves à compter pour cette classe
    (origine ou destination, c'est l'appelant qui choisit la liste).
    """
    par_niveau: dict[str, dict] = {}
    par_propriete: dict[str, dict] = {}

    for eleve in eleves:
        niveau_libelle = eleve.niveau.libelle if eleve.niveau else "?"
        niveau_couleur = eleve.niveau.couleur if eleve.niveau else "#A2D2FF"
        bucket = par_niveau.setdefault(
            niveau_libelle, {"F": 0, "M": 0, "couleur": niveau_couleur}
        )
        bucket[eleve.sexe] += 1

        for propriete in eleve.proprietes:
            bucket_p = par_propriete.setdefault(
                propriete.libelle, {"total": 0, "couleur": propriete.couleur}
            )
            bucket_p["total"] += 1

    par_niveau_sexe = [
        {
            "niveau": niveau,
            "couleur": valeurs["couleur"],
            "filles": valeurs["F"],
            "garcons": valeurs["M"],
            "total": valeurs["F"] + valeurs["M"],
        }
        for niveau, valeurs in sorted(par_niveau.items())
    ]

    par_propriete_liste = [
        {"propriete": libelle, "couleur": valeurs["couleur"], "total": valeurs["total"]}
        for libelle, valeurs in sorted(par_propriete.items())
    ]

    return {
        "classe_id": classe.id,
        "nom": classe.nom,
        "effectif_total": len(eleves),
        "effectif_cible": classe.effectif_cible,
        "par_niveau_sexe": par_niveau_sexe,
        "par_propriete": par_propriete_liste,
        "alertes": evaluer_regles(db, eleves),
    }
