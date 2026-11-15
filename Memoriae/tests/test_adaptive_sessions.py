import pytest

from app import models


def _patient(client, name="Sujet adaptatif"):
    response = client.post(
        "/patients", json={"nom": name, "consentement": True}
    )
    assert response.status_code == 201
    return response.json()


def _start_grid(client, patient_id, parameters):
    response = client.post(
        "/sessions-test",
        json={
            "patient_id": patient_id,
            "protocole": "progression-grilles",
            "type_test": "visuospatial",
            "seed": 123,
            "parametres": parameters,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_fixed_progression_persists_trials_scores_and_decisions(client, db_session):
    patient = _patient(client)
    started = _start_grid(
        client,
        patient["id"],
        {
            "mode": "fixe",
            "difficulte": "facile",
            "nombre_essais": 3,
            "maximum_essais": 3,
        },
    )
    session_id = started["id"]
    response_url = f"/sessions-test/{session_id}/reponses"

    for trial_number in range(3):
        current = client.get(
            f"/sessions-test/{session_id}/essai-courant"
        ).json()
        assert current["condition"] == "presentation"
        assert client.post(
            response_url,
            json={"essai_index": current["essai_index"], "reponse": {"continue": True}},
        ).status_code == 200

        db_session.expire_all()
        stored = db_session.get(models.SessionTest, session_id)
        reproduction = stored.essais[stored.essai_courant]
        submitted = client.post(
            response_url,
            json={
                "essai_index": reproduction["index"],
                "reponse": reproduction["attendu"],
            },
        )
        assert submitted.status_code == 200
        assert submitted.json()["session_terminee"] is (trial_number == 2)

    results = client.get(f"/sessions-test/{session_id}/resultats").json()
    scored = [item for item in results["resultats"] if item["score"] is not None]
    assert [item["score"] for item in scored] == [1.0, 1.0, 1.0]
    assert [item["mesures"]["taille_grille"] for item in scored] == [
        {"lignes": 2, "colonnes": 2},
        {"lignes": 2, "colonnes": 3},
        {"lignes": 3, "colonnes": 3},
    ]
    assert scored[-1]["mesures"]["decision_progression"]["action"] == "arreter_nombre_fixe"
    assert results["parametres"]["algorithme_adaptatif"]["maximum_essais"] == 3


def test_one_failed_trial_does_not_stop_adaptive_task(client, db_session):
    patient = _patient(client, "Sujet erreur isolée")
    started = _start_grid(
        client,
        patient["id"],
        {"mode": "adaptatif", "maximum_essais": 3},
    )
    session_id = started["id"]
    url = f"/sessions-test/{session_id}/reponses"
    client.post(url, json={"essai_index": 0, "reponse": {"continue": True}})
    stored = db_session.get(models.SessionTest, session_id)
    positions = stored.essais[1]["attendu"]["positions"]
    response = client.post(
        url,
        json={"essai_index": 1, "reponse": {"positions": list(reversed(positions))}},
    )
    assert response.status_code == 200
    assert response.json()["session_terminee"] is False
    assert response.json()["mesures"]["decision_progression"]["action"] == "continuer_reduire"
    assert client.get(f"/sessions-test/{session_id}/essai-courant").status_code == 200


@pytest.mark.parametrize(
    "test_type", ["visuospatial", "reconnaissance_visuelle", "memoire_visuelle"]
)
def test_progressive_visual_protocols_complete_through_the_api(
    client, db_session, test_type
):
    patient = _patient(client, f"Sujet {test_type}")
    parameters = {
        "mode": "fixe",
        "difficulte": "facile",
        "nombre_essais": 3,
        "maximum_essais": 3,
    }
    if test_type == "reconnaissance_visuelle":
        parameters["nombre_propositions"] = 4
    started = client.post(
        "/sessions-test",
        json={
            "patient_id": patient["id"],
            "protocole": f"parcours-{test_type}",
            "type_test": test_type,
            "seed": 77,
            "parametres": parameters,
        },
    ).json()
    session_id = started["id"]
    url = f"/sessions-test/{session_id}/reponses"

    while True:
        current_response = client.get(f"/sessions-test/{session_id}/essai-courant")
        if current_response.status_code == 409:
            break
        current = current_response.json()
        if current["condition"] == "presentation":
            answer = {"continue": True}
        else:
            db_session.expire_all()
            stored = db_session.get(models.SessionTest, session_id)
            answer = stored.essais[current["essai_index"]]["attendu"]
        submitted = client.post(
            url,
            json={"essai_index": current["essai_index"], "reponse": answer},
        )
        assert submitted.status_code == 200
        if submitted.json()["session_terminee"]:
            break

    results = client.get(f"/sessions-test/{session_id}/resultats").json()
    assert len([item for item in results["resultats"] if item["score"] is not None]) == 3
    assert all(
        item["score"] == 1.0
        for item in results["resultats"]
        if item["score"] is not None
    )


def test_patient_and_memory_can_be_updated_and_deleted(client):
    patient = _patient(client, "Prénom Nom")
    updated = client.patch(
        f"/patients/{patient['id']}", json={"nom": "Prénom Modifié"}
    )
    assert updated.status_code == 200

    memory = client.post(
        f"/patients/{patient['id']}/souvenirs",
        json={
            "description": "Sortie au parc",
            "provenance": "proche",
            "indices": [
                {"type": "sortie familiale", "contenu": "le parc", "score_pertinence": 0.75}
            ],
        },
    ).json()
    changed = client.patch(
        f"/souvenirs/{memory['id']}",
        json={
            "description": "Sortie familiale au parc",
            "indices": [
                {"type": "lieu", "contenu": "près du lac", "score_pertinence": 1.0}
            ],
        },
    )
    assert changed.status_code == 200
    assert changed.json()["indices"][0]["type"] == "lieu"
    assert client.delete(f"/souvenirs/{memory['id']}").status_code == 204
    assert client.delete(f"/patients/{patient['id']}").status_code == 204
