"""
Route d'export PDF des classes.

GET /api/export/classes         → toutes les classes (origine + cible)
GET /api/export/classe/{id}     → une seule classe
GET /api/export/classes?ids=1,2,3 → sélection libre
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import Annee, Classe
from app.services.export_pdf import generer_pdf_classes

router = APIRouter()


@router.get("/api/export/classe/{classe_id}")
def exporter_classe(classe_id: int, db: Session = Depends(get_db)):
    classe = db.get(Classe, classe_id)
    if classe is None:
        raise HTTPException(404, "Classe introuvable")
    pdf_bytes = generer_pdf_classes(db, [classe_id])
    nom_fichier = classe.nom.replace(" ", "_") + ".pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )


@router.get("/api/export/classes")
def exporter_classes(
    ids: str | None = Query(None, description="IDs séparés par virgule"),
    db: Session = Depends(get_db),
):
    """
    Si `ids` est fourni, exporte les classes demandées dans cet ordre.
    Sinon, exporte toutes les classes de l'année cible (N+1) puis N.
    """
    if ids:
        try:
            classe_ids = [int(i.strip()) for i in ids.split(",") if i.strip()]
        except ValueError:
            raise HTTPException(400, "Paramètre ids invalide")
    else:
        annee_cible = db.query(Annee).filter_by(est_annee_cible=True).first()
        annee_origine = db.query(Annee).filter_by(est_annee_origine=True).first()
        classe_ids = []
        if annee_cible:
            classe_ids += [c.id for c in db.query(Classe).filter_by(annee_id=annee_cible.id).all()]
        if annee_origine:
            classe_ids += [c.id for c in db.query(Classe).filter_by(annee_id=annee_origine.id).all()]

    if not classe_ids:
        raise HTTPException(404, "Aucune classe à exporter")

    pdf_bytes = generer_pdf_classes(db, classe_ids)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="listing_classes.pdf"'},
    )
