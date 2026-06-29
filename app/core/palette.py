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
]


def couleur_pour_index(index: int) -> str:
    return PALETTE_NIVEAUX[index % len(PALETTE_NIVEAUX)]
