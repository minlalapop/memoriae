import { escapeHtml } from "../api.js";
import { $$ } from "../app.js";

let choice = null;

export function renderAssociatif(trial) {
  choice = null;
  const stimulus = trial.stimulus;
  if (trial.condition === "presentation") return `<div class="image-options">${stimulus.images.map((image) => `<div class="image-choice static-image"><img src="${escapeHtml(image.src)}" alt="${escapeHtml(image.label)}"></div>`).join("")}</div><p id="presentation-timer" class="trial-timer"></p>`;
  return `<div class="image-options">${stimulus.propositions.map((image) => `<button type="button" class="image-choice" data-associative-choice="${image.id}" aria-pressed="false"><img src="${escapeHtml(image.src)}" alt="${escapeHtml(image.label)}"></button>`).join("")}</div>`;
}

export function bindAssociatif(trial) {
  if (trial.condition === "presentation") return;
  $$('[data-associative-choice]').forEach((button) => button.addEventListener("click", () => {
    choice = button.dataset.associativeChoice;
    $$('[data-associative-choice]').forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
  }));
}

export function readAssociatifAnswer() { return { choix:choice }; }
