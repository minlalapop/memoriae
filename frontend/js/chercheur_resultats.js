import { api, escapeHtml } from "./api.js";
import { $, $$, appReady, message } from "./app.js";

const labels = { rappel:"Rappel verbal", visuospatial:"Mémoire visuospatiale", reconnaissance_visuelle:"Reconnaissance de motifs", memoire_visuelle:"Mémoire visuelle", associatif:"Mémoire associative", fashion_mnist_partiel:"Reconnaissance d’image partielle", presentation:"Présentation", reconnaissance_indicee:"Reconnaissance indicée" };
const dateTime = (value) => value ? new Intl.DateTimeFormat("fr-FR", { dateStyle:"medium", timeStyle:"short" }).format(new Date(value)) : "";
const percent = (value) => value === null ? "Non terminé" : `${Math.round(value * 100)} %`;

async function logout() { await api("/api/auth/logout", { method:"POST", body:"{}" }); window.location.href = "/connexion"; }

function readable(value) {
  if (value === null || value === undefined) return "Non renseigné";
  if (Array.isArray(value)) return value.map(readable).join(", ");
  if (typeof value === "object") return Object.entries(value).map(([key, item]) => `${key.replaceAll("_", " ")} : ${readable(item)}`).join("; ");
  if (typeof value === "boolean") return value ? "Oui" : "Non";
  return String(value);
}

async function loadResults() {
  try {
    const results = await api("/api/research/results");
    $("#research-results").innerHTML = results.length ? `<div class="table-scroll"><table><thead><tr><th>Date</th><th>Participant</th><th>Expérience</th><th>Test</th><th>Score</th><th></th></tr></thead><tbody>${results.map((item) => `<tr><td>${dateTime(item.started_at)}</td><td>${escapeHtml(item.pseudonyme)}</td><td>${escapeHtml(item.experience)}</td><td>${escapeHtml(labels[item.test_type] || item.test_type)}</td><td>${percent(item.score)}</td><td><button type="button" class="secondary" data-session="${item.session_id}">Consulter</button>${item.test_type === "fashion_mnist_partiel" ? `<button type="button" class="secondary" data-comparison="${item.experiment_id}">Comparer</button>` : ""}</td></tr>`).join("")}</tbody></table></div>` : '<p>Aucun résultat.</p>';
    $$('[data-session]').forEach((button) => button.addEventListener("click", () => showDetail(button.dataset.session)));
    $$('[data-comparison]').forEach((button) => button.addEventListener("click", () => showComparison(button.dataset.comparison)));
  } catch (error) { if (error.message.includes("Authentification")) window.location.href = "/connexion"; else message(error.message, true); }
}

async function showComparison(experimentId) {
  try {
    const data = await api(`/api/research/experiments/${experimentId}/comparison`), container = $("#result-detail"); container.hidden = false;
    const levels = [["0.25", "25 %"], ["0.5", "50 %"], ["0.75", "75 %"]];
    const levelRows = levels.map(([key, label]) => {
      const humanLevel = data.human.by_mask[key], modelLevel = data.model?.by_mask?.[key];
      const humanValue = humanLevel?.accuracy ?? 0, modelValue = modelLevel?.accuracy ?? 0;
      return `<section class="mask-comparison"><h4>Masquage ${label}</h4><div><span>Participants humains</span><progress max="100" value="${Math.round(humanValue * 100)}"></progress><strong>${humanLevel?.accuracy === null ? "Données insuffisantes" : percent(humanValue)}</strong><small>${humanLevel?.trials || 0} essai(s)</small></div><div><span>Memoriae V2</span><progress max="100" value="${Math.round(modelValue * 100)}"></progress><strong>${modelLevel?.accuracy === null || !modelLevel ? "Aucune exécution" : percent(modelValue)}</strong><small>${modelLevel ? `${modelLevel.trials} essai(s), MSE ${modelLevel.mse.toFixed(6)}` : ""}</small></div></section>`;
    }).join("");
    container.innerHTML = `<h3>Comparaison humain et modèle</h3><p>${escapeHtml(data.experiment_name)}</p><p><strong>Participants :</strong> ${data.human.participants} · <strong>Essais humains :</strong> ${data.human.trials} · <strong>Essais V2 :</strong> ${data.model?.nombre_essais || 0}</p>${data.human.status === "Données insuffisantes" ? '<p class="inline-error">Données insuffisantes</p>' : ""}<div class="comparison-bars">${levelRows}</div><h4 class="subheading">Erreurs par image</h4><div class="table-scroll"><table><thead><tr><th>Image</th><th>Masquage</th><th>Erreurs humaines</th><th>Erreurs du modèle</th><th>Observation</th></tr></thead><tbody>${data.by_stimulus.map((item) => `<tr><td>${item.src ? `<img class="result-stimulus" src="${escapeHtml(item.src)}" alt="${escapeHtml(item.label || item.stimulus_id)}">` : ""}${escapeHtml(item.label || item.stimulus_id)}</td><td>${Math.round(item.mask_ratio * 100)} %</td><td>${item.human_errors} sur ${item.human_trials}</td><td>${item.model_errors} sur ${item.model_trials}</td><td>${data.divergent_stimulus_ids.includes(item.stimulus_id) ? "Divergence" : ""}</td></tr>`).join("")}</tbody></table></div>`;
  } catch (error) { message(error.message, true); }
}

async function showDetail(sessionId) {
  try {
    const data = await api(`/api/research/results/${sessionId}`), container = $("#result-detail"); container.hidden = false;
    container.innerHTML = `<h3>${escapeHtml(labels[data.type_test] || data.type_test)}</h3><div class="table-scroll"><table><thead><tr><th>Condition</th><th>Stimulus</th><th>Réponse</th><th>Attendu</th><th>Score</th><th>Temps</th></tr></thead><tbody>${data.resultats.map((item) => `<tr><td>${escapeHtml(labels[item.condition] || item.condition)}</td><td>${escapeHtml(readable(item.stimulus))}</td><td>${escapeHtml(readable(item.reponse))}</td><td>${escapeHtml(readable(item.reponse_attendue))}</td><td>${item.score === null ? "Non évalué" : percent(item.score)}</td><td>${item.temps_reponse_ms === null ? "Non mesuré" : `${item.temps_reponse_ms} ms`}</td></tr>`).join("")}</tbody></table></div>`;
  } catch (error) { message(error.message, true); }
}

appReady.then(() => { $("#logout").addEventListener("click", logout); $("#refresh-results").addEventListener("click", loadResults); loadResults(); });
