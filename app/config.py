"""
Configuration centrale de l'application.
Toute valeur "en dur" (chemins, port...) doit passer par ici,
jamais éparpillée dans le code.
"""
import sys
from pathlib import Path
from pydantic_settings import BaseSettings

if getattr(sys, "frozen", False):
    # Exécutable PyInstaller : les fichiers statiques/templates sont extraits
    # dans un dossier temporaire (sys._MEIPASS), mais les DONNÉES (base SQLite,
    # imports) doivent rester à côté de l'exécutable pour ne pas être perdues
    # à la fermeture de l'application.
    RESSOURCES_DIR = Path(sys._MEIPASS)
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    RESSOURCES_DIR = Path(__file__).resolve().parent.parent
    BASE_DIR = RESSOURCES_DIR


class Settings(BaseSettings):
    app_name: str = "Répartition des élèves"
    host: str = "127.0.0.1"
    port: int = 8421

    data_dir: Path = BASE_DIR / "data"
    db_path: Path = BASE_DIR / "data" / "app.db"
    imports_dir: Path = BASE_DIR / "data" / "imports"

    static_dir: Path = RESSOURCES_DIR / "app" / "static"
    templates_dir: Path = RESSOURCES_DIR / "app" / "templates"

    class Config:
        env_prefix = "REPARTITION_"


settings = Settings()


def version_assets(*chemins_relatifs: str) -> str:
    """
    Calcule une version de cache basée sur la date de dernière modification
    des fichiers passés (chemins relatifs à `static_dir`), pas sur l'heure de
    démarrage du serveur. Ainsi, même sans redémarrer le serveur après avoir
    remplacé un fichier (app.js, theme.css...), le navigateur détecte le
    changement et recharge la bonne version — on ne dépend plus de la
    discipline de l'utilisateur à relancer le process.
    """
    derniere_modif = 0.0
    for relatif in chemins_relatifs:
        chemin = settings.static_dir / relatif
        try:
            derniere_modif = max(derniere_modif, chemin.stat().st_mtime)
        except FileNotFoundError:
            continue
    return str(int(derniere_modif))


# S'assure que les dossiers de données existent (utile au premier lancement,
# notamment depuis l'exécutable PyInstaller).
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.imports_dir.mkdir(parents=True, exist_ok=True)
