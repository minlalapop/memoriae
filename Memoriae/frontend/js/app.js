export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

export function message(text = "", error = false) {
  const output = $("#page-message");
  if (!output) return;
  output.textContent = text;
  output.classList.toggle("error", error);
}

function initShell() {
  const path = window.location.pathname;
  const researcher = path.startsWith("/chercheur");
  const navigation = researcher
    ? [["/chercheur", "Expériences"], ["/chercheur/modeles", "Modèles de mémoire"], ["/chercheur/resultats", "Résultats"]]
    : [["/", "Accueil"], ["/participer", "Participer"], ["/connexion", "Espace chercheur"]];
  const shell = $("#app-shell");
  if (!shell) return;
  const activeParticipant = localStorage.getItem("memoriae_active_participant_name");
  shell.innerHTML = `<header><h1>Memoriae</h1></header><nav aria-label="Navigation principale">${navigation.map(([url, label]) => `<a href="${url}" class="${path === url ? "active" : ""}">${label}</a>`).join("")}${researcher ? '<button type="button" class="secondary nav-logout" id="logout">Déconnexion</button>' : ""}</nav>${researcher ? `<div class="active-participant"><strong>Participant actif :</strong> <span id="active-participant-name">${activeParticipant || "Aucun participant sélectionné"}</span></div>` : ""}`;
}

export function updateActiveParticipant(name = "") {
  const output = $("#active-participant-name");
  if (output) output.textContent = name || "Aucun participant sélectionné";
}

export const appReady = new Promise((resolve) => {
  document.addEventListener("DOMContentLoaded", () => { initShell(); resolve(); });
});
