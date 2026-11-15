import { $ , $$ } from "../app.js";

let sequence = [];

function gridHtml(grid, positions = [], interactive = false) {
  return `<div class="matrix-board memory-grid grid-columns-${grid.colonnes}" role="grid">${Array.from({ length:grid.lignes * grid.colonnes }, (_, index) => {
    const row = Math.floor(index / grid.colonnes), col = index % grid.colonnes;
    const order = positions.findIndex((position) => position.ligne === row && position.colonne === col);
    return `<button type="button" class="matrix-cell grid-cell${order >= 0 ? interactive ? " selected" : " sequence" : ""}" data-row="${row}" data-col="${col}" ${interactive ? "" : "disabled"} aria-label="ligne ${row + 1}, colonne ${col + 1}">${order >= 0 ? order + 1 : ""}</button>`;
  }).join("")}</div>`;
}

export function renderVisuospatial(trial) {
  sequence = [];
  if (trial.condition === "presentation") return gridHtml(trial.stimulus.grille, trial.stimulus.sequence);
  return `<div id="spatial-grid">${gridHtml(trial.stimulus.grille, [], true)}</div><p id="spatial-count">0 sur ${trial.stimulus.longueur_sequence} positions</p><button type="button" class="secondary" id="reset-grid">Effacer</button>`;
}

export function bindVisuospatial(trial, rerender) {
  if (trial.condition !== "reproduction") return;
  $$('[data-row]').forEach((cell) => cell.addEventListener("click", () => {
    if (sequence.length >= trial.stimulus.longueur_sequence) return;
    const position = { ligne:Number(cell.dataset.row), colonne:Number(cell.dataset.col) };
    if (sequence.some((item) => item.ligne === position.ligne && item.colonne === position.colonne)) return;
    sequence.push(position); cell.classList.add("selected"); cell.textContent = sequence.length;
    $("#spatial-count").textContent = `${sequence.length} sur ${trial.stimulus.longueur_sequence} positions`;
  }));
  $("#reset-grid").addEventListener("click", rerender);
}

export function readVisuospatialAnswer() { return { positions:sequence }; }
