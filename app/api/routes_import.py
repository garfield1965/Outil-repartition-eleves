"""
Route d'upload du fichier Excel ONDE.
"""
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.services.import_onde import importer_fichier_onde

router = APIRouter()


@router.post("/api/import")
async def importer(
    classe_id: int = Form(...),
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not fichier.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Le fichier doit être un export Excel (.xlsx)")

    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin_destination = settings.imports_dir / f"{horodatage}_{fichier.filename}"

    with chemin_destination.open("wb") as f:
        shutil.copyfileobj(fichier.file, f)

    try:
        rapport = importer_fichier_onde(db, chemin_destination, classe_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return {"fichier": fichier.filename, **rapport}
