"""
Génère un exécutable autonome à partir du fichier repartition_eleves.spec.

Usage depuis la racine du projet, avec le venv ACTIVÉ :
    source .venv/bin/activate          # Windows : .venv\\Scripts\\activate
    python scripts/build_exe.py

Le résultat se trouve dans dist/repartition_eleves(.exe).

Pourquoi passer par un .spec plutôt que des flags CLI ?
    Le .spec définit explicitement pathex=[RACINE], ce qui ajoute la
    racine du projet à sys.path pendant l'analyse PyInstaller. Sans ça,
    sur Windows, le package local `app` n'est pas trouvé et l'exécutable
    plante avec "No module named app.api".
    Le .spec liste aussi tous les sous-modules de `app` en hiddenimports,
    garantissant qu'aucun sous-package n'est silencieusement omis.
"""
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
EXE_DEST = RACINE / "dist" / (
    "repartition_eleves.exe" if sys.platform.startswith("win") else "repartition_eleves"
)


def tuer_exe_si_ouvert() -> None:
    """
    Sur Windows, PyInstaller ne peut pas écraser l'exe s'il tourne encore
    (PermissionError WinError 5). On cherche et termine le processus avant
    de lancer le build.
    """
    if not sys.platform.startswith("win"):
        return
    if not EXE_DEST.exists():
        return

    try:
        # tasklist /FI filtre sur le nom du processus
        resultat = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq repartition_eleves.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True,
        )
        if "repartition_eleves.exe" in resultat.stdout:
            print("⚠  L'exécutable tourne encore — fermeture en cours...")
            subprocess.run(
                ["taskkill", "/F", "/IM", "repartition_eleves.exe"],
                capture_output=True,
            )
            time.sleep(1.5)  # laisse Windows libérer le verrou sur le fichier
            print("   Processus terminé.")
    except FileNotFoundError:
        pass  # tasklist/taskkill indisponibles (rare)


def main():
    spec = RACINE / "repartition_eleves.spec"
    if not spec.exists():
        print(f"ERREUR : {spec} introuvable — il doit être à la racine du projet.")
        sys.exit(1)

    tuer_exe_si_ouvert()

    commande = ["pyinstaller", str(spec), "--clean", "--noconfirm"]
    print("Construction de l'exécutable depuis le .spec...")
    print("Commande :", " ".join(commande))
    subprocess.run(commande, check=True, cwd=RACINE)
    print("\n✓ Exécutable disponible dans dist/repartition_eleves")


if __name__ == "__main__":
    main()