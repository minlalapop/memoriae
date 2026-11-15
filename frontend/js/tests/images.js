import { escapeHtml } from "../api.js";
import { $, $$ } from "../app.js";

let selected = [];

export function renderImages(trial) {
  selected = [];
  const stimulus = trial.stimulus;
  if (trial.condition === "presentation") return `<div class="image-options">${stimulus.images.map((image) => `<div class="image-choice static-image"><img src="${escapeHtml(image.src)}" alt="${escapeHtml(image.label)}"></div>`).join("")}</div>`;
  return `<p id="image-count">0 image sélectionnée sur ${stimulus.nombre_choix}</p><div class="image-options">${stimulus.propositions.map((image) => `<button type="button" class="image-choice" data-image="${image.id}" aria-pressed="false"><img src="${escapeHtml(image.src)}" alt="${escapeHtml(image.label)}"></button>`).join("")}</div>`;
}

export function bindImages(trial) { $$('[data-image]').forEach((button) => button.addEventListener("click", () => { const id = button.dataset.image; if (selected.includes(id)) selected = selected.filter((item) => item !== id); else if (selected.length < trial.stimulus.nombre_choix) selected.push(id); $$('[data-image]').forEach((item) => item.setAttribute("aria-pressed", String(selected.includes(item.dataset.image)))); $("#image-count").textContent = `${selected.length} ${selected.length > 1 ? "images sélectionnées" : "image sélectionnée"} sur ${trial.stimulus.nombre_choix}`; })); }
export function readImagesAnswer() { return { images:selected }; }
