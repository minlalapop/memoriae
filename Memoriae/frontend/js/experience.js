import { api, escapeHtml } from "./api.js";
import { $, appReady, message } from "./app.js";
import { bindAssociatif, readAssociatifAnswer, renderAssociatif } from "./tests/associatif.js";
import { bindFashion, readFashionAnswer, renderFashion } from "./tests/fashion.js";
import { bindImages, readImagesAnswer, renderImages } from "./tests/images.js";
import { bindMotifs, readMotifsAnswer, renderMotifs } from "./tests/motifs.js";
import { readRappelAnswer, renderRappel } from "./tests/rappel.js";
import { bindVisuospatial, readVisuospatialAnswer, renderVisuospatial } from "./tests/visuospatial.js";

let sessionId = null, trial = null, testType = null, startedAt = null, presentationTimer = null;

function renderer(type) {
  if (type === "rappel") return { render:renderRappel, read:readRappelAnswer };
  if (type === "visuospatial") return { render:renderVisuospatial, read:readVisuospatialAnswer, bind:bindVisuospatial };
  if (type === "reconnaissance_visuelle") return { render:renderMotifs, read:readMotifsAnswer, bind:bindMotifs };
  if (type === "associatif") return { render:renderAssociatif, read:readAssociatifAnswer, bind:bindAssociatif };
  if (type === "fashion_mnist_partiel") return { render:renderFashion, read:readFashionAnswer, bind:bindFashion };
  return { render:renderImages, read:readImagesAnswer, bind:bindImages };
}

async function nextTrial() {
  const data = await api(`/api/sessions/${sessionId}/next`);
  if (data.changement_etape) {
    sessionId = data.session_id;
    sessionStorage.setItem("memoriae_session", sessionId);
    $("#trial-progress").textContent = `Test ${data.etape} sur ${data.nombre_etapes}`;
    await nextTrial();
    return;
  }
  if (data.terminee) { await finish(); return; }
  trial = data.essai; testType = data.test_type; startedAt = performance.now();
  $("#trial-progress").textContent = `Étape ${data.progression.courant} sur ${data.progression.total}`;
  renderTrial();
}

function renderTrial() {
  if (presentationTimer) clearInterval(presentationTimer);
  const current = renderer(testType), presentation = trial.condition === "presentation";
  $("#experiment-workspace").innerHTML = `<div class="trial-header"><h2>${escapeHtml(trial.phase.replaceAll("_", " "))}</h2><p>${escapeHtml(trial.stimulus.instruction || "")}</p></div><p id="trial-error" class="inline-error" role="alert" hidden></p>${current.render(trial)}<div class="button-row"><button type="button" id="submit-trial">${presentation ? "Continuer" : "Valider"}</button></div>`;
  current.bind?.(trial, renderTrial);
  const button = $("#submit-trial");
  button.addEventListener("click", () => submit(presentation ? { continue:true } : current.read(trial)));
  const duration = trial.stimulus.duree_presentation_ms;
  if (presentation && duration) {
    button.hidden = true;
    const deadline = performance.now() + duration;
    const update = () => {
      const remaining = Math.max(0, deadline - performance.now());
      $("#presentation-timer").textContent = `Présentation : ${Math.ceil(remaining / 1000)} s`;
      if (remaining <= 0) { clearInterval(presentationTimer); submit({ continue:true }); }
    };
    update(); presentationTimer = setInterval(update, 200);
  }
}

async function submit(answer) {
  try {
    const presentation = trial.condition === "presentation";
    await api(`/api/sessions/${sessionId}/responses`, {
      method:"POST",
      body:JSON.stringify({
        essai_index:trial.essai_index,
        reponse:answer,
        temps_reponse_ms:presentation ? null : Math.round(performance.now() - startedAt),
      }),
    });
    await nextTrial();
  } catch (error) { const output = $("#trial-error"); output.textContent = error.message; output.hidden = false; }
}

async function finish() {
  await api(`/api/sessions/${sessionId}/finish`, { method:"POST", body:"{}" });
  sessionStorage.removeItem("memoriae_session");
  $("#trial-progress").textContent = "";
  $("#experiment-workspace").innerHTML = '<div class="test-score"><h2>Expérience terminée</h2><p>Vos réponses ont été enregistrées.</p><a class="secondary-link" href="/">Retour à l’accueil</a></div>';
}

appReady.then(async () => {
  sessionId = sessionStorage.getItem("memoriae_session");
  if (!sessionId) { window.location.href = "/participer"; return; }
  try { await nextTrial(); } catch (error) { message(error.message, true); }
});
