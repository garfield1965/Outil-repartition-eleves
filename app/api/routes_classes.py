"""
Routes liées aux classes : page principale, fragments de carte de classe.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings, version_assets
from app.core.database import get_db
from app.core.models import Classe, Annee, Niveau, Propriete
from app.services.stats import calculer_stats_classe

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.templates_dir))


def _donnees_classes(db: Session, classes: list[Classe], origine: bool) -> list[dict]:
    """Calcule, pour une liste de classes, les élèves à afficher et les stats."""
    donnees = []
    for classe in classes:
        if origine:
            eleves = [e for e in classe.eleves_origine if e.classe_destination_id is None]
        else:
            eleves = list(classe.eleves_destination)
        donnees.append({
            "classe": classe,
            "eleves": eleves,
            "stats": calculer_stats_classe(db, classe, eleves),
            "origine": origine,
        })
    return donnees


@router.get("/")
def page_accueil(request: Request, db: Session = Depends(get_db)):
    annee_origine = db.query(Annee).filter_by(est_annee_origine=True).first()
    annee_cible = db.query(Annee).filter_by(est_annee_cible=True).first()

    classes_origine = (
        db.query(Classe).filter_by(annee_id=annee_origine.id).all() if annee_origine else []
    )
    classes_cible = (
        db.query(Classe).filter_by(annee_id=annee_cible.id).all() if annee_cible else []
    )

    donnees_origine = _donnees_classes(db, classes_origine, origine=True)
    donnees_cible = _donnees_classes(db, classes_cible, origine=False)
    niveaux = db.query(Niveau).order_by(Niveau.ordre, Niveau.libelle).all()
    proprietes = db.query(Propriete).order_by(Propriete.libelle).all()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "donnees_origine": donnees_origine,
            "donnees_cible": donnees_cible,
            "niveaux": niveaux,
            "proprietes": proprietes,
            "asset_version": version_assets(
                "css/theme.css", "js/app.js", "js/vendor/sortable.complete.esm.js"
            ),
        },
    )


@router.get("/fragments/classe/{classe_id}")
def fragment_classe(
    classe_id: int, origine: bool, request: Request, db: Session = Depends(get_db)
):
    """
    Renvoie le HTML à jour d'UNE carte de classe (élèves + stats).
    `origine=true` -> on affiche les élèves dont la classe d'origine est classe_id
    `origine=false` -> on affiche les élèves dont la classe de destination est classe_id
    Utilisé après chaque drag&drop pour rafraîchir uniquement les cartes concernées.
    """
    classe = db.get(Classe, classe_id)
    donnees = _donnees_classes(db, [classe], origine)[0]

    return templates.TemplateResponse(
        "partials/classe_card.html",
        {
            "request": request,
            "classe": donnees["classe"],
            "eleves": donnees["eleves"],
            "stats": donnees["stats"],
            "origine": origine,
        },
    )


@router.get("/fragments/canvas-cible")
def fragment_canvas_cible(request: Request, db: Session = Depends(get_db)):
    """
    Renvoie le HTML complet du tableau des classes cibles (N+1). Utilisé
    après une création/modification/suppression de classe pour rafraîchir
    tout le canevas sans recharger la page entière.
    """
    annee_cible = db.query(Annee).filter_by(est_annee_cible=True).first()
    classes_cible = (
        db.query(Classe).filter_by(annee_id=annee_cible.id).all() if annee_cible else []
    )
    donnees_cible = _donnees_classes(db, classes_cible, origine=False)

    return templates.TemplateResponse(
        "partials/canvas.html",
        {"request": request, "donnees": donnees_cible},
    )


@router.get("/fragments/canvas-origine")
def fragment_canvas_origine(request: Request, db: Session = Depends(get_db)):
    """Équivalent de fragment_canvas_cible pour les classes d'origine (N)."""
    annee_origine = db.query(Annee).filter_by(est_annee_origine=True).first()
    classes_origine = (
        db.query(Classe).filter_by(annee_id=annee_origine.id).all() if annee_origine else []
    )
    donnees_origine = _donnees_classes(db, classes_origine, origine=True)

    return templates.TemplateResponse(
        "partials/canvas.html",
        {"request": request, "donnees": donnees_origine},
    )
