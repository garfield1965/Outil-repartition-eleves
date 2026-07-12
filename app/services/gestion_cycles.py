"""
Gestion des cycles pédagogiques et calcul des statistiques par cycle.

Un cycle regroupe plusieurs niveaux :
  Cycle 1 : TPS, PS, MS, GS
  Cycle 2 : CP, CE1, CE2
  Cycle 3 : CM1, CM2

Les statistiques calculées :
  - Effectif par cycle (N et N+1)
  - Élèves qui changent de cycle (ex : GS → CP = transition cycle 1 → 2)
  - Matrice de flux : combien d'élèves vont de chaque cycle vers chaque cycle
"""
from sqlalchemy.orm import Session

from app.core.models import Cycle, Niveau, Eleve, Annee, Classe


# ---------- CRUD ----------

def lister_cycles(db: Session) -> list[Cycle]:
    return db.query(Cycle).order_by(Cycle.ordre, Cycle.libelle).all()


def creer_cycle(
    db: Session, libelle: str, description: str | None, ordre: int
) -> Cycle:
    cycle = Cycle(libelle=libelle, description=description, ordre=ordre)
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle


def modifier_cycle(
    db: Session, cycle_id: int,
    libelle: str | None, description: str | None, ordre: int | None,
) -> Cycle:
    cycle = db.get(Cycle, cycle_id)
    if cycle is None:
        raise LookupError(f"Cycle {cycle_id} introuvable")
    if libelle is not None:
        cycle.libelle = libelle
    if description is not None:
        cycle.description = description
    if ordre is not None:
        cycle.ordre = ordre
    db.commit()
    db.refresh(cycle)
    return cycle


def supprimer_cycle(db: Session, cycle_id: int) -> int:
    """
    Supprime un cycle. Les niveaux qui y étaient rattachés sont
    délié (cycle_id = None) mais pas supprimés.
    Retourne le nombre de niveaux délié.
    """
    cycle = db.get(Cycle, cycle_id)
    if cycle is None:
        raise LookupError(f"Cycle {cycle_id} introuvable")
    nb_niveaux = len(cycle.niveaux)
    for niveau in cycle.niveaux:
        niveau.cycle_id = None
    db.delete(cycle)
    db.commit()
    return nb_niveaux


def affecter_niveau_a_cycle(
    db: Session, niveau_id: int, cycle_id: int | None
) -> Niveau:
    """Rattache (ou détache si cycle_id=None) un niveau à un cycle."""
    niveau = db.get(Niveau, niveau_id)
    if niveau is None:
        raise LookupError(f"Niveau {niveau_id} introuvable")
    if cycle_id is not None and db.get(Cycle, cycle_id) is None:
        raise LookupError(f"Cycle {cycle_id} introuvable")
    niveau.cycle_id = cycle_id
    db.commit()
    db.refresh(niveau)
    return niveau


# ---------- Statistiques ----------

def _cycle_du_niveau(niveau: Niveau | None) -> Cycle | None:
    if niveau is None:
        return None
    return niveau.cycle


def stats_cycles(db: Session) -> dict:
    """
    Calcule les statistiques par cycle pour l'année N et N+1.

    Retourne :
      - effectifs par cycle (N et N+1)
      - élèves qui changent de cycle (avec détail par transition)
      - élèves sans cycle défini (niveaux non rattachés)
    """
    annee_n = db.query(Annee).filter_by(est_annee_origine=True).first()
    annee_n1 = db.query(Annee).filter_by(est_annee_cible=True).first()
    tous_cycles = db.query(Cycle).order_by(Cycle.ordre).all()

    if not tous_cycles:
        return {"erreur": "Aucun cycle défini. Configurez les cycles dans l'administration."}

    def effectifs_par_cycle(eleves: list[Eleve]) -> dict:
        """
        Retourne {cycle_id: {"libelle": ..., "ordre": ..., "nb": ..., "filles": ..., "garcons": ...}}
        Plus une entrée None pour les élèves sans cycle.
        """
        buckets = {c.id: {"libelle": c.libelle, "ordre": c.ordre, "nb": 0, "filles": 0, "garcons": 0}
                   for c in tous_cycles}
        buckets[None] = {"libelle": "Sans cycle", "ordre": 99, "nb": 0, "filles": 0, "garcons": 0}
        for e in eleves:
            cle = e.niveau.cycle_id if e.niveau else None
            if cle not in buckets:
                cle = None
            buckets[cle]["nb"] += 1
            if e.sexe == "F":
                buckets[cle]["filles"] += 1
            else:
                buckets[cle]["garcons"] += 1
        return buckets

    # Élèves N
    classes_n = db.query(Classe).filter_by(annee_id=annee_n.id).all() if annee_n else []
    ids_classes_n = [c.id for c in classes_n]
    eleves_n = db.query(Eleve).filter(
        Eleve.classe_origine_id.in_(ids_classes_n)
    ).all() if ids_classes_n else []

    # Élèves N+1
    classes_n1 = db.query(Classe).filter_by(annee_id=annee_n1.id).all() if annee_n1 else []
    ids_classes_n1 = [c.id for c in classes_n1]
    eleves_n1 = db.query(Eleve).filter(
        Eleve.classe_destination_id.in_(ids_classes_n1)
    ).all() if ids_classes_n1 else []

    effectifs_n = effectifs_par_cycle(eleves_n)
    effectifs_n1 = effectifs_par_cycle(eleves_n1)

    # Transitions de cycle : pour chaque élève placé en N+1, on compare son
    # cycle actuel (via son niveau) au cycle de sa classe de destination
    # (via les niveaux de cette classe).
    transitions: dict[tuple, int] = {}  # (cycle_src_id, cycle_dst_id) → nb élèves
    eleves_changement_cycle = []

    for eleve in eleves_n:
        if eleve.classe_destination_id is None:
            continue
        cycle_src = _cycle_du_niveau(eleve.niveau)
        # Détermine le cycle de destination via les niveaux de la classe cible
        classe_dst = db.get(Classe, eleve.classe_destination_id)
        if not classe_dst or not classe_dst.niveaux:
            continue
        # On prend le cycle du premier niveau de la classe (une classe peut
        # être multi-niveaux, mais ils sont généralement dans le même cycle)
        cycle_dst = _cycle_du_niveau(classe_dst.niveaux[0])

        cle_src = cycle_src.id if cycle_src else None
        cle_dst = cycle_dst.id if cycle_dst else None
        cle = (cle_src, cle_dst)
        transitions[cle] = transitions.get(cle, 0) + 1

        if cle_src != cle_dst:
            eleves_changement_cycle.append({
                "nom": f"{eleve.prenom} {eleve.nom}",
                "sexe": eleve.sexe,
                "niveau": eleve.niveau.libelle if eleve.niveau else "?",
                "cycle_src": cycle_src.libelle if cycle_src else "Sans cycle",
                "cycle_dst": cycle_dst.libelle if cycle_dst else "Sans cycle",
            })

    # Formate les transitions pour la réponse
    def label_cycle(cycle_id):
        if cycle_id is None:
            return "Sans cycle"
        c = db.get(Cycle, cycle_id)
        return c.libelle if c else "?"

    transitions_liste = [
        {
            "cycle_src": label_cycle(src),
            "cycle_dst": label_cycle(dst),
            "nb": nb,
            "changement": src != dst,
        }
        for (src, dst), nb in sorted(transitions.items())
    ]

    return {
        "annee_n": annee_n.libelle if annee_n else "—",
        "annee_n1": annee_n1.libelle if annee_n1 else "—",
        "cycles": [
            {"id": c.id, "libelle": c.libelle, "ordre": c.ordre,
             "niveaux": [n.libelle for n in c.niveaux]}
            for c in tous_cycles
        ],
        "effectifs_n": [
            {"cycle_id": cid, **vals}
            for cid, vals in sorted(effectifs_n.items(), key=lambda x: x[1]["ordre"])
            if vals["nb"] > 0
        ],
        "effectifs_n1": [
            {"cycle_id": cid, **vals}
            for cid, vals in sorted(effectifs_n1.items(), key=lambda x: x[1]["ordre"])
            if vals["nb"] > 0
        ],
        "transitions": transitions_liste,
        "nb_changements_cycle": len(eleves_changement_cycle),
        "eleves_changement_cycle": eleves_changement_cycle,
    }
