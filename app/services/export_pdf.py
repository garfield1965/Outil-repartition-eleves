"""
Génération PDF du listing d'une ou plusieurs classes.

Chaque classe produit une page (ou plus si nombreux élèves) avec :
  - Un en-tête coloré (couleur d'accent de la classe)
  - Les statistiques (effectif, niveaux, sexes, propriétés, alertes)
  - La liste des élèves triée par niveau puis par nom, avec devant
    chaque élève des pastilles colorées représentant ses propriétés

Bibliothèque : ReportLab (Platypus pour la mise en page automatique).
"""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

from sqlalchemy.orm import Session

from app.core.models import Classe, Eleve
from app.services.stats import calculer_stats_classe

# Largeur utile A4 avec marges 1.5 cm
LARGEUR = A4[0] - 3 * cm
HAUTEUR = A4[1]


def hex_vers_rgb(hex_str: str) -> tuple[float, float, float]:
    """Convertit '#RRGGBB' en tuple (r, g, b) dans [0, 1]."""
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


def hex_vers_color(hex_str: str) -> colors.Color:
    r, g, b = hex_vers_rgb(hex_str)
    return colors.Color(r, g, b)


def melange_couleur(hex_str: str, ratio_blanc: float = 0.4) -> colors.Color:
    """Mélange une couleur hex avec du blanc pour obtenir un ton pastel."""
    r, g, b = hex_vers_rgb(hex_str)
    return colors.Color(
        r + (1 - r) * ratio_blanc,
        g + (1 - g) * ratio_blanc,
        b + (1 - b) * ratio_blanc,
    )


def _construire_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "classe_titre": ParagraphStyle(
            "ClasseTitre",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#2E2C45"),
        ),
        "classe_sous_titre": ParagraphStyle(
            "ClasseSousTitre",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#6b6884"),
        ),
        "stat_label": ParagraphStyle(
            "StatLabel",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#6b6884"),
        ),
        "stat_valeur": ParagraphStyle(
            "StatValeur",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2E2C45"),
        ),
        "alerte": ParagraphStyle(
            "Alerte",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#b3401f"),
        ),
        "eleve_nom": ParagraphStyle(
            "EleveNom",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2E2C45"),
        ),
        "eleve_detail": ParagraphStyle(
            "EleveDetail",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#6b6884"),
        ),
        "niveau_header": ParagraphStyle(
            "NiveauHeader",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.white,
        ),
    }


def _pastilles_proprietes(proprietes: list, taille: float = 6.0) -> str:
    """
    Génère des pastilles colorées en SVG inline dans un Paragraph ReportLab.
    Utilise des balises <font color="..."> et des caractères ● (U+25CF)
    pour des ronds colorés, séparés par une fine espace.
    """
    if not proprietes:
        return ""
    parties = []
    for p in proprietes:
        couleur = p.couleur if hasattr(p, "couleur") else "#cccccc"
        libelle = p.libelle if hasattr(p, "libelle") else str(p)
        parties.append(
            f'<font color="{couleur}" size="{taille}">&#x25CF;</font>'
            f'<font size="6" color="#888888"> </font>'
        )
    return "".join(parties)


def _bloc_stats(stats: dict, styles: dict, couleur_accent: str) -> Table:
    """Tableau de statistiques compact : niveaux + propriétés + alertes."""
    couleur_fond = melange_couleur(couleur_accent, 0.82)

    lignes_stats = []

    # Ligne niveaux/sexes
    for ligne in stats["par_niveau_sexe"]:
        texte = (
            f"{ligne['niveau']} : "
            f"<b>{ligne['total']}</b> élève{'s' if ligne['total'] > 1 else ''} "
            f"({ligne['filles']}F / {ligne['garcons']}G)"
        )
        lignes_stats.append(Paragraph(texte, styles["stat_valeur"]))

    # Ligne propriétés
    for ligne in stats["par_propriete"]:
        texte = (
            f'<font color="{ligne["couleur"]}">&#x25CF;</font>'
            f" {ligne['propriete']} : <b>{ligne['total']}</b>"
        )
        lignes_stats.append(Paragraph(texte, styles["stat_valeur"]))

    # Alertes de dépassement
    for alerte in stats["alertes"]:
        texte = f"⚠ {alerte['libelle']} — {alerte['message']}"
        lignes_stats.append(Paragraph(texte, styles["alerte"]))

    if not lignes_stats:
        lignes_stats.append(Paragraph("Aucun élève", styles["stat_valeur"]))

    data = [[cell] for cell in lignes_stats]
    t = Table(data, colWidths=[LARGEUR])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), couleur_fond),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def generer_pdf_classes(db: Session, classe_ids: list[int]) -> bytes:
    """
    Génère un PDF multi-pages (une page par classe) et retourne les bytes
    à servir directement comme réponse HTTP.
    """
    styles = _construire_styles()
    buffer = io.BytesIO()

    def _pied_de_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#6b6884"))
        canvas.drawRightString(
            A4[0] - 1.5 * cm, 1 * cm,
            f"Répartition des élèves — export du {date.today().strftime('%d/%m/%Y')} — page {doc.page}"
        )
        canvas.restoreState()

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id="normal",
    )
    template = PageTemplate(id="base", frames=[frame], onPage=_pied_de_page)
    doc.addPageTemplates([template])

    story = []
    premiere_page = True

    for idx, classe_id in enumerate(classe_ids):
        classe = db.get(Classe, classe_id)
        if classe is None:
            continue

        # Récupère les élèves (destination si classe cible, origine sinon)
        annee = classe.annee
        if annee and annee.est_annee_cible:
            eleves = sorted(
                classe.eleves_destination,
                key=lambda e: (e.niveau.ordre if e.niveau else 99, e.nom, e.prenom),
            )
        else:
            eleves = sorted(
                [e for e in classe.eleves_origine if e.classe_destination_id is None],
                key=lambda e: (e.niveau.ordre if e.niveau else 99, e.nom, e.prenom),
            )
            # Inclure tous si c'est une exportation de l'état final
            if not eleves:
                eleves = sorted(
                    classe.eleves_origine,
                    key=lambda e: (e.niveau.ordre if e.niveau else 99, e.nom, e.prenom),
                )

        stats = calculer_stats_classe(db, classe, eleves)
        couleur_accent = classe.couleur or "#A2D2FF"

        if not premiere_page:
            story.append(PageBreak())
        premiere_page = False

        # --- En-tête de classe ---
        couleur_bandeau = melange_couleur(couleur_accent, 0.75)
        couleur_barre = hex_vers_color(couleur_accent)
        niveaux_texte = ", ".join(n.libelle for n in classe.niveaux) or "—"
        effectif_texte = (
            f"{stats['effectif_total']} élève{'s' if stats['effectif_total'] > 1 else ''}"
            + (f" / objectif {stats['effectif_cible']}" if stats['effectif_cible'] else "")
        )

        entete_data = [[
            Paragraph(classe.nom, styles["classe_titre"]),
            Paragraph(
                f"{niveaux_texte}<br/><font color='#6b6884'>{effectif_texte}</font>",
                styles["classe_sous_titre"],
            ),
        ]]
        entete_table = Table(entete_data, colWidths=[LARGEUR * 0.65, LARGEUR * 0.35])
        entete_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), couleur_bandeau),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEABOVE", (0, 0), (-1, 0), 4, couleur_barre),
            ("ROUNDEDCORNERS", [6]),
        ]))
        story.append(entete_table)
        story.append(Spacer(1, 4 * mm))

        # --- Statistiques ---
        story.append(_bloc_stats(stats, styles, couleur_accent))
        story.append(Spacer(1, 6 * mm))

        # --- Liste des élèves groupés par niveau ---
        niveaux_presents = {}
        for eleve in eleves:
            libelle = eleve.niveau.libelle if eleve.niveau else "Non précisé"
            couleur_niv = eleve.niveau.couleur if eleve.niveau else "#A2D2FF"
            niveaux_presents.setdefault(libelle, {"couleur": couleur_niv, "eleves": []})
            niveaux_presents[libelle]["eleves"].append(eleve)

        premiere_section = True
        for libelle_niveau, groupe in niveaux_presents.items():
            # Sous-titre de niveau
            if len(niveaux_presents) > 1:
                couleur_niv_bg = hex_vers_color(groupe["couleur"])
                header_data = [[
                    Paragraph(
                        f'<font color="white">  {libelle_niveau}  '
                        f'({len(groupe["eleves"])} élève{"s" if len(groupe["eleves"]) > 1 else ""})</font>',
                        styles["niveau_header"],
                    )
                ]]
                header_t = Table(header_data, colWidths=[LARGEUR])
                header_t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), couleur_niv_bg),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(header_t)

            # Lignes alternées pour chaque élève
            for i, eleve in enumerate(groupe["eleves"]):
                couleur_fond_ligne = (
                    melange_couleur(groupe["couleur"], 0.92) if i % 2 == 0 else colors.white
                )
                pastilles_html = _pastilles_proprietes(eleve.proprietes)
                sexe_symbole = "♀" if eleve.sexe == "F" else "♂"
                sexe_couleur = "#FF8C6B" if eleve.sexe == "F" else "#6FB7E8"

                ligne_data = [[
                    Paragraph(pastilles_html or "", styles["eleve_nom"]),
                    Paragraph(
                        f'<font color="{sexe_couleur}" size="10">{sexe_symbole}</font>',
                        styles["eleve_nom"],
                    ),
                    Paragraph(
                        f"{eleve.nom.upper()} {eleve.prenom}",
                        styles["eleve_nom"],
                    ),
                    Paragraph(
                        eleve.niveau.libelle if eleve.niveau else "",
                        styles["eleve_detail"],
                    ),
                ]]
                ligne = Table(
                    ligne_data,
                    colWidths=[1.6 * cm, 0.6 * cm, LARGEUR - 3.8 * cm, 1.6 * cm],
                )
                ligne.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), couleur_fond_ligne),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E4DFD3")),
                ]))
                story.append(ligne)

            premiere_section = False

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
