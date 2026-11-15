import { escapeHtml } from "../api.js";
import { $, $$ } from "../app.js";

export function renderRappel(trial) {
  const stimulus = trial.stimulus;
  if (trial.condition === "presentation") return `<ul class="stimulus-list">${stimulus.elements.map((item) => `<li><strong>${escapeHtml(item.categorie)}</strong> : ${escapeHtml(item.item)}</li>`).join("")}</ul>`;
  if (trial.condition === "rappel_libre") return `<div class="answer-list free-recall-list">${Array.from({ length:stimulus.nombre_attendu }, (_, index) => `<input data-free-answer autocomplete="off" placeholder="Un mot rappelé" aria-label="Mot rappelé ${index + 1}">`).join("")}</div>`;
  if (trial.condition === "rappel_indice") return `<div class="answer-list">${stimulus.categories.map((category) => `<label>${escapeHtml(category)}<input data-cued-answer="${escapeHtml(category)}" autocomplete="off"></label>`).join("")}</div>`;
  return `<div class="answer-list choice-list">${stimulus.propositions.map((item) => `<label><input type="checkbox" data-word-choice value="${escapeHtml(item)}">${escapeHtml(item)}</label>`).join("")}</div>`;
}

export function readRappelAnswer(trial) {
  if (trial.condition === "rappel_libre") return { items:$$('[data-free-answer]').map((input) => input.value.trim()).filter(Boolean) };
  if (trial.condition === "rappel_indice") { const answer = { reponses:{} }; $$('[data-cued-answer]').forEach((input) => { answer.reponses[input.dataset.cuedAnswer] = input.value.trim(); }); return answer; }
  return { items:$$('[data-word-choice]:checked').map((input) => input.value) };
}
