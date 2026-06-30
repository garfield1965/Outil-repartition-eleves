/*
  Logique de la page d'administration : accordéons, CRUD niveaux /
  propriétés / règles, et réinitialisation des données.
*/

// ---------- Accordéons (état mémorisé dans localStorage) ----------

const CLE_ACCORDEON = "admin_accordeons";

function lireEtatsAccordeons() {
  try { return JSON.parse(localStorage.getItem(CLE_ACCORDEON) || "{}"); }
  catch { return {}; }
}

function sauvegarderEtatAccordeon(id, ouvert) {
  const etats = lireEtatsAccordeons();
  etats[id] = ouvert;
  try { localStorage.setItem(CLE_ACCORDEON, JSON.stringify(etats)); }
  catch { /* localStorage indisponible : pas critique */ }
}

function ouvrirAccordeon(corps, entete) {
  // On retire d'abord l'attribut hidden (posé par le serveur pour l'état
  // initial) pour laisser l'animation CSS max-height prendre le dessus.
  corps.removeAttribute("hidden");
  requestAnimationFrame(() => corps.classList.add("ouvert"));
  entete.setAttribute("aria-expanded", "true");
  const icone = entete.querySelector(".accordeon__icone");
  if (icone) icone.textContent = "▾";
}

function fermerAccordeon(corps, entete) {
  corps.classList.remove("ouvert");
  entete.setAttribute("aria-expanded", "false");
  const icone = entete.querySelector(".accordeon__icone");
  if (icone) icone.textContent = "▸";
}

function basculerAccordeon(section) {
  const id = section.dataset.accordeon;
  const entete = section.querySelector(".accordeon__entete");
  const corps = section.querySelector(".accordeon__corps");
  const estOuvert = entete.getAttribute("aria-expanded") === "true";

  if (estOuvert) {
    fermerAccordeon(corps, entete);
  } else {
    ouvrirAccordeon(corps, entete);
  }
  sauvegarderEtatAccordeon(id, !estOuvert);
}

function initialiserAccordeons() {
  const etats = lireEtatsAccordeons();

  document.querySelectorAll(".accordeon").forEach((section) => {
    const id = section.dataset.accordeon;
    const entete = section.querySelector(".accordeon__entete");
    const corps = section.querySelector(".accordeon__corps");

    // L'état localStorage est prioritaire sur l'attribut HTML initial
    // (aria-expanded dans le template), pour que la page retrouve
    // la disposition que l'enseignant avait laissée.
    if (id in etats) {
      if (etats[id]) {
        ouvrirAccordeon(corps, entete);
      } else {
        fermerAccordeon(corps, entete);
        // Corps part avec max-height:0, pas besoin d'animation au chargement
      }
    } else {
      // Pas encore de préférence sauvegardée : on respecte l'état HTML
      if (entete.getAttribute("aria-expanded") === "true") {
        ouvrirAccordeon(corps, entete);
      }
    }

    // Clic sur l'en-tête (pas sur les boutons d'action à l'intérieur)
    entete.addEventListener("click", (evt) => {
      if (evt.target.closest(".accordeon__action")) return;
      basculerAccordeon(section);
    });
  });
}

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

// ---------- Sélecteurs de couleur (partagés niveau + propriété) ----------
// Deux façons de choisir une couleur : une pastille prédéfinie, ou le
// sélecteur natif <input type="color"> pour une couleur sur mesure.
// Les deux restent synchronisés avec le champ caché qui part dans l'API.

document.querySelectorAll(".pastille-couleur").forEach((pastille) => {
  pastille.addEventListener("click", () => {
    const groupe = pastille.closest(".liste-couleurs");
    const pour = groupe.dataset.pour; // "niveau" ou "propriete"
    appliquerCouleurChoisie(pour, pastille.dataset.couleur, pastille);
  });
});

document.querySelectorAll('input[type="color"]').forEach((selecteur) => {
  selecteur.addEventListener("input", () => {
    const pour = selecteur.id.includes("niveau") ? "niveau" : "propriete";
    appliquerCouleurChoisie(pour, selecteur.value, null);
  });
});

function appliquerCouleurChoisie(pour, couleur, pastilleCliquee) {
  document.getElementById(`champ-${pour}-couleur`).value = couleur;

  const groupePastilles = document.querySelector(`.liste-couleurs[data-pour="${pour}"]`);
  groupePastilles.querySelectorAll(".pastille-couleur").forEach((p) => {
    p.classList.toggle("selectionnee", p === pastilleCliquee);
  });

  const selecteurLibre = document.getElementById(`champ-${pour}-couleur-libre`);
  selecteurLibre.value = couleur;
  selecteurLibre.closest(".selecteur-couleur-libre").classList.toggle("selectionnee", !pastilleCliquee);
}

function selectionnerCouleur(pour, couleur) {
  const groupePastilles = document.querySelector(`.liste-couleurs[data-pour="${pour}"]`);
  const pastilleCorrespondante = [...groupePastilles.querySelectorAll(".pastille-couleur")]
    .find((p) => p.dataset.couleur.toLowerCase() === couleur.toLowerCase());
  appliquerCouleurChoisie(pour, couleur, pastilleCorrespondante || null);
}

// ---------- Niveaux ----------

const modaleNiveau = document.getElementById("modale-niveau");
const formNiveau = document.getElementById("form-niveau");

document.getElementById("bouton-creer-niveau").addEventListener("click", () => {
  formNiveau.reset();
  document.getElementById("champ-niveau-id").value = "";
  document.getElementById("champ-niveau-ordre").value = 0;
  document.getElementById("modale-niveau-titre").textContent = "Nouveau niveau";
  const premiere = document.querySelector('.liste-couleurs[data-pour="niveau"] .pastille-couleur');
  document.getElementById("champ-niveau-couleur").value = premiere.dataset.couleur;
  selectionnerCouleur("niveau", premiere.dataset.couleur);
  modaleNiveau.hidden = false;
});

document.getElementById("bouton-annuler-niveau").addEventListener("click", () => { modaleNiveau.hidden = true; });
modaleNiveau.addEventListener("click", (evt) => { if (evt.target === modaleNiveau) modaleNiveau.hidden = true; });

document.querySelectorAll(".bouton-modifier-niveau").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    formNiveau.reset();
    document.getElementById("champ-niveau-id").value = bouton.dataset.id;
    document.getElementById("champ-niveau-libelle").value = bouton.dataset.libelle;
    document.getElementById("champ-niveau-ordre").value = bouton.dataset.ordre;
    document.getElementById("champ-niveau-couleur").value = bouton.dataset.couleur;
    document.getElementById("modale-niveau-titre").textContent = "Modifier le niveau";
    selectionnerCouleur("niveau", bouton.dataset.couleur);
    modaleNiveau.hidden = false;
  });
});

document.querySelectorAll(".bouton-supprimer-niveau").forEach((bouton) => {
  bouton.addEventListener("click", async () => {
    if (!confirm(`Supprimer le niveau "${bouton.dataset.libelle}" ?`)) return;
    try {
      await appelApi(`/api/niveaux/${bouton.dataset.id}`, { method: "DELETE" });
      afficherToast("Niveau supprimé ✓");
      setTimeout(() => location.reload(), 700);
    } catch (e) { /* déjà notifié */ }
  });
});

formNiveau.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const id = document.getElementById("champ-niveau-id").value;
  const payload = {
    libelle: document.getElementById("champ-niveau-libelle").value,
    couleur: document.getElementById("champ-niveau-couleur").value,
    ordre: parseInt(document.getElementById("champ-niveau-ordre").value || "0", 10),
  };
  try {
    if (id) {
      await appelApi(`/api/niveaux/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      afficherToast("Niveau modifié ✓");
    } else {
      await appelApi(`/api/niveaux`, { method: "POST", body: JSON.stringify(payload) });
      afficherToast("Niveau créé 🎉");
    }
    modaleNiveau.hidden = true;
    setTimeout(() => location.reload(), 500);
  } catch (e) { /* déjà notifié */ }
});

// ---------- Propriétés ----------

const modalePropriete = document.getElementById("modale-propriete");
const formPropriete = document.getElementById("form-propriete");

document.getElementById("bouton-creer-propriete").addEventListener("click", () => {
  formPropriete.reset();
  document.getElementById("champ-propriete-id").value = "";
  document.getElementById("modale-propriete-titre").textContent = "Nouvelle propriété";
  const premiere = document.querySelector('.liste-couleurs[data-pour="propriete"] .pastille-couleur');
  document.getElementById("champ-propriete-couleur").value = premiere.dataset.couleur;
  selectionnerCouleur("propriete", premiere.dataset.couleur);
  modalePropriete.hidden = false;
});

document.getElementById("bouton-annuler-propriete").addEventListener("click", () => { modalePropriete.hidden = true; });
modalePropriete.addEventListener("click", (evt) => { if (evt.target === modalePropriete) modalePropriete.hidden = true; });

document.querySelectorAll(".bouton-modifier-propriete").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    formPropriete.reset();
    document.getElementById("champ-propriete-id").value = bouton.dataset.id;
    document.getElementById("champ-propriete-libelle").value = bouton.dataset.libelle;
    document.getElementById("champ-propriete-couleur").value = bouton.dataset.couleur;
    document.getElementById("modale-propriete-titre").textContent = "Modifier la propriété";
    selectionnerCouleur("propriete", bouton.dataset.couleur);
    modalePropriete.hidden = false;
  });
});

document.querySelectorAll(".bouton-supprimer-propriete").forEach((bouton) => {
  bouton.addEventListener("click", async () => {
    if (!confirm(`Supprimer la propriété "${bouton.dataset.libelle}" ? Elle sera retirée des élèves qui l'avaient.`)) return;
    try {
      const resultat = await appelApi(`/api/proprietes/${bouton.dataset.id}`, { method: "DELETE" });
      afficherToast(
        resultat.eleves_concernes > 0
          ? `Propriété supprimée, retirée de ${resultat.eleves_concernes} élève(s)`
          : "Propriété supprimée ✓"
      );
      setTimeout(() => location.reload(), 900);
    } catch (e) { /* déjà notifié */ }
  });
});

formPropriete.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const id = document.getElementById("champ-propriete-id").value;
  const payload = {
    libelle: document.getElementById("champ-propriete-libelle").value,
    couleur: document.getElementById("champ-propriete-couleur").value,
  };
  try {
    if (id) {
      await appelApi(`/api/proprietes/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      afficherToast("Propriété modifiée ✓");
    } else {
      await appelApi(`/api/proprietes`, { method: "POST", body: JSON.stringify(payload) });
      afficherToast("Propriété créée 🎉");
    }
    modalePropriete.hidden = true;
    setTimeout(() => location.reload(), 500);
  } catch (e) { /* déjà notifié */ }
});

// ---------- Règles de gestion ----------

const modaleRegle = document.getElementById("modale-regle");
const formRegle = document.getElementById("form-regle");
const champTypeRegle = document.getElementById("champ-regle-type");
const champProprieteWrapper = document.getElementById("champ-regle-propriete-wrapper");
const champSeuilLibelle = document.getElementById("champ-regle-seuil-libelle");

const LIBELLES_SEUIL = {
  effectif_max: "Seuil maximum (effectif)",
  propriete_max: "Seuil maximum (nombre d'élèves)",
  ecart_sexe_max: "Seuil maximum (% du sexe majoritaire)",
};

function adapterChampsSelonType() {
  const type = champTypeRegle.value;
  champProprieteWrapper.hidden = type !== "propriete_max";
  champSeuilLibelle.textContent = LIBELLES_SEUIL[type] || "Seuil";
}
champTypeRegle.addEventListener("change", adapterChampsSelonType);

document.getElementById("bouton-creer-regle").addEventListener("click", () => {
  formRegle.reset();
  document.getElementById("champ-regle-id").value = "";
  document.getElementById("champ-regle-actif").checked = true;
  document.getElementById("modale-regle-titre").textContent = "Nouvelle règle";
  champTypeRegle.value = "effectif_max";
  adapterChampsSelonType();
  modaleRegle.hidden = false;
});

document.getElementById("bouton-annuler-regle").addEventListener("click", () => { modaleRegle.hidden = true; });
modaleRegle.addEventListener("click", (evt) => { if (evt.target === modaleRegle) modaleRegle.hidden = true; });

document.querySelectorAll(".bouton-modifier-regle").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    formRegle.reset();
    document.getElementById("champ-regle-id").value = bouton.dataset.id;
    document.getElementById("champ-regle-libelle").value = bouton.dataset.libelle;
    champTypeRegle.value = bouton.dataset.typeRegle;
    document.getElementById("champ-regle-seuil").value = bouton.dataset.seuil;
    document.getElementById("champ-regle-actif").checked = bouton.dataset.actif === "true";
    if (bouton.dataset.proprieteId) {
      document.getElementById("champ-regle-propriete").value = bouton.dataset.proprieteId;
    }
    document.getElementById("modale-regle-titre").textContent = "Modifier la règle";
    adapterChampsSelonType();
    modaleRegle.hidden = false;
  });
});

document.querySelectorAll(".bouton-supprimer-regle").forEach((bouton) => {
  bouton.addEventListener("click", async () => {
    if (!confirm(`Supprimer la règle "${bouton.dataset.libelle}" ?`)) return;
    try {
      await appelApi(`/api/regles/${bouton.dataset.id}`, { method: "DELETE" });
      afficherToast("Règle supprimée ✓");
      setTimeout(() => location.reload(), 700);
    } catch (e) { /* déjà notifié */ }
  });
});

formRegle.addEventListener("submit", async (evt) => {
  evt.preventDefault();
  const id = document.getElementById("champ-regle-id").value;
  const type = champTypeRegle.value;
  const payload = {
    libelle: document.getElementById("champ-regle-libelle").value,
    type_regle: type,
    seuil: parseInt(document.getElementById("champ-regle-seuil").value, 10),
    propriete_id: type === "propriete_max"
      ? parseInt(document.getElementById("champ-regle-propriete").value, 10)
      : null,
    actif: document.getElementById("champ-regle-actif").checked,
  };
  try {
    if (id) {
      await appelApi(`/api/regles/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      afficherToast("Règle modifiée ✓");
    } else {
      await appelApi(`/api/regles`, { method: "POST", body: JSON.stringify(payload) });
      afficherToast("Règle créée 🎉");
    }
    modaleRegle.hidden = true;
    setTimeout(() => location.reload(), 500);
  } catch (e) { /* déjà notifié par appelApi */ }
});

// ---------- Réinitialisation ----------

document.getElementById("bouton-reinitialiser").addEventListener("click", async () => {
  const premiereConfirmation = confirm(
    "Cette action supprime définitivement toutes les années, classes, élèves " +
    "et historiques de déplacement. Les niveaux, propriétés et règles de gestion " +
    "seront conservés. Continuer ?"
  );
  if (!premiereConfirmation) return;

  const texteConfirmation = prompt('Pour confirmer, tapez RESET en majuscules :');
  if (texteConfirmation !== "RESET") {
    afficherToast("Réinitialisation annulée");
    return;
  }

  try {
    const resultat = await appelApi("/api/admin/reinitialiser", { method: "POST" });
    afficherToast(
      `Données réinitialisées : ${resultat.classes_supprimees} classe(s) et ` +
      `${resultat.eleves_supprimes} élève(s) supprimés. Niveaux et propriétés conservés.`
    );
    setTimeout(() => { window.location.href = "/"; }, 1800);
  } catch (e) { /* déjà notifié */ }
});

// Initialisation au chargement
initialiserAccordeons();
