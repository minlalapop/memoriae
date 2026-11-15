import { api, escapeHtml } from "./api.js";
import { $, appReady, message } from "./app.js";

async function logout() { await api("/api/auth/logout", { method:"POST", body:"{}" }); window.location.href = "/connexion"; }
const percent = (value) => `${Math.round(value * 10000) / 100} %`;

appReady.then(async () => {
  $("#logout").addEventListener("click", logout);
  try {
    const [models, experiments] = await Promise.all([
      api("/api/research/models"),
      api("/api/research/models/memoriae_v2/experiments"),
    ]);
    const model = models[0];
    $("#model-status").textContent = model.status;
    $("#run-model").disabled = !model.available || !experiments.length;
    $("#model-experiment").innerHTML = experiments.length
      ? experiments.map((item) => `<option value="${item.id}">${escapeHtml(item.nom)}</option>`).join("")
      : '<option value="">Aucune expérience compatible</option>';
  } catch (error) { message(error.message, true); }
  $("#model-form").addEventListener("submit", async (event) => {
    event.preventDefault(); $("#run-model").disabled = true; message("Exécution en cours…");
    try {
      const result = await api("/api/research/models/memoriae_v2/execute", { method:"POST", body:JSON.stringify({experiment_id:$("#model-experiment").value}) });
      $("#model-result").hidden = false;
      $("#model-result").innerHTML = `<h3>Résultat computationnel</h3><p><strong>Accuracy :</strong> ${percent(result.accuracy)}</p><p><strong>MSE moyenne :</strong> ${result.mse.toFixed(6)}</p><p><strong>Essais :</strong> ${result.nombre_essais}</p><a class="secondary-link" href="/chercheur/resultats">Comparer aux résultats humains</a>`;
      message("Exécution terminée.");
    } catch (error) { message(error.message, true); }
    finally { $("#run-model").disabled = false; }
  });
});
