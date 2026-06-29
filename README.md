# Répartition des élèves

Application web autonome pour répartir les élèves d'une école (plusieurs
classes, plusieurs niveaux) de l'année en cours (N) vers les classes de
l'année prochaine (N+1), par glisser-déposer.

## Démarrage rapide (développement, dans VS Code)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt

python -m app.main
```
Le navigateur s'ouvre automatiquement sur `http://127.0.0.1:8421`.
Au premier lancement, une base SQLite est créée dans `data/app.db` avec un
jeu de données de démonstration (une classe de CE2 à répartir vers deux CM1).

## Fonctionnement

- **Page principale** (`/`) : deux canevas libres, "classes actuelles" à gauche
  et "futures classes" à droite. Chaque élève est une icône (👧/👦) qu'on
  glisse-dépose d'une carte de classe à une autre.
- **Classes déplaçables** : on glisse l'en-tête d'une carte de classe pour la
  repositionner librement sur le tableau (comme un post-it). La position est
  mémorisée en base, donc conservée après rechargement.
- **Repli en bandeau** : le bouton ▾/▸ dans l'en-tête réduit une carte à son
  simple bandeau (nom + effectif), pour libérer de la place visuellement.
- **Sélection multiple** : Ctrl/Cmd + clic sur plusieurs élèves les
  sélectionne (surlignage corail), puis on glisse n'importe lequel des
  élèves sélectionnés pour les déplacer tous ensemble.
- **Couleur de niveau** : chaque niveau (CP, CE1...) a sa propre couleur,
  appliquée au fond de l'avatar de l'élève et à la pastille de statistique
  correspondante, pour repérer visuellement la composition d'une classe.
- Le déplacement met à jour le compteur d'effectif (total, par niveau, par
  sexe, **et par propriété** — ULIS, TDAH... — affiché sous forme de
  pastilles en pointillé sous les statistiques de niveau) en temps réel,
  calculé côté serveur pour garantir l'exactitude.
- Glisser un élève vers une carte d'origine annule son affectation (il
  redevient "non placé").
- **Gestion des classes N+1** : bouton "+ Nouvelle classe" pour créer une
  classe cible (nom, niveaux, effectif cible, couleur) ; icônes ✎ et 🗑 sur
  chaque carte cible pour la modifier ou la supprimer. Supprimer une classe
  qui contient déjà des élèves les remet automatiquement "en attente"
  (aucune perte de données).
- **Import ONDE** : bouton en haut de page → on choisit la classe d'origine
  cible et le fichier Excel exporté d'ONDE. Le mapping des colonnes est
  paramétrable dans `app/services/import_onde.py` (`MAPPING_COLONNES`) si
  les intitulés d'en-tête diffèrent d'un établissement à l'autre.
- **Propriétés d'élève** (ULIS, TDAH, "bon niveau"...) : table libre en base,
  affichées comme petits badges colorés sur l'icône. **Clic simple sur un
  élève** → fiche d'édition pour cocher/décocher ses propriétés. Pour ajouter
  une nouvelle catégorie de propriété, il suffit d'insérer une ligne dans la
  table `proprietes` — aucune modification de code n'est nécessaire.
- **Légende** (bouton 🎨 dans l'en-tête) : panneau récapitulant la couleur de
  chaque niveau et de chaque propriété.
- **Administration** (bouton ⚙️ dans l'en-tête, page `/admin`) :
  - CRUD complet des **niveaux** (libellé, couleur, ordre d'affichage) et des
    **propriétés** (libellé, couleur). Pour la couleur, 8 pastilles
    prédéfinies sont proposées, mais un sélecteur natif **"+ personnalisée"**
    permet aussi de choisir n'importe quelle couleur précise (utile pour
    distinguer beaucoup de niveaux ou de propriétés sans se limiter à la
    palette). Un niveau utilisé par au moins un élève ne peut pas être
    supprimé (message explicite) ; une propriété, elle, peut toujours être
    supprimée — elle est simplement retirée des élèves qui l'avaient.
  - **Réinitialisation des données** : supprime toutes les années, classes,
    élèves et historiques de déplacement, tout en **conservant les niveaux,
    propriétés et règles de gestion déjà définis**. Pratique en début
    d'année pour repartir d'un tableau vide sans tout reconfigurer. Double
    confirmation requise (case de confirmation + saisie du mot "RESET")
    avant l'exécution, action irréversible.
  - **Règles de gestion** : définissez des contraintes que l'enseignant veut
    surveiller — effectif maximum par classe, nombre maximum d'élèves
    porteurs d'une propriété donnée (ex: "pas plus de 2 élèves TSA par
    classe"), écart maximum filles/garçons (en %). Chaque classe qui dépasse
    une règle active affiche automatiquement un badge ⚠️ (visible même carte
    repliée) et un détail du dépassement dans ses statistiques. Une règle
    peut être désactivée sans être supprimée (case "Règle active"). Supprimer
    une propriété supprime aussi les règles qui en dépendent.
- **Classes d'origine (N) créables manuellement** : le bouton "+ Nouvelle
  classe" est maintenant disponible sur les deux colonnes. C'est nécessaire
  après une réinitialisation pour pouvoir importer un nouveau fichier ONDE
  (l'import cible toujours une classe d'origine existante). Une classe
  d'origine contenant encore des élèves ne peut pas être supprimée
  (contrairement à une classe cible, où les élèves sont simplement remis
  en attente).

## Organisation du code

```
app/
├── main.py            # lance le serveur + ouvre le navigateur
├── config.py           # tous les chemins/paramètres centralisés
├── core/                # modèles SQLAlchemy + schémas Pydantic + connexion BD
├── services/            # logique métier pure (import, répartition, stats, seed)
├── api/                 # routeurs FastAPI (un fichier par domaine fonctionnel)
├── static/              # CSS, JS (dont SortableJS vendorisé pour le hors-ligne)
└── templates/            # pages et fragments HTML (Jinja2)
```

Pour ajouter une fonctionnalité (export PDF des classes, algorithme
d'équilibrage automatique, historique multi-années...) :
1. Ajoutez la logique dans un nouveau fichier de `services/`.
2. Exposez-la via un nouveau `routes_xxx.py` dans `api/`.
3. Déclarez le routeur dans `api/app.py` (`app.include_router(...)`).

Aucune autre partie du code n'a besoin d'être modifiée.

## Générer un exécutable autonome (sans Python installé sur le poste)

```bash
pip install pyinstaller
python scripts/build_exe.py
```
Le résultat (`dist/repartition_eleves` ou `.exe` sous Windows) peut être
copié sur n'importe quel poste ou clé USB : double-clic, le serveur démarre
et le navigateur s'ouvre, sans aucune installation préalable. Le fichier
`data/app.db` est créé à côté de l'exécutable, donc les données suivent si
on copie le dossier entier.

## Limites connues / pistes d'évolution

- L'import ONDE suppose que la première ligne du fichier contient les
  en-têtes ; adaptez `MAPPING_COLONNES` si votre export diffère.
- Pas encore d'authentification : pensé pour un usage local, par un seul
  enseignant/directeur à la fois sur la même machine.
- Les polices utilisent une pile de secours système (pas de dépendance
  internet). Pour personnaliser davantage l'identité visuelle, déposez des
  fichiers `.woff2` dans `app/static/fonts/` et référencez-les dans
  `theme.css` via `@font-face`.
- `app.js` est chargé en `<script type="module">` afin de pouvoir importer
  `sortable.complete.esm.js` (la seule build de SortableJS qui embarque et
  monte automatiquement le plugin MultiDrag, nécessaire à la sélection
  multiple d'élèves). Si vous ajoutez du code, gardez à l'esprit que c'est
  un module ES (variables non globales, mode strict).
- Les fichiers CSS/JS sont servis avec un paramètre `?v=...` basé sur l'heure
  de démarrage du serveur, pour éviter qu'un navigateur affiche une version
  mise en cache après une mise à jour. Un simple redémarrage du serveur
  suffit donc à invalider le cache ; pas besoin de vider le cache à la main.
- ⚠️ **Si vous avez une base `data/app.db` issue d'une version précédente**
  du projet (avant l'ajout des positions/repli/couleurs de niveau), elle ne
  contient pas les nouvelles colonnes. Le plus simple est de supprimer
  `data/app.db` pour qu'elle soit recréée à jour au prochain lancement (vous
  perdrez les données de démo, pas un vrai jeu de données ONDE qu'il faudra
  réimporter). Il n'y a pas encore de système de migration (Alembic) ; à
  prévoir si l'application doit un jour gérer des données réelles sur la
  durée.
