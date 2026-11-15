import { api, escapeHtml } from "./api.js";
import { $, appReady, message, updateActiveParticipant } from "./app.js";

let protocols = [], experiments = [], participants = [], steps = [];

const protocolName = (type) => protocols.find((item) => item.type === type)?.description || type;
const participantName = (item) => [item.prenom, item.nom].filter(Boolean).join(" ");

async function logout() {
  await api("/api/auth/logout", { method:"POST", body:"{}" });
  window.location.href = "/connexion";
}

function defaultStep(type = protocols[0]?.type) {
  const protocol = protocols.find((item) => item.type === type);
  return { test_type:type, parametres:{ ...(protocol?.parametres_defaut || {}) }, seed_offset:steps.length * 100 };
}

function parameterFields(step, index) {
  const p = step.parametres;
  if (step.test_type === "rappel") return `
    <label><span>Difficulté des mots</span><select data-step="${index}" data-param="difficulte_mots"><option value="facile" ${p.difficulte_mots === "facile" ? "selected" : ""}>Facile</option><option value="moyen" ${p.difficulte_mots === "moyen" ? "selected" : ""}>Moyenne</option><option value="difficile" ${p.difficulte_mots === "difficile" ? "selected" : ""}>Difficile</option></select></label>
    <label><span>Nombre de mots</span><input type="number" min="2" max="8" value="${p.nombre_items}" data-step="${index}" data-param="nombre_items"></label>`;
  if (step.test_type === "associatif") return `
    <label><span>Nombre d’objets</span><input type="number" min="3" max="6" value="${p.nombre_items}" data-step="${index}" data-param="nombre_items"></label>
    <label><span>Choix par question</span><input type="number" min="2" max="4" value="${p.nombre_options}" data-step="${index}" data-param="nombre_options"></label>
    <label><span>Présentation en secondes</span><input type="number" min="1" max="15" value="${p.duree_presentation_ms / 1000}" data-step="${index}" data-param="duree_presentation_ms" data-seconds="true"></label>`;
  if (step.test_type === "fashion_mnist_partiel") {
    if (p.nombre_essais !== undefined) return `
      <p class="meta">Ancienne configuration conservée : ${p.nombre_images} images, ${p.nombre_essais} essai(s), masquage ${Math.round(p.mask_ratio * 100)} %.</p>
      <label><span>Présentation en secondes</span><input type="number" min="1" max="30" value="${p.duree_presentation_ms / 1000}" data-step="${index}" data-param="duree_presentation_ms" data-seconds="true"></label>`;
    return `<p class="meta">12 images, 4 essais à 25 %, 4 à 50 % et 4 à 75 %. L’ordre est mélangé à partir de la seed.</p>
      <label><span>Présentation en secondes</span><input type="number" min="1" max="30" value="${p.duree_presentation_ms / 1000}" data-step="${index}" data-param="duree_presentation_ms" data-seconds="true"></label>`;
  }
  return `
    <label><span>Progression</span><select data-step="${index}" data-param="mode"><option value="adaptatif" ${p.mode === "adaptatif" ? "selected" : ""}>Adaptative</option><option value="fixe" ${p.mode === "fixe" ? "selected" : ""}>Fixe</option></select></label>
    ${p.mode === "fixe" || step.test_type === "reconnaissance_visuelle" ? `<label><span>Difficulté</span><select data-step="${index}" data-param="difficulte"><option value="facile" ${p.difficulte === "facile" ? "selected" : ""}>Facile</option><option value="moyen" ${p.difficulte === "moyen" ? "selected" : ""}>Moyenne</option><option value="difficile" ${p.difficulte === "difficile" ? "selected" : ""}>Difficile</option></select></label>` : ""}${p.mode === "fixe" ? `<label><span>Nombre d’essais</span><input type="number" min="3" max="10" value="${p.nombre_essais}" data-step="${index}" data-param="nombre_essais"></label>` : ""}`;
}

function renderSteps() {
  $("#steps-list").innerHTML = steps.map((step, index) => `
    <div class="step-editor">
      <div class="step-top"><span class="step-number">${index + 1}</span><select data-step-type="${index}">${protocols.map((protocol) => `<option value="${protocol.type}" ${protocol.type === step.test_type ? "selected" : ""}>${escapeHtml(protocol.description)}</option>`).join("")}</select><button type="button" class="danger" data-remove-step="${index}" ${steps.length === 1 ? "disabled" : ""}>Retirer</button></div>
      <div class="step-parameters">${parameterFields(step, index)}</div>
      <div class="button-row"><button type="button" class="secondary" data-move-up="${index}" ${index === 0 ? "disabled" : ""}>Monter</button><button type="button" class="secondary" data-move-down="${index}" ${index === steps.length - 1 ? "disabled" : ""}>Descendre</button></div>
    </div>`).join("");
}

function bindStepEditor() {
  $("#steps-list").addEventListener("change", (event) => {
    const target = event.target;
    if (target.dataset.stepType !== undefined) {
      steps[Number(target.dataset.stepType)] = defaultStep(target.value); renderSteps(); return;
    }
    if (target.dataset.param) {
      const step = steps[Number(target.dataset.step)];
      let value = target.type === "number" ? Number(target.value) : target.value;
      if (target.dataset.seconds) value *= 1000;
      step.parametres[target.dataset.param] = value;
      if (target.dataset.param === "mode") renderSteps();
    }
  });
  $("#steps-list").addEventListener("click", (event) => {
    const button = event.target.closest("button"); if (!button) return;
    const action = ["removeStep", "moveUp", "moveDown"].find((name) => button.dataset[name] !== undefined);
    if (!action) return;
    const index = Number(button.dataset[action]);
    if (action === "removeStep") steps.splice(index, 1);
    if (action === "moveUp") [steps[index - 1], steps[index]] = [steps[index], steps[index - 1]];
    if (action === "moveDown") [steps[index + 1], steps[index]] = [steps[index], steps[index + 1]];
    renderSteps();
  });
}

function openExperiment(experiment = null) {
  $("#experiment-id").value = experiment?.id || "";
  $("#experiment-form-title").textContent = experiment ? "Modifier l’expérience" : "Nouvelle expérience";
  $("#experiment-name").value = experiment?.nom || "";
  $("#experiment-description").value = experiment?.description || "";
  $("#seed-base").value = experiment?.seed_base ?? 42;
  $("#experiment-active").checked = experiment?.active ?? true;
  steps = experiment ? experiment.etapes.map((step) => ({ test_type:step.test_type, parametres:{...step.parametres}, seed_offset:step.seed_offset })) : [defaultStep()];
  renderSteps(); $("#experiment-form").hidden = false; $("#experiment-name").focus();
}

async function saveExperiment(event) {
  event.preventDefault();
  const id = $("#experiment-id").value;
  const body = { nom:$("#experiment-name").value.trim(), description:$("#experiment-description").value.trim() || null, seed_base:Number($("#seed-base").value), active:$("#experiment-active").checked, etapes:steps };
  try {
    await api(id ? `/api/research/experiments/${id}` : "/api/research/experiments", { method:id ? "PATCH" : "POST", body:JSON.stringify(body) });
    $("#experiment-form").hidden = true; message(id ? "Expérience modifiée." : "Expérience créée."); await loadExperiments();
  } catch (error) { message(error.message, true); }
}

async function loadExperiments() {
  experiments = await api("/api/research/experiments");
  $("#experiment-list").innerHTML = experiments.length ? experiments.map((item) => `
    <article class="record"><h3>${escapeHtml(item.nom)}</h3>${item.description ? `<p>${escapeHtml(item.description)}</p>` : ""}<p><strong>Code : ${escapeHtml(item.code)}</strong></p>
    <ol>${item.etapes.map((step) => `<li>${escapeHtml(protocolName(step.test_type))}</li>`).join("")}</ol>
    <p class="meta">${item.active ? "Active" : "Inactive"}</p><div class="record-actions">
      <button type="button" data-launch="${item.id}">Lancer avec le participant actif</button><button type="button" class="secondary" data-edit="${item.id}">Modifier</button><button type="button" class="secondary" data-duplicate="${item.id}">Dupliquer</button><button type="button" class="secondary" data-toggle="${item.id}" data-active="${item.active}">${item.active ? "Désactiver" : "Activer"}</button><button type="button" class="danger" data-delete="${item.id}">Supprimer</button>
    </div></article>`).join("") : '<p class="empty-state">Aucune expérience.</p>';
}

async function experimentAction(event) {
  const button = event.target.closest("button"); if (!button) return;
  try {
    if (button.dataset.edit) openExperiment(experiments.find((item) => item.id === button.dataset.edit));
    if (button.dataset.toggle) { await api(`/api/research/experiments/${button.dataset.toggle}`, { method:"PATCH", body:JSON.stringify({active:button.dataset.active !== "true"}) }); await loadExperiments(); }
    if (button.dataset.duplicate) { await api(`/api/research/experiments/${button.dataset.duplicate}/duplicate`, {method:"POST", body:"{}"}); await loadExperiments(); }
    if (button.dataset.delete && confirm("Supprimer cette expérience ?")) { await api(`/api/research/experiments/${button.dataset.delete}`, {method:"DELETE"}); await loadExperiments(); }
    if (button.dataset.launch) {
      const patientId = localStorage.getItem("memoriae_active_participant_id");
      if (!patientId) throw new Error("Sélectionnez d’abord un participant actif.");
      const started = await api(`/api/research/experiments/${button.dataset.launch}/launch`, {method:"POST", body:JSON.stringify({patient_id:patientId})});
      sessionStorage.setItem("memoriae_session", started.session_id); window.location.href = "/experience";
    }
  } catch (error) { message(error.message, true); }
}

function openParticipant(item = null) {
  $("#participant-id").value = item?.id || ""; $("#participant-form-title").textContent = item ? "Modifier le participant" : "Nouveau participant";
  $("#participant-lastname").value = item?.nom || ""; $("#participant-firstname").value = item?.prenom || ""; $("#participant-age").value = item?.age ?? "";
  $("#participant-form").hidden = false; $("#participant-lastname").focus();
}

async function saveParticipant(event) {
  event.preventDefault(); const id = $("#participant-id").value;
  const body = { nom:$("#participant-lastname").value.trim(), prenom:$("#participant-firstname").value.trim() || null, age:$("#participant-age").value ? Number($("#participant-age").value) : null };
  try { await api(id ? `/api/research/participants/${id}` : "/api/research/participants", {method:id ? "PATCH" : "POST", body:JSON.stringify(body)}); $("#participant-form").hidden = true; await loadParticipants(); }
  catch (error) { message(error.message, true); }
}

async function loadParticipants() {
  participants = await api("/api/research/participants");
  const selectedId = localStorage.getItem("memoriae_active_participant_id");
  if (selectedId && !participants.some((item) => item.id === selectedId)) { localStorage.removeItem("memoriae_active_participant_id"); localStorage.removeItem("memoriae_active_participant_name"); updateActiveParticipant(); }
  $("#participant-list").innerHTML = participants.length ? participants.map((item) => `<article class="record ${item.id === selectedId ? "selected-record" : ""}"><h3>${escapeHtml(participantName(item))}</h3><p>${item.age === null ? "Âge non renseigné" : `${item.age} ans`}</p><div class="record-actions"><button type="button" data-select-participant="${item.id}">${item.id === selectedId ? "Participant actif" : "Sélectionner"}</button><button type="button" class="secondary" data-edit-participant="${item.id}">Modifier</button><button type="button" class="danger" data-delete-participant="${item.id}">Supprimer</button></div></article>`).join("") : '<p class="empty-state">Aucun participant.</p>';
}

async function participantAction(event) {
  const button = event.target.closest("button"); if (!button) return;
  try {
    if (button.dataset.selectParticipant) { const item = participants.find((p) => p.id === button.dataset.selectParticipant); localStorage.setItem("memoriae_active_participant_id", item.id); localStorage.setItem("memoriae_active_participant_name", participantName(item)); updateActiveParticipant(participantName(item)); await loadParticipants(); }
    if (button.dataset.editParticipant) openParticipant(participants.find((p) => p.id === button.dataset.editParticipant));
    if (button.dataset.deleteParticipant && confirm("Supprimer ce participant de la liste ?")) { await api(`/api/research/participants/${button.dataset.deleteParticipant}`, {method:"DELETE"}); await loadParticipants(); }
  } catch (error) { message(error.message, true); }
}

appReady.then(async () => {
  $("#logout").addEventListener("click", logout);
  $("#show-participant-form").addEventListener("click", () => openParticipant()); $("#cancel-participant").addEventListener("click", () => { $("#participant-form").hidden = true; }); $("#participant-form").addEventListener("submit", saveParticipant); $("#participant-list").addEventListener("click", participantAction);
  $("#show-experiment-form").addEventListener("click", () => openExperiment()); $("#cancel-experiment").addEventListener("click", () => { $("#experiment-form").hidden = true; }); $("#add-step").addEventListener("click", () => { steps.push(defaultStep()); renderSteps(); }); $("#experiment-form").addEventListener("submit", saveExperiment); $("#experiment-list").addEventListener("click", experimentAction); bindStepEditor();
  try { protocols = await api("/tests-cognitifs"); await Promise.all([loadParticipants(), loadExperiments()]); }
  catch (error) { if (error.message.includes("Authentification")) window.location.href = "/connexion"; else message(error.message, true); }
});
