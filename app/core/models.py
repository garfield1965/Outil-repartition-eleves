"""
Modèle de données.

Le choix clé pour la scalabilité : les "propriétés" d'élève (ULIS, TDAH...)
sont stockées dans une table à part plutôt qu'en colonnes booléennes figées.
On peut ainsi ajouter un nouveau tag pédagogique sans migration de schéma.
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, Table
)
from sqlalchemy.orm import relationship

from app.core.database import Base

# Association classe <-> niveau (une classe peut être à double niveau, ex: CE1-CE2)
classe_niveau = Table(
    "classe_niveau",
    Base.metadata,
    Column("classe_id", ForeignKey("classes.id"), primary_key=True),
    Column("niveau_id", ForeignKey("niveaux.id"), primary_key=True),
)

# Association élève <-> propriété (ULIS, TDAH, "bon niveau"...)
eleve_propriete = Table(
    "eleve_propriete",
    Base.metadata,
    Column("eleve_id", ForeignKey("eleves.id"), primary_key=True),
    Column("propriete_id", ForeignKey("proprietes.id"), primary_key=True),
)


class Annee(Base):
    """Une année scolaire, ex: '2025-2026'."""
    __tablename__ = "annees"

    id = Column(Integer, primary_key=True)
    libelle = Column(String, nullable=False, unique=True)
    est_annee_origine = Column(Boolean, default=False)  # année N (en cours)
    est_annee_cible = Column(Boolean, default=False)    # année N+1 (à construire)

    classes = relationship("Classe", back_populates="annee")


class Cycle(Base):
    """
    Regroupement pédagogique de niveaux.
    Cycle 1 : TPS, PS, MS, GS
    Cycle 2 : CP, CE1, CE2
    Cycle 3 : CM1, CM2
    """
    __tablename__ = "cycles"

    id = Column(Integer, primary_key=True)
    libelle = Column(String, nullable=False, unique=True)  # ex : "Cycle 2"
    description = Column(String, nullable=True)            # ex : "CP, CE1, CE2"
    ordre = Column(Integer, default=0)

    niveaux = relationship("Niveau", back_populates="cycle")


class Niveau(Base):
    """Un niveau scolaire : CP, CE1, CE2, CM1, CM2..."""
    __tablename__ = "niveaux"

    id = Column(Integer, primary_key=True)
    libelle = Column(String, nullable=False, unique=True)
    ordre = Column(Integer, default=0)
    couleur = Column(String, default="#A2D2FF")
    cycle_id = Column(Integer, ForeignKey("cycles.id"), nullable=True)

    cycle = relationship("Cycle", back_populates="niveaux")
    classes = relationship("Classe", secondary=classe_niveau, back_populates="niveaux")
    eleves = relationship("Eleve", back_populates="niveau")


class Classe(Base):
    """Une classe, rattachée à une année (origine N ou cible N+1)."""
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)            # ex: "CE2 Mme Dupont"
    annee_id = Column(Integer, ForeignKey("annees.id"), nullable=False)
    effectif_cible = Column(Integer, nullable=True)  # objectif, optionnel
    couleur = Column(String, default="#A2D2FF")      # couleur d'accent de la carte

    # Position libre sur le tableau (l'enseignant organise les classes comme
    # il le souhaite, par glisser-déposer de la carte elle-même).
    position_x = Column(Integer, default=20)
    position_y = Column(Integer, default=20)
    repliee = Column(Boolean, default=False)  # carte réduite en bandeau

    annee = relationship("Annee", back_populates="classes")
    niveaux = relationship("Niveau", secondary=classe_niveau, back_populates="classes")

    eleves_origine = relationship(
        "Eleve", foreign_keys="Eleve.classe_origine_id", back_populates="classe_origine"
    )
    eleves_destination = relationship(
        "Eleve", foreign_keys="Eleve.classe_destination_id", back_populates="classe_destination"
    )


class Propriete(Base):
    """Tag pédagogique libre : ULIS, TDAH, PAP, 'bon niveau'... extensible."""
    __tablename__ = "proprietes"

    id = Column(Integer, primary_key=True)
    libelle = Column(String, nullable=False, unique=True)
    couleur = Column(String, default="#FFD6A5")
    icone = Column(String, default="star")  # nom d'icône (voir static/js/icons.js)


class Eleve(Base):
    """Un élève, avec sa classe d'origine (N) et sa classe de destination (N+1)."""
    __tablename__ = "eleves"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    sexe = Column(String, nullable=False)  # "F" ou "M"
    date_naissance = Column(String, nullable=True)

    niveau_id = Column(Integer, ForeignKey("niveaux.id"), nullable=False)
    classe_origine_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    classe_destination_id = Column(Integer, ForeignKey("classes.id"), nullable=True)

    niveau = relationship("Niveau", back_populates="eleves")
    classe_origine = relationship(
        "Classe", foreign_keys=[classe_origine_id], back_populates="eleves_origine"
    )
    classe_destination = relationship(
        "Classe", foreign_keys=[classe_destination_id], back_populates="eleves_destination"
    )
    proprietes = relationship("Propriete", secondary=eleve_propriete)


class HistoriqueAffectation(Base):
    """Journal des déplacements, pour pouvoir annuler/auditer une répartition."""
    __tablename__ = "historique_affectations"

    id = Column(Integer, primary_key=True)
    eleve_id = Column(Integer, ForeignKey("eleves.id"), nullable=False)
    classe_avant_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    classe_apres_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    horodatage = Column(DateTime, default=datetime.utcnow)


class RegleGestion(Base):
    """
    Règle de gestion configurable depuis l'administration, évaluée pour
    chaque classe afin d'afficher une alerte en cas de dépassement.

    type_regle :
      - "effectif_max"   : effectif total de la classe > seuil
      - "propriete_max"  : nombre d'élèves ayant `propriete` > seuil
      - "ecart_sexe_max" : % du sexe majoritaire dans la classe > seuil

    Conçu pour rester simple à étendre : ajouter un nouveau type ne demande
    qu'un nouveau bloc dans `services/regles.py`, pas de migration de schéma
    (sauf si le nouveau type a besoin d'un paramètre supplémentaire).
    """
    __tablename__ = "regles_gestion"

    id = Column(Integer, primary_key=True)
    libelle = Column(String, nullable=False)
    type_regle = Column(String, nullable=False)
    seuil = Column(Integer, nullable=False)
    propriete_id = Column(Integer, ForeignKey("proprietes.id"), nullable=True)
    actif = Column(Boolean, default=True)

    propriete = relationship("Propriete")
