import json

from app import models


def _patient(client):
    return client.post(
        "/patients", json={"nom": "Sujet expérimental", "consentement": True}
    ).json()


def _start(client, patient_id, type_test="rappel", seed=42, parametres=None):
    response = client.post(
        "/sessions-test",
        json={
            "patient_id": patient_id,
            "protocole": "protocole-test",
            "type_test": type_test,
            "seed": seed,
            "parametres": parametres or {},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_current_trial_and_submission_do_not_leak_expected_answer(client):
    patient = _patient(client)
    session = _start(client, patient["id"], "rappel", parametres={"nombre_items": 3})

    current = client.get(f"/sessions-test/{session['id']}/essai-courant")
    assert current.status_code == 200
    assert "attendu" not in current.text

    submitted = client.post(
        f"/sessions-test/{session['id']}/reponses",
        json={"essai_index": 0, "reponse": {"continue": True}},
    )
    assert submitted.status_code == 200
    assert "attendu" not in submitted.text

    partial_results = client.get(f"/sessions-test/{session['id']}/resultats").json()
    assert partial_results["resultats"][0]["stimulus"] is None
    assert partial_results["resultats"][0]["reponse_attendue"] is None


def test_response_is_persisted_and_repeated_or_invalid_submissions_are_rejected(
    client, db_session
):
    patient = _patient(client)
    session = _start(
        client,
        patient["id"],
        "visuospatial",
        parametres={"mode": "fixe", "nombre_essais": 3, "difficulte": "facile"},
    )
    url = f"/sessions-test/{session['id']}/reponses"
    first = client.post(
        url,
        json={
            "essai_index": 0,
            "reponse": {"continue": True},
            "temps_reponse_ms": 800,
        },
    )
    assert first.status_code == 200

    repeated = client.post(
        url, json={"essai_index": 0, "reponse": {"continue": True}}
    )
    assert repeated.status_code == 409

    invalid = client.post(
        url,
        json={"essai_index": 1, "reponse": {"positions": [{"ligne": 0, "colonne": 0}]}},
    )
    assert invalid.status_code == 422

    saved = db_session.query(models.ReponseSession).filter_by(session_id=session["id"]).one()
    assert json.loads(saved.contenu) == {"continue": True}
    assert saved.stimulus is not None
    assert saved.temps_reponse_ms == 800
    assert saved.score is None


def test_completed_session_results_and_descriptive_analysis(client, db_session):
    patient = _patient(client)
    started = _start(
        client, patient["id"], "rappel", seed=5, parametres={"nombre_items": 3}
    )
    session_id = started["id"]
    url = f"/sessions-test/{session_id}/reponses"

    assert client.post(
        url, json={"essai_index": 0, "reponse": {"continue": True}}
    ).status_code == 200
    stored = db_session.get(models.SessionTest, session_id)
    essais = stored.essais

    free_items = essais[1]["attendu"]["items"]
    assert client.post(
        url, json={"essai_index": 1, "reponse": {"items": free_items}}
    ).status_code == 200

    cued = essais[2]["attendu"]["reponses"].copy()
    cued[next(iter(cued))] = "réponse incorrecte"
    assert client.post(
        url, json={"essai_index": 2, "reponse": {"reponses": cued}}
    ).status_code == 200

    recognized = essais[3]["attendu"]["items"]
    finished = client.post(
        url, json={"essai_index": 3, "reponse": {"items": recognized}}
    )
    assert finished.status_code == 200
    assert finished.json()["session_terminee"] is True

    results = client.get(f"/sessions-test/{session_id}/resultats")
    assert results.status_code == 200
    payload = results.json()
    assert payload["statut"] == "terminee"
    assert payload["resultats"][1]["reponse_attendue"] is not None
    assert payload["resultats"][1]["score"] == 1.0
    assert payload["resultats"][2]["score"] == 2 / 3

    json_export = client.get(f"/sessions-test/{session_id}/export/json")
    assert json_export.status_code == 200
    exported = json_export.json()
    assert exported["metadata"]["protocol_version"] == "2.0"
    assert exported["session"]["seed"] == 5
    assert exported["session"]["resultats"][1]["score"] == 1.0

    csv_export = client.get(f"/sessions-test/{session_id}/export/csv")
    assert csv_export.status_code == 200
    assert "session_id,patient_id" in csv_export.text
    assert "rappel_indice" in csv_export.text

    profile = client.get(f"/patients/{patient['id']}/profil-cognitif")
    assert profile.status_code == 200
    summary = profile.json()
    assert summary["sessions_terminees"] == 1
    conditions = summary["performances"]["rappel"]["conditions"]
    assert conditions["rappel_libre"]["score_moyen"] == 1.0
    assert conditions["rappel_indice"]["score_moyen"] == 0.666667
    assert conditions["reconnaissance"]["score_moyen"] == 1.0
    assert "diagnostique" in summary["avertissement"]
