"""
Schémas Pydantic : ce que l'API accepte en entrée et renvoie en JSON.
Séparés des modèles SQLAlchemy pour ne jamais exposer la base brute.
"""
from typing import Optional
from pydantic import BaseModel


class ProprieteOut(BaseModel):
    id: int
    libelle: str
    couleur: str
    icone: str

    class Config:
        from_attributes = True


class NiveauOut(BaseModel):
    id: int
    libelle: str
    couleur: str

    class Config:
        from_attributes = True


class EleveOut(BaseModel):
    id: int
    nom: str
    prenom: str
    sexe: str
    niveau_libelle: str
    classe_origine_id: int
    classe_destination_id: Optional[int] = None
    proprietes: list[ProprieteOut] = []

    class Config:
        from_attributes = True


class AffectationIn(BaseModel):
    classe_destination_id: Optional[int] = None  # None = retour en classe d'origine


class AffectationGroupeIn(BaseModel):
    eleve_ids: list[int]
    classe_destination_id: Optional[int] = None


class StatNiveauSexe(BaseModel):
    niveau: str
    couleur: str
    filles: int
    garcons: int
    total: int


class StatPropriete(BaseModel):
    propriete: str
    couleur: str
    total: int


class AlerteRegle(BaseModel):
    libelle: str
    message: str


class ClasseStats(BaseModel):
    classe_id: int
    nom: str
    effectif_total: int
    effectif_cible: Optional[int]
    par_niveau_sexe: list[StatNiveauSexe]
    par_propriete: list[StatPropriete] = []
    alertes: list[AlerteRegle] = []


class ImportRapport(BaseModel):
    fichier: str
    eleves_importes: int
    eleves_ignores: int
    erreurs: list[str]


class ClasseCreateIn(BaseModel):
    nom: str
    niveau_ids: list[int] = []
    effectif_cible: Optional[int] = None
    couleur: str = "#A2D2FF"
    cible: bool = True  # True = classe N+1 (destination), False = classe N (origine)


class ClasseUpdateIn(BaseModel):
    nom: Optional[str] = None
    niveau_ids: Optional[list[int]] = None
    effectif_cible: Optional[int] = None
    couleur: Optional[str] = None


class ClassePositionIn(BaseModel):
    position_x: int
    position_y: int


class ClasseReplieeIn(BaseModel):
    repliee: bool


class EleveDetailOut(BaseModel):
    id: int
    nom: str
    prenom: str
    sexe: str
    niveau_libelle: str
    propriete_ids: list[int] = []


class ProprietesEleveIn(BaseModel):
    propriete_ids: list[int] = []


class NiveauCreateIn(BaseModel):
    libelle: str
    couleur: str = "#A2D2FF"
    ordre: int = 0


class NiveauUpdateIn(BaseModel):
    libelle: Optional[str] = None
    couleur: Optional[str] = None
    ordre: Optional[int] = None


class ProprieteCreateIn(BaseModel):
    libelle: str
    couleur: str = "#A2D2FF"
    icone: str = "star"


class ProprieteUpdateIn(BaseModel):
    libelle: Optional[str] = None
    couleur: Optional[str] = None
    icone: Optional[str] = None


class RegleOut(BaseModel):
    id: int
    libelle: str
    type_regle: str
    seuil: int
    propriete_id: Optional[int] = None
    propriete_libelle: Optional[str] = None
    actif: bool

    class Config:
        from_attributes = True


class RegleCreateIn(BaseModel):
    libelle: str
    type_regle: str  # "effectif_max" | "propriete_max" | "ecart_sexe_max"
    seuil: int
    propriete_id: Optional[int] = None
    actif: bool = True


class RegleUpdateIn(BaseModel):
    libelle: Optional[str] = None
    type_regle: Optional[str] = None
    seuil: Optional[int] = None
    propriete_id: Optional[int] = None
    actif: Optional[bool] = None


class CycleOut(BaseModel):
    id: int
    libelle: str
    description: Optional[str] = None
    ordre: int
    niveaux: list[str] = []

    class Config:
        from_attributes = True


class CycleCreateIn(BaseModel):
    libelle: str
    description: Optional[str] = None
    ordre: int = 0


class CycleUpdateIn(BaseModel):
    libelle: Optional[str] = None
    description: Optional[str] = None
    ordre: Optional[int] = None

