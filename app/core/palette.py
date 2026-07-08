"""
Palette de couleurs utilisée pour attribuer automatiquement une couleur à
chaque niveau (CP, CE1...) au moment de sa création — que ce soit via le
jeu de données de démo ou via l'import d'un fichier ONDE.

Centralisé ici pour qu'un seul endroit définisse "à quoi ressemble"
l'application (cohérent avec le reste de la charte dans theme.css).
"""

PALETTE_NIVEAUX = [
    "#FF8C6B",  # corail
    "#6FB7E8",  # ciel
    "#6FCF97",  # menthe
    "#FFD27D",  # pêche
    "#B79CED",  # lavande
    "#F4D35E",  # citron
    "#7ED6C1",  # turquoise
    "#F49AC2",  # rose
    "#FF7D00",  # orange
    "#00FF00",  # vert
]
PALETTE_PROPRIETES   = [
    "#FFA500",  # orange
    "#00FF00",  # vert
    "#FF0000",  # rouge
    "#0000FF",  # bleu
    "#800080",  # violet
    "#FFC0CB",  # rose
    "#FFFF00",  # jaune
    "#00FFFF",  # cyan
    "#166866",  # bleu foncé
    "#FF00FF",  # magenta
]


def couleur_pour_index(index: int, palette: list[str]= PALETTE_NIVEAUX) -> str:
    """
    Retourne la couleur correspondant à l'index dans la palette.
    Si l'index dépasse la taille de la palette, les couleurs sont réutilisées
    de manière circulaire.
    """
    return palette[index % len(palette)]
