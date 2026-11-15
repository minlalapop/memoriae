import { escapeHtml } from "../api.js";
import { $$ } from "../app.js";

let choice = null;

function imageCard(image, partial = false) {
  return `<span class="fashion-image${partial ? " fashion-image-partial" : ""}"><img src="${escapeHtml(image.src)}" alt="${escapeHtml(partial ? image.alt : image.label)}"></span>`;
}

export function renderFashion(trial) {
  choice = null;
  if (trial.condition === "presentation") {
    return `<div class="fashion-study">${trial.stimulus.images.map((image) => imageCard(image)).join("")}</div><p class="trial-timer" id="presentation-timer"></p>`;
  }
  return `<div class="fashion-query">${imageCard(trial.stimulus.image_partielle, true)}</div><div class="fashion-options">${trial.stimulus.propositions.map((image) => `<button type="button" class="fashion-choice" data-fashion="${escapeHtml(image.id)}" aria-pressed="false">${imageCard(image)}<span>${escapeHtml(image.label)}</span></button>`).join("")}</div>`;
}

export function bindFashion() {
  $$('[data-fashion]').forEach((button) => button.addEventListener("click", () => {
    choice = button.dataset.fashion;
    $$('[data-fashion]').forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
  }));
}

export function readFashionAnswer() { return { choix:choice }; }
