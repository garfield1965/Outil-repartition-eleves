"""
Génère un exécutable autonome (un seul fichier) à partir de app/main.py.

Usage :
    python scripts/build_exe.py

Le résultat se trouve ensuite dans dist/repartition_eleves(.exe).
L'enseignant n'a qu'à double-cliquer : le serveur démarre et le navigateur
s'ouvre automatiquement, sans rien installer.
"""
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def main():
    separateur = ";" if sys.platform.startswith("win") else ":"
    commande = [
        "pyinstaller",
        "--onefile",
        "--name", "repartition_eleves",
        "--add-data", f"{RACINE / 'app' / 'static'}{separateur}app/static",
        "--add-data", f"{RACINE / 'app' / 'templates'}{separateur}app/templates",
        str(RACINE / "app" / "main.py"),
    ]
    print("Commande exécutée :", " ".join(commande))
    subprocess.run(commande, check=True, cwd=RACINE)


if __name__ == "__main__":
    main()
