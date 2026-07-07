/*
  Logique du tableau de répartition.

  Quatre grandes responsabilités :
  1. Glisser-déposer des élèves (simple ou en sélection multiple via
     le plugin SortableJS MultiDrag) entre les classes.
  2. Glisser-déposer des classes elles-mêmes (repositionnement libre sur
     le canevas), géré "à la main" avec les Pointer Events.
  3. Repli d'une classe en bandeau.
  4. Création / modification / suppression d'une classe N+1 via une modale.

  Ce fichier est chargé en tant que module ES (voir <script type="module">
  dans index.html) afin de pouvoir importer la build "complète" de
  SortableJS : c'est la seule qui inclut et monte automatiquement le
  plugin MultiDrag nécessaire à la sélection multiple d'élèves. Le build
  UMD classique (Sortable.min.js) ne contient pas ce plugin.
*/
import Sortable from "./vendor/sortable.complete.esm.js";

// ---------- Utilitaires ----------

function afficherToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("visible"), 2600);
}

async function appelApi(url, options = {}) {
  const reponse = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!reponse.ok) {
    let detail = "Une erreur est survenue.";
    try { detail = (await reponse.json()).detail || detail; } catch (e) {}
    afficherToast(detail);
    throw new Error(detail);
  }
  return reponse.headers.get("content-type")?.includes("application/json")
    ? reponse.json()
    : reponse.text();
}

// ---------- 1. Déplacement des élèves (simple + sélection multiple) ----------

async function rafraichirCarte(classeId, origine) {
  const html = await appelApi(`/fragments/classe/${classeId}?origine=${origine}`);
  const carteActuelle = document.getElementById(`carte-classe-${classeId}`);
  if (!carteActuelle) return;
  const wrapper = carteActuelle.closest("[data-wrapper-classe]");
  wrapper.innerHTML = html;
  initialiserCarte(wrapper);
}

async function rafraichirToutesLesCartes() {
  const cartes = [...document.querySelectorAll(".carte-classe[data-classe-id]")];
  const requetes = cartes.map((carte) => {
    const zone = carte.querySelector(".zone-depot");
    if (!zone) return Promise.resolve();
    return rafraichirCarte(zone.dataset.classeId, zone.dataset.origine === "true");
  });
  await Promise.all(requetes);
}

function initialiserZoneDepot(zone) {
  if (!zone || zone._sortableInitialise) return;
  zone._sortableInitialise = true;

  Sortable.create(zone, {
    group: "eleves",
    animation: 180,
    ghostClass: "sortable-ghost",
    dragClass: "sortable-drag",

    // Sélection multiple : Ctrl/Cmd + clic sélectionne plusieurs élèves,
    // puis on glisse n'importe lequel des élèves sélectionnés pour les
    // déplacer tous ensemble.
    multiDrag: true,
    selectedClass: "selectionne",
    multiDragKey: "ctrl",

    onEnd: async function (evt) {
      const zoneSource = evt.from;
      const zoneCible = evt.to;
      if (zoneSource === zoneCible) return; // simple réordonnancement visuel, rien à enregistrer

      const elementsDeplaces = (evt.items && evt.items.length > 0) ? evt.items : [evt.item];
      const eleveIds = elementsDeplaces.map((el) => parseInt(el.dataset.eleveId, 10));

      const origineCible = zoneCible.dataset.origine === "true";
      const nouvelleDestination = origineCible ? null : parseInt(zoneCible.dataset.classeId, 10);

      try {
        if (eleveIds.length === 1) {
          await appelApi(`/api/eleves/${eleveIds[0]}/affecter`, {
            method: "PATCH",
            body: JSON.stringify({ classe_destination_id: nouvelleDestination }),
          });
        } else {
          await appelApi(`/api/eleves/affecter-groupe`, {
            method: "PATCH",
            body: JSON.stringify({ eleve_ids: eleveIds, classe_destination_id: nouvelleDestination }),
          });
        }
        afficherToast(
          eleveIds.length === 1
            ? "Élève déplacé ✓"
            : `${eleveIds.length} élèves déplacés ✓`
        );
      } finally {
        // Le DOM a déjà été manipulé par SortableJS ; on resynchronise
        // l'ensemble du tableau avec la base pour des compteurs toujours
        // exacts (et pour ré-appliquer les classes CSS perdues au passage).
        await rafraichirToutesLesCartes();
      }
    },
  });
}

// ---------- 2. Déplacement libre des cartes de classe ----------

function initialiserDeplacementCarte(wrapper) {
  const poignee = wrapper.querySelector(".carte-classe__poignee");
  if (!poignee || poignee._dragInitialise) return;
  poignee._dragInitialise = true;

  let depart = null;

  poignee.addEventListener("pointerdown", (evt) => {
    if (evt.target.closest("button") || evt.target.closest("a")) return; // ne pas interférer avec les boutons et liens d'action
    poignee.setPointerCapture(evt.pointerId);
    depart = {
      x: evt.clientX,
      y: evt.clientY,
      left: wrapper.offsetLeft,
      top: wrapper.offsetTop,
    };
    wrapper.classList.add("en-deplacement", "au-premier-plan");
  });

  poignee.addEventListener("pointermove", (evt) => {
    if (!depart) return;
    const dx = evt.clientX - depart.x;
    const dy = evt.clientY - depart.y;
    wrapper.style.left = Math.max(0, depart.left + dx) + "px";
    wrapper.style.top = Math.max(0, depart.top + dy) + "px";
  });

  async function terminerDeplacement(evt) {
    if (!depart) return;
    wrapper.classList.remove("en-deplacement");
    const classeId = wrapper.dataset.wrapperClasse;
    const x = parseInt(wrapper.style.left, 10) || 0;
    const y = parseInt(wrapper.style.top, 10) || 0;
    depart = null;
    try {
      await appelApi(`/api/classes/${classeId}/position`, {
        method: "PATCH",
        body: JSON.stringify({ position_x: x, position_y: y }),
      });
    } catch (e) { /* déjà notifié par appelApi */ }
  }

  poignee.addEventListener("pointerup", terminerDeplacement);
  poignee.addEventListener("pointercancel", terminerDeplacement);
}

// ---------- 3. Repli d'une classe en bandeau ----------

function initialiserBoutonRepli(carte) {
  const bouton = carte.querySelector(".bouton-repli");
  if (!bouton || bouton._initialise) return;
  bouton._initialise = true;

  bouton.addEventListener("click", async (evt) => {
    evt.stopPropagation();
    const repliee = !carte.classList.contains("carte-classe--repliee");
    carte.classList.toggle("carte-classe--repliee", repliee);
    bouton.textContent = repliee ? "▸" : "▾";
    try {
      await appelApi(`/api/classes/${carte.dataset.classeId}/repli`, {
        method: "PATCH",
        body: JSON.stringify({ repliee }),
      });
    } catch (e) { /* déjà notifié */ }
  });
}

// ---------- 4. Création / modification / suppression de classe ----------

const modaleClasse = document.getElementById("modale-classe");
const formClasse = document.getElementById("form-classe");

function ouvrirModaleCreation(cible) {
  formClasse.reset();
  document.getElementById("champ-classe-id").value = "";
  document.getElementById("champ-cible").value = cible ? "true" : "false";
  document.getElementById("modale-classe-titre").textContent =
    cible ? "Nouvelle classe (année prochaine)" : "Nouvelle classe (année en cours)";
  document.querySelectorAll(".pastille-couleur").forEach((p) => p.classList.remove("selectionnee"));
  const premierePastille = document.querySelector(".pastille-couleur");
  if (premierePastille) {
    premierePastille.classList.add("selectionnee");
    document.getElementById("champ-couleur").value = premierePastille.dataset.couleur;
  }
  modaleClasse.hidden = false;
}

function ouvrirModaleModification(bouton) {
  formClasse.reset();
  document.getElementById("champ-classe-id").value = bouton.dataset.classeId;
  document.getElementById("champ-cible").value = bouton.dataset.cible;
  document.getElementById("champ-nom").value = bouton.dataset.nom;
  document.getElementById("champ-effectif").value = bouton.dataset.effectifCible || "";
  document.getElementById("modale-classe-titre").textContent = "Modifier la classe";

  const niveauIds = (bouton.dataset.niveauIds || "").split(",").filter(Boolean);
  document.querySelectorAll('input[name="niveau_ids"]').forEach((case_) => {
    case_.checked = niveauIds.includes(case_.value);
  });

  document.querySelectorAll(".pastille-couleur").forEach((p) => {
    p.classList.toggle("selectionnee", p.dataset.couleur === bouton.dataset.couleur);
  });
  document.getElementById("champ-couleur").value = bouton.dataset.couleur;

  modaleClasse.hidden = false;
}

function fermerModaleClasse() {
  modaleClasse.hidden = true;
}

function initialiserActionsClasse(carte) {
  const boutonModifier = carte.querySelector(".bouton-modifier-classe");
  if (boutonModifier && !boutonModifier._initialise) {
    boutonModifier._initialise = true;
    boutonModifier.addEventListener("click", (evt) => {
      evt.stopPropagation();
      ouvrirModaleModification(boutonModifier);
    });
  }

  const boutonSupprimer = carte.querySelector(".bouton-supprimer-classe");
  if (boutonSupprimer && !boutonSupprimer._initialise) {
    boutonSupprimer._initialise = true;
    boutonSupprimer.addEventListener("click", async (evt) => {
      evt.stopPropagation();
      const nom = boutonSupprimer.dataset.nom;
      if (!confirm(`Supprimer la classe "${nom}" ?`)) {
        return;
      }
      try {
        const resultat = await appelApi(`/api/classes/${boutonSupprimer.dataset.classeId}`, {
          method: "DELETE",
        });
        afficherToast(
          resultat.eleves_desaffectes > 0
            ? `Classe supprimée, ${resultat.eleves_desaffectes} élève(s) remis en attente`
            : "Classe supprimée"
        );
        setTimeout(() => location.reload(), 900);
      } catch (e) { /* déjà notifié */ }
    });
  }
}

formClasse.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const donnees = new FormData(formClasse);
  const classeId = donnees.get("classe_id");
  const niveauIds = donnees.getAll("niveau_ids").map((v) => parseInt(v, 10));
  const effectifBrut = donnees.get("effectif_cible");

  const payload = {
    nom: donnees.get("nom"),
    niveau_ids: niveauIds,
    effectif_cible: effectifBrut ? parseInt(effectifBrut, 10) : null,
    couleur: donnees.get("couleur"),
    cible: donnees.get("cible") === "true",
  };

  try {
    if (classeId) {
      await appelApi(`/api/classes/${classeId}`, { method: "PATCH", body: JSON.stringify(payload) });
      afficherToast("Classe modifiée ✓");
    } else {
      await appelApi(`/api/classes`, { method: "POST", body: JSON.stringify(payload) });
      afficherToast("Classe créée 🎉");
    }
    fermerModaleClasse();
    setTimeout(() => location.reload(), 600);
  } catch (e) { /* déjà notifié par appelApi */ }
});

document.getElementById("bouton-creer-classe-origine").addEventListener("click", () => ouvrirModaleCreation(false));
document.getElementById("bouton-creer-classe-cible").addEventListener("click", () => ouvrirModaleCreation(true));
document.getElementById("bouton-annuler-classe").addEventListener("click", fermerModaleClasse);
modaleClasse.addEventListener("click", (evt) => { if (evt.target === modaleClasse) fermerModaleClasse(); });

// ---------- Statistiques de l'école ----------

const modaleStatsEcole = document.getElementById("modale-stats-ecole");
const boutonStatsEcole = document.getElementById("bouton-stats-ecole");
const boutonFermerStats = document.getElementById("bouton-fermer-stats");
const contenuStats = document.getElementById("contenu-stats-ecole");

function construireHtmlStats(data) {
  function blocAnnee(stats, annee) {
    if (!stats) {
      return `<div class="stats-bloc">
        <div class="stats-bloc__titre">${annee}</div>
        <p class="stats-vide">Aucune donnée</p>
      </div>`;
    }

    const lignesProprietes = stats.par_propriete
      .filter(p => p.nombre > 0)
      .map(p => `
        <div class="stats-propriete-ligne">
          <span class="pastille-legende" style="background:${p.couleur}"></span>
          <span class="stats-propriete-ligne__libelle">${p.libelle}</span>
          <span class="stats-propriete-ligne__nb">${p.nombre}</span>
          <div class="stats-propriete-barre-fond">
            <div class="stats-propriete-barre" style="width:${p.pourcentage}%; background:${p.couleur}"></div>
          </div>
          <span class="stats-propriete-ligne__pct">${p.pourcentage} %</span>
        </div>`)
      .join("");

    return `<div class="stats-bloc">
      <div class="stats-bloc__titre">${stats.libelle}</div>
      <div class="stats-total">${stats.total} <span>élève${stats.total > 1 ? "s" : ""}</span></div>
      <div class="stats-sexes">
        <div class="stats-sexe-badge stats-sexe-badge--f">
          <span class="stats-sexe-badge__nb">👧 ${stats.filles}</span>
          <span class="stats-sexe-badge__label">${stats.pct_filles} % Filles</span>
        </div>
        <div class="stats-sexe-badge stats-sexe-badge--m">
          <span class="stats-sexe-badge__nb">👦 ${stats.garcons}</span>
          <span class="stats-sexe-badge__label">${stats.pct_garcons} % Garçons</span>
        </div>
      </div>
      <div class="stats-proprietes">
        ${lignesProprietes || '<p class="stats-vide">Aucune propriété assignée</p>'}
      </div>
    </div>`;
  }

  return blocAnnee(data.annee_n, "Année en cours (N)") +
         blocAnnee(data.annee_n1, "Année prochaine (N+1)");
}

boutonStatsEcole.addEventListener("click", async (evt) => {
  evt.stopPropagation();
  contenuStats.innerHTML = '<p class="legende-vide">Chargement…</p>';
  modaleStatsEcole.hidden = false;
  try {
    const data = await appelApi("/api/stats/ecole/global");
    contenuStats.innerHTML = construireHtmlStats(data);
  } catch (e) {
    contenuStats.innerHTML = '<p class="legende-vide">Erreur lors du chargement.</p>';
  }
});

boutonFermerStats.addEventListener("click", () => { modaleStatsEcole.hidden = true; });
modaleStatsEcole.addEventListener("click", (evt) => {
  if (evt.target === modaleStatsEcole) modaleStatsEcole.hidden = true;
});

// ---------- Panneau légende (couleurs niveaux / propriétés) ----------

const panneauLegende = document.getElementById("panneau-legende");
const boutonLegende = document.getElementById("bouton-legende");

boutonLegende.addEventListener("click", (evt) => {
  evt.stopPropagation();
  panneauLegende.hidden = !panneauLegende.hidden;
});

document.addEventListener("click", (evt) => {
  if (!panneauLegende.hidden && !panneauLegende.contains(evt.target) && evt.target !== boutonLegende) {
    panneauLegende.hidden = true;
  }
});

// ---------- Zone d'import ONDE (masquée par défaut) ----------

const zoneImport = document.getElementById("zone-import");
const boutonToggleImport = document.getElementById("bouton-toggle-import");
const boutonFermerImport = document.getElementById("bouton-fermer-import");

boutonToggleImport.addEventListener("click", () => {
  zoneImport.hidden = !zoneImport.hidden;
  if (!zoneImport.hidden) {
    zoneImport.scrollIntoView({ behavior: "smooth", block: "center" });
  }
});

boutonFermerImport.addEventListener("click", () => {
  zoneImport.hidden = true;
});

document.querySelectorAll(".pastille-couleur").forEach((pastille) => {
  pastille.addEventListener("click", () => {
    document.querySelectorAll(".pastille-couleur").forEach((p) => p.classList.remove("selectionnee"));
    pastille.classList.add("selectionnee");
    document.getElementById("champ-couleur").value = pastille.dataset.couleur;
  });
});

// ---------- Fiche élève : ajouter / retirer des propriétés ----------

const modaleEleve = document.getElementById("modale-eleve");
const formEleve = document.getElementById("form-eleve");

async function ouvrirFicheEleve(eleveId) {
  let eleve;
  try {
    eleve = await appelApi(`/api/eleves/${eleveId}`);
  } catch (e) {
    return; // déjà notifié par appelApi
  }

  document.getElementById("champ-eleve-id").value = eleve.id;
  document.getElementById("modale-eleve-titre").textContent = `${eleve.prenom} ${eleve.nom}`;
  document.getElementById("modale-eleve-sous-titre").textContent = eleve.niveau_libelle;

  document.querySelectorAll('#liste-proprietes-eleve input[name="propriete_ids"]').forEach((case_) => {
    case_.checked = eleve.propriete_ids.includes(parseInt(case_.value, 10));
  });

  modaleEleve.hidden = false;
}

function fermerFicheEleve() {
  modaleEleve.hidden = true;
}

formEleve.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const eleveId = document.getElementById("champ-eleve-id").value;
  const proprieteIds = [...document.querySelectorAll('#liste-proprietes-eleve input[name="propriete_ids"]:checked')]
    .map((c) => parseInt(c.value, 10));

  try {
    await appelApi(`/api/eleves/${eleveId}/proprietes`, {
      method: "PATCH",
      body: JSON.stringify({ propriete_ids: proprieteIds }),
    });
    afficherToast("Propriétés mises à jour ✓");
    fermerFicheEleve();
    await rafraichirToutesLesCartes();
  } catch (e) { /* déjà notifié par appelApi */ }
});

document.getElementById("bouton-annuler-eleve").addEventListener("click", fermerFicheEleve);
modaleEleve.addEventListener("click", (evt) => { if (evt.target === modaleEleve) fermerFicheEleve(); });

// Un simple clic (sans Ctrl/Cmd, et pas la fin d'un glisser-déposer) sur un
// élève ouvre sa fiche. Délégué sur le document car les icônes sont
// recréées à chaque rafraîchissement de carte.
document.addEventListener("click", (evt) => {
  const icone = evt.target.closest(".eleve");
  if (!icone) return;
  if (evt.ctrlKey || evt.metaKey) return; // c'est une sélection multiple (SortableJS MultiDrag)
  ouvrirFicheEleve(icone.dataset.eleveId);
});

// ---------- Initialisation générale ----------

function initialiserCarte(wrapperOuCarte) {
  const carte = wrapperOuCarte.matches(".carte-classe")
    ? wrapperOuCarte
    : wrapperOuCarte.querySelector(".carte-classe");
  const wrapper = wrapperOuCarte.matches("[data-wrapper-classe]")
    ? wrapperOuCarte
    : wrapperOuCarte.closest("[data-wrapper-classe]");
  if (!carte) return;

  initialiserZoneDepot(carte.querySelector(".zone-depot"));
  initialiserBoutonRepli(carte);
  initialiserActionsClasse(carte);
  if (wrapper) initialiserDeplacementCarte(wrapper);
}

function initialiserToutLeCanevas(canvas) {
  canvas.querySelectorAll("[data-wrapper-classe]").forEach(initialiserCarte);
}

// ---------- Import du fichier ONDE ----------

function initialiserFormulaireImport() {
  const formulaire = document.getElementById("form-import");
  if (!formulaire) return;

  formulaire.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    const donnees = new FormData(formulaire);
    const rapportEl = document.getElementById("rapport-import");
    rapportEl.textContent = "Import en cours…";

    try {
      const reponse = await fetch("/api/import", { method: "POST", body: donnees });
      const resultat = await reponse.json();

      if (!reponse.ok) {
        rapportEl.textContent = `Erreur : ${resultat.detail || "import impossible"}`;
        return;
      }

      rapportEl.textContent =
        `${resultat.eleves_importes} élève(s) importé(s)` +
        (resultat.eleves_ignores ? `, ${resultat.eleves_ignores} ignoré(s)` : "");
      afficherToast("Import terminé, la page va se rafraîchir 🎉");
      setTimeout(() => location.reload(), 1200);
    } catch (erreur) {
      rapportEl.textContent = "Erreur réseau pendant l'import.";
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".colonne-canvas").forEach(initialiserToutLeCanevas);
  initialiserFormulaireImport();
  initialiserZoneDepart();
});

// ---------- Zone "Quitte l'école" ----------

function initialiserZoneDepart() {
  const zoneDepart = document.getElementById("zone-depart");
  if (!zoneDepart) return;

  // File d'attente des élèves déposés : remplie par le drop,
  // vidée après confirmation ou annulation.
  let elevesEnAttente = [];

  Sortable.create(zoneDepart, {
    group: { name: "eleves", put: true, pull: false },
    animation: 180,
    ghostClass: "sortable-ghost",
    multiDrag: true,
    selectedClass: "selectionne",
    multiDragKey: "ctrl",

    onAdd: async function (evt) {
      const elementsDeplaces = (evt.items && evt.items.length > 0) ? evt.items : [evt.item];

      // On retire immédiatement les icônes déposées de la zone de départ
      // (visuellement elles ne doivent pas y rester — la suppression réelle
      // n'a lieu qu'après confirmation).
      elementsDeplaces.forEach((el) => {
        if (el.parentNode === zoneDepart) {
          zoneDepart.removeChild(el);
        }
      });

      elevesEnAttente = elementsDeplaces.map((el) => ({
        id: parseInt(el.dataset.eleveId, 10),
        nom: el.querySelector(".eleve__nom")?.textContent?.trim() || `Élève ${el.dataset.eleveId}`,
        sexe: el.classList.contains("eleve--fille") ? "F" : "M",
        classeOrigineId: null, // sera récupéré depuis l'API
      }));

      ouvrirModaleDepart(elevesEnAttente);
    },

    onMove: function () {
      zoneDepart.classList.add("survol-actif");
    },
  });

  // Feedback visuel au survol pendant le drag (Sortable ne déclenche pas
  // d'événement natif "dragenter" sur les zones non-SortableJS standard).
  document.addEventListener("sortableUpdate", () => {});
  zoneDepart.addEventListener("dragover", () => zoneDepart.classList.add("survol-actif"));
  zoneDepart.addEventListener("dragleave", () => zoneDepart.classList.remove("survol-actif"));
  zoneDepart.addEventListener("drop", () => zoneDepart.classList.remove("survol-actif"));

  // ---------- Modale de confirmation ----------

  const modaleDepart = document.getElementById("modale-depart");
  const liste = document.getElementById("modale-depart__liste");
  const texte = document.getElementById("modale-depart__texte");

  function ouvrirModaleDepart(eleves) {
    zoneDepart.classList.remove("survol-actif");
    const nb = eleves.length;
    texte.textContent = nb === 1
      ? "L'élève suivant va être définitivement retiré de la base :"
      : `Les ${nb} élèves suivants vont être définitivement retirés de la base :`;

    liste.innerHTML = eleves.map((e) =>
      `<li>${e.sexe === "F" ? "👧" : "👦"} ${e.nom}</li>`
    ).join("");

    modaleDepart.hidden = false;
  }

  function fermerModaleDepart() {
    modaleDepart.hidden = true;
    elevesEnAttente = [];
    // Rafraîchit toutes les cartes pour remettre les icônes à leur place
    // si l'utilisateur avait annulé (elles avaient été retirées du DOM).
    rafraichirToutesLesCartes();
  }

  document.getElementById("bouton-annuler-depart").addEventListener("click", fermerModaleDepart);
  modaleDepart.addEventListener("click", (evt) => {
    if (evt.target === modaleDepart) fermerModaleDepart();
  });

  document.getElementById("bouton-confirmer-depart").addEventListener("click", async () => {
    const ids = elevesEnAttente.map((e) => e.id);
    try {
      const resultat = await appelApi("/api/eleves/quitter-ecole", {
        method: "DELETE",
        body: JSON.stringify({ eleve_ids: ids }),
      });

      modaleDepart.hidden = true;
      elevesEnAttente = [];

      const nb = resultat.supprimes.length;
      afficherToast(`${nb} élève${nb > 1 ? "s" : ""} retiré${nb > 1 ? "s" : ""} de l'école 🚪`);

      // Rafraîchit uniquement les cartes impactées
      for (const { classe_id, origine } of resultat.classes_impactees) {
        await rafraichirCarte(classe_id, origine);
      }
    } catch (e) { /* déjà notifié par appelApi */ }
  });
}
