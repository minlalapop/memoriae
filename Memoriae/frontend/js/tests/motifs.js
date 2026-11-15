import { escapeHtml } from "../api.js";
import { $$ } from "../app.js";

let choice = null;

function matrixHtml(matrix) { return `<div class="matrix-board symbol-matrix grid-columns-${matrix[0].length}" role="grid">${matrix.flat().map((symbol) => `<span class="matrix-cell symbol-cell">${symbol ? escapeHtml(symbol) : "&nbsp;"}</span>`).join("")}</div>`; }

export function renderMotifs(trial) {
  choice = null;
  if (trial.condition === "presentation") return matrixHtml(trial.stimulus.matrice);
  return `<div class="pattern-options">${trial.stimulus.propositions.map((matrix, index) => `<button type="button" class="pattern-choice" data-pattern="${index}" aria-pressed="false">${matrixHtml(matrix)}<span>Motif ${index + 1}</span></button>`).join("")}</div>`;
}

export function bindMotifs() { $$('[data-pattern]').forEach((button) => button.addEventListener("click", () => { choice = Number(button.dataset.pattern); $$('[data-pattern]').forEach((item) => item.setAttribute("aria-pressed", String(item === button))); })); }
export function readMotifsAnswer() { return { choix:choice }; }
