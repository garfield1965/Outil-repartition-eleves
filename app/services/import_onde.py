"""
Import d'un fichier Excel exporté depuis ONDE (logiciel de l'Éducation Nationale).

Les exports ONDE varient selon les écoles/versions : on normalise les en-têtes
(minuscules, sans accents) et on passe par un dictionnaire de correspondance
MAPPING_COLONNES, modifiable ici en un seul endroit si un établissement a des
intitulés différents (ex: "Né(e) le" vs "Date de naissance").
"""
import unicodedata
from pathlib import Path

import openpyxl
from sqlalchemy.orm import Session

from app.core.models import Eleve, Niveau, Classe
from app.core.palette import couleur_pour_index

# Clé interne -> liste de libellés d'en-tête possibles (déjà normalisés en interne)
MAPPING_COLONNES = {
    "nom": ["nom", "nom de famille", "nom usage"],
    "prenom": ["prenom", "prénom", "premier prenom"],
    "sexe": ["sexe", "sexe (m/f)", "genre"],
    "date_naissance": ["date de naissance", "ne(e) le", "né(e) le", "date naissance"],
    "niveau": ["niveau", "classe niveau", "code niveau", "division"],
    "statut": ["statut", "statut élève", "statut de l'élève"],
}


def _normaliser(texte: str) -> str:
    """minuscule + suppression accents, pour comparer les en-têtes sans ambiguïté."""
    if texte is None:
        return ""
    texte = str(texte).strip().lower()
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return texte


def _detecter_colonnes(en_tetes: list[str]) -> dict[str, int]:
    """Retourne {cle_interne: index_colonne} en cherchant parmi les libellés connus."""
    en_tetes_norm = [_normaliser(h) for h in en_tetes]
    resultat = {}
    for cle, libelles_possibles in MAPPING_COLONNES.items():
        for libelle in libelles_possibles:
            if libelle in en_tetes_norm:
                resultat[cle] = en_tetes_norm.index(libelle)
                break
    return resultat


def importer_fichier_onde(
    db: Session,
    chemin_fichier: Path,
    classe_id: int,
) -> dict:
    """
    Lit le fichier Excel ONDE et crée les élèves dans `classe_id` (classe d'origine N).
    Crée automatiquement les Niveau manquants.
    Retourne un rapport : {eleves_importes, eleves_ignores, erreurs}.
    """
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise ValueError(f"Classe {classe_id} introuvable")

    classeur = openpyxl.load_workbook(chemin_fichier, data_only=True)
    feuille = classeur.active

    lignes = list(feuille.iter_rows(values_only=True))
    if not lignes:
        return {"eleves_importes": 0, "eleves_ignores": 0, "erreurs": ["Fichier vide"]}

    en_tetes = [str(c) if c is not None else "" for c in lignes[0]]
    colonnes = _detecter_colonnes(en_tetes)

    erreurs: list[str] = []
    manquantes = [c for c in ("nom", "prenom", "sexe") if c not in colonnes]
    if manquantes:
        erreurs.append(
            f"Colonnes obligatoires non trouvées dans l'en-tête : {manquantes}. "
            f"En-têtes lues : {en_tetes}"
        )
        return {"eleves_importes": 0, "eleves_ignores": 0, "erreurs": erreurs}

    eleves_importes = 0
    eleves_ignores = 0

    for num_ligne, ligne in enumerate(lignes[1:], start=2):
        try:
            nom = ligne[colonnes["nom"]]
            prenom = ligne[colonnes["prenom"]]
            sexe_brut = ligne[colonnes["sexe"]]

            if not nom or not prenom:
                eleves_ignores += 1
                continue

            sexe = "F" if _normaliser(sexe_brut).startswith("f") else "M"

            date_naissance = None
            if "date_naissance" in colonnes:
                val = ligne[colonnes["date_naissance"]]
                date_naissance = str(val) if val else None

            libelle_niveau = "Non précisé"
            if "niveau" in colonnes and ligne[colonnes["niveau"]]:
                libelle_niveau = str(ligne[colonnes["niveau"]]).strip()

            niveau = db.query(Niveau).filter_by(libelle=libelle_niveau).first()
            if niveau is None:
                nb_niveaux_existants = db.query(Niveau).count()
                niveau = Niveau(
                    libelle=libelle_niveau,
                    ordre=99,
                    couleur=couleur_pour_index(nb_niveaux_existants),
                )
                db.add(niveau)
                db.flush()

            eleve = Eleve(
                nom=str(nom).strip(),
                prenom=str(prenom).strip(),
                sexe=sexe,
                date_naissance=date_naissance,
                niveau_id=niveau.id,
                classe_origine_id=classe.id,
            )
            db.add(eleve)
            eleves_importes += 1

        except Exception as exc:  # on isole l'erreur ligne par ligne, on continue l'import
            erreurs.append(f"Ligne {num_ligne} ignorée : {exc}")
            eleves_ignores += 1

    db.commit()
    return {
        "eleves_importes": eleves_importes,
        "eleves_ignores": eleves_ignores,
        "erreurs": erreurs,
    }
