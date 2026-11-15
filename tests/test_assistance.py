from app import models
from app.assistance import MoteurAdaptation, SelecteurIndices, StrategieAdaptation
from app.cognitive import ProfilCognitif


def _patient_with_memory(db_session, name="Sujet récupération"):
    patient = models.Patient(nom=name, consentement=True)
    souvenir = models.Souvenir(
        patient=patient,
        description="Pique-nique familial au bord du lac",
        provenance=models.ProvenanceSouvenir.PATIENT,
        statut_verification=models.StatutVerification.DECLARE,
        indices=[
            models.Indice(type="texte", contenu="Un lieu avec de l'eau", score_pertinence=0.2),
            models.Indice(type="catégorie", contenu="Une sortie familiale", score_pertinence=0.6),
            models.Indice(type="visuel", contenu="Photo du panier rouge", score_pertinence=0.9),
        ],
    )
    db_session.add(patient)
    db_session.commit()
    return patient, souvenir


def test_index_selection_is_deterministic_and_never_repeats(db_session):
    _, souvenir = _patient_with_memory(db_session)
    strategie = StrategieAdaptation("equilibree_par_defaut", [], "test")
    selecteur = SelecteurIndices()

    first, _ = selecteur.selectionner(souvenir.indices, set(), strategie, niveau_aide=0)
    repeated, _ = selecteur.selectionner(souvenir.indices, set(), strategie, niveau_aide=0)
    second, _ = selecteur.selectionner(
        souvenir.indices, {first.id}, strategie, niveau_aide=1
    )

    assert first.id == repeated.id
    assert second.id != first.id
    assert second.score_pertinence == 0.9


def test_adaptation_uses_repeated_descriptive_data_or_a_default():
    moteur = MoteurAdaptation()
    categorical_profile = ProfilCognitif(
        patient_id="p1",
        sessions_terminees=2,
        performances={
            "rappel": {
                "conditions": {
                    "rappel_libre": {"nombre_essais": 2, "score_moyen": 0.4},
                    "rappel_indice": {"nombre_essais": 2, "score_moyen": 0.8},
                }
            }
        },
    )
    assert moteur.choisir_strategie(categorical_profile).nom == "indices_categoriels"

    visual_profile = ProfilCognitif(
        patient_id="p2",
        sessions_terminees=4,
        performances={
            "reconnaissance_visuelle": {"nombre_essais": 2, "score_moyen": 0.8},
            "visuospatial": {"nombre_essais": 2, "score_moyen": 1.0},
        },
    )
    assert moteur.choisir_strategie(visual_profile).nom == "indices_visuels"

    insufficient_profile = ProfilCognitif(
        patient_id="p3",
        sessions_terminees=1,
        performances={
            "rappel": {
                "conditions": {
                    "rappel_libre": {"nombre_essais": 1, "score_moyen": 0.0},
                    "rappel_indice": {"nombre_essais": 1, "score_moyen": 1.0},
                }
            }
        },
    )
    assert moteur.choisir_strategie(insufficient_profile).nom == "equilibree_par_defaut"


def test_recovery_session_persists_resumes_and_keeps_evocation_unverified(
    client, db_session
):
    patient, souvenir = _patient_with_memory(db_session)
    started = client.post(
        f"/patients/{patient.id}/recuperations", json={"souvenir_id": souvenir.id}
    )
    assert started.status_code == 201
    session = started.json()
    assert session["strategie"] == "equilibree_par_defaut"

    cue_url = f"/patients/{patient.id}/recuperations/{session['id']}/indice"
    first = client.get(cue_url)
    resumed = client.get(cue_url)
    assert first.status_code == 200
    assert resumed.json()["id"] == first.json()["id"]

    feedback_url = f"/patients/{patient.id}/recuperations/{session['id']}/feedback"
    feedback = client.post(
        feedback_url,
        json={
            "tentative_id": first.json()["id"],
            "feedback": "non_retrouve",
            "reponse_patient": "Je pense à une promenade.",
            "souvenir_evoque": "Une promenade près d'une forêt, date inconnue",
        },
    )
    assert feedback.status_code == 200
    assert feedback.json()["candidat_id"] is not None

    second = client.get(cue_url)
    assert second.status_code == 200
    assert second.json()["id"] != first.json()["id"]
    assert second.json()["indice_id"] != first.json()["indice_id"]
    assert second.json()["niveau_aide"] == 1
    assert client.post(
        feedback_url,
        json={"tentative_id": second.json()["id"], "feedback": "non_retrouve"},
    ).status_code == 200

    finish = client.post(
        f"/patients/{patient.id}/recuperations/{session['id']}/terminer",
        json={"resultat": "non_retrouve"},
    )
    assert finish.status_code == 200
    history = finish.json()
    assert history["statut"] == "terminee"
    assert len(history["tentatives"]) == 2
    assert history["candidats"][0]["statut"] == "en_attente_verification"

    assert db_session.query(models.Souvenir).filter_by(patient_id=patient.id).count() == 1
    candidate = db_session.get(models.CandidatSouvenir, feedback.json()["candidat_id"])
    assert candidate.statut == "en_attente_verification"
    assert souvenir.statut_verification == models.StatutVerification.DECLARE


def test_patient_isolation_and_external_memory_verification_status(client, db_session):
    owner, souvenir = _patient_with_memory(db_session, "Propriétaire")
    other = models.Patient(nom="Autre sujet", consentement=True)
    db_session.add(other)
    db_session.commit()

    denied_start = client.post(
        f"/patients/{other.id}/recuperations", json={"souvenir_id": souvenir.id}
    )
    assert denied_start.status_code == 404

    session = client.post(
        f"/patients/{owner.id}/recuperations", json={"souvenir_id": souvenir.id}
    ).json()
    denied_history = client.get(
        f"/patients/{other.id}/recuperations/{session['id']}"
    )
    assert denied_history.status_code == 404

    external_url = (
        f"/patients/{owner.id}/recuperations/{session['id']}/memoire-externe"
    )
    unverified = client.get(external_url)
    assert unverified.status_code == 200
    assert unverified.json()["presentation_comme_fait_verifie"] is False
    assert "non vérifiée" in unverified.json()["avertissement"]
    assert unverified.json()["provenance"] == "patient"

    validation = client.post(
        f"/souvenirs/{souvenir.id}/validation",
        json={"source_validation": "Album familial daté"},
    )
    assert validation.status_code == 200
    verified = client.get(external_url)
    assert verified.json()["statut_verification"] == "verifie"
    assert verified.json()["presentation_comme_fait_verifie"] is True

    finished = client.post(
        f"/patients/{owner.id}/recuperations/{session['id']}/terminer",
        json={"resultat": "assistance_externe"},
    )
    assert finished.status_code == 200
    assert finished.json()["resultat_final"] == "assistance_externe"
