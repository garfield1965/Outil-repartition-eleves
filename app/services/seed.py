"""
Jeu de données de démo, inséré uniquement si la base est vide.
Permet de tester l'appli (drag&drop, stats...) sans attendre un vrai export ONDE.
"""
from sqlalchemy.orm import Session

from app.core.models import Annee, Niveau, Classe, Eleve, Propriete
from app.core.palette import couleur_pour_index

PRENOMS_F = ["Emma", "Léa", "Chloé", "Manon", "Inès", "Camille", "Jade", "Louise", "Lucie", "Sarah", "Mia", "Lina", "Zoé", "Clara", "Juliette", "Ambre", "Rose", "Anaïs"]
PRENOMS_M = ["Lucas", "Hugo", "Nathan", "Léo", "Gabriel", "Raphaël", "Tom", "Adam","Francis","Thomas","Louis","Arthur","Ethan","Noah","Paul","Maxime","Clément","Mathis","Alexandre"]
NOMS = ["Martin", "Bernard", "Dubois", "Petit", "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David", "Bertrand", "Roux", "Vincent", "Fournier", "Morel", "Girard", "André"]


def seed_si_vide(db: Session) -> None:
    if db.query(Annee).count() > 0:
        return  # déjà initialisé

    annee_n = Annee(libelle="2025-2026", est_annee_origine=True)
    annee_n1 = Annee(libelle="2026-2027", est_annee_cible=True)
    db.add_all([annee_n, annee_n1])
    db.flush()

    niveau_tps = Niveau(libelle="TPS", ordre=1, couleur=couleur_pour_index(0))
    niveau_ps = Niveau(libelle="PS", ordre=2, couleur=couleur_pour_index(1))
    niveau_ms = Niveau(libelle="MS", ordre=3, couleur=couleur_pour_index(2))
    niveau_gs = Niveau(libelle="GS", ordre=4, couleur=couleur_pour_index(3))
    niveau_cp = Niveau(libelle="CP", ordre=5, couleur=couleur_pour_index(4))
    niveau_ce1 = Niveau(libelle="CE1", ordre=6, couleur=couleur_pour_index(5))
    niveau_ce2 = Niveau(libelle="CE2", ordre=7, couleur=couleur_pour_index(6))
    niveau_cm1 = Niveau(libelle="CM1", ordre=8, couleur=couleur_pour_index(7))
    niveau_cm2 = Niveau(libelle="CM2", ordre=9, couleur=couleur_pour_index(8))
    db.add_all([niveau_tps,niveau_ps, niveau_ms, niveau_gs, niveau_cp, niveau_ce1, niveau_ce2, niveau_cm1, niveau_cm2])
    db.flush()

    ulis = Propriete(libelle="ULIS", couleur="#FFB4A2", icone="puzzle")
    tdah = Propriete(libelle="TDAH", couleur="#A2D2FF", icone="bolt")
    tsa = Propriete(libelle="TSA", couleur="#FF6B6B", icone="brain")
    pai = Propriete(libelle="PAI", couleur="#C2A2EE", icone="puzzle")
    pap = Propriete(libelle="PAP", couleur="#E2D2AA", icone="puzzle")
    ime = Propriete(libelle="IME", couleur="#F9C74F", icone="bell")
    bon_niveau = Propriete(libelle="Bon niveau", couleur="#B9FBC0", icone="star")
    en_difficulte = Propriete(libelle="En difficulté", couleur="#F54927", icone="exclamation")
    a_separer = Propriete(libelle="À séparer", couleur="#FFD6A5", icone="split")
    redoublement = Propriete(libelle="Redoublement", couleur="#FCBA03", icone="redoublement")
    db.add_all([ulis, tdah, tsa, pai, pap, ime, bon_niveau, en_difficulte, a_separer, redoublement])
    db.flush()

    # Classe d'origine (année N)
    classe_origine = Classe(
        nom="CE2 M X", annee_id=annee_n.id, couleur="#A2D2FF",
        position_x=20, position_y=20,
    )
    classe_origine.niveaux = [niveau_ce2]
    db.add(classe_origine)
    db.flush()

    classe_origine_2 = Classe(
        nom="CE1/CE2 Mme Z", annee_id=annee_n.id, couleur="#A2D2FF",
        position_x=20, position_y=20,
    )
    classe_origine_2.niveaux = [niveau_ce1,niveau_ce2]
    db.add(classe_origine_2)
    db.flush()
    # Deux classes cibles (année N+1), encore vides
    classe_cible_a = Classe(
        nom="CM1", annee_id=annee_n1.id, effectif_cible=24, couleur="#B9FBC0",
        position_x=20, position_y=20,
    )
    classe_cible_a.niveaux = [niveau_cm1]
    classe_cible_b = Classe(
        nom="CE2", annee_id=annee_n1.id, effectif_cible=24, couleur="#FFD6A5",
        position_x=340, position_y=20,
    )
    classe_cible_b.niveaux = [niveau_ce2]
    classe_cible_c = Classe(
        nom="CM1/CM2", annee_id=annee_n1.id, effectif_cible=24, couleur="#FFD6A5",
        position_x=340, position_y=20,
    )
    classe_cible_c.niveaux = [niveau_cm1, niveau_cm2]
    db.add_all([classe_cible_a, classe_cible_b, classe_cible_c])
    db.flush()

    import random
    random.seed(44)
    proprietes_dispo = [ulis, tdah, tsa,pai, pap, ime, bon_niveau, a_separer, en_difficulte, redoublement]

    for i in range(28):
        sexe = "F" if i % 2 == 0 else "M"
        prenom = random.choice(PRENOMS_F if sexe == "F" else PRENOMS_M)
        nom = random.choice(NOMS)
        eleve = Eleve(
            nom=nom,
            prenom=f"{prenom}",
            sexe=sexe,
            niveau_id=niveau_ce2.id,
            classe_origine_id=classe_origine.id,
        )
        if random.random() < 0.25:
            eleve.proprietes.append(random.choice(proprietes_dispo))
        db.add(eleve)
    for i in range(18):
        sexe = "F" if i % 2 == 0 else "M"
        prenom = random.choice(PRENOMS_F if sexe == "F" else PRENOMS_M)
        nom = random.choice(NOMS)
        eleve = Eleve(
            nom=nom,
            prenom=f"{prenom}",
            sexe=sexe,
            niveau_id=niveau_ce1.id,
            classe_origine_id=classe_origine_2.id,
        )
        if random.random() < 0.35:
            eleve.proprietes.append(random.choice(proprietes_dispo))
        db.add(eleve)
    for i in range(12):
        sexe = "F" if i % 2 == 0 else "M"
        prenom = random.choice(PRENOMS_F if sexe == "F" else PRENOMS_M)
        nom = random.choice(NOMS)
        eleve = Eleve(
            nom=nom,
            prenom=f"{prenom}",
            sexe=sexe,
            niveau_id=niveau_ce2.id,
            classe_origine_id=classe_origine_2.id,
        )
        if random.random() < 0.30:
            eleve.proprietes.append(random.choice(proprietes_dispo))
        db.add(eleve)
    db.commit()
