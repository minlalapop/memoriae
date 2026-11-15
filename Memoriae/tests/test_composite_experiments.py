from app import models


def _complete_current_session(client, db_session, session_id):
    while True:
        current = client.get(f"/api/sessions/{session_id}/next")
        assert current.status_code == 200
        payload = current.json()
        if payload.get("changement_etape"):
            return payload["session_id"]
        if payload["terminee"]:
            return None
        trial = payload["essai"]
        stored = db_session.get(models.SessionTest, session_id)
        expected = stored.essais[trial["essai_index"]]["attendu"]
        answer = {"continue": True} if expected is None else expected
        submitted = client.post(
            f"/api/sessions/{session_id}/responses",
            json={"essai_index": trial["essai_index"], "reponse": answer},
        )
        assert submitted.status_code == 200


def test_composite_experiment_and_synthetic_participant_path(client, db_session):
    created = client.post(
        "/api/research/experiments",
        json={
            "nom": "Parcours mémoire",
            "description": "Deux tâches ordonnées",
            "seed_base": 80,
            "etapes": [
                {
                    "test_type": "rappel",
                    "parametres": {"nombre_items": 2, "difficulte_mots": "facile"},
                    "seed_offset": 0,
                },
                {
                    "test_type": "associatif",
                    "parametres": {
                        "nombre_items": 3,
                        "nombre_options": 2,
                        "duree_presentation_ms": 1000,
                    },
                    "seed_offset": 100,
                },
            ],
        },
    )
    assert created.status_code == 201
    experiment = created.json()
    assert [step["test_type"] for step in experiment["etapes"]] == ["rappel", "associatif"]

    updated = client.patch(
        f"/api/research/experiments/{experiment['id']}",
        json={"nom": "Parcours mémoire modifié", "etapes": list(reversed(experiment["etapes"]))},
    )
    assert updated.status_code == 200
    assert [step["test_type"] for step in updated.json()["etapes"]] == [
        "associatif",
        "rappel",
    ]
    duplicated = client.post(f"/api/research/experiments/{experiment['id']}/duplicate")
    assert duplicated.status_code == 201
    assert duplicated.json()["active"] is False

    participant = client.post(
        "/api/research/participants",
        json={"nom": "Martin", "prenom": "Alice", "age": 64},
    )
    assert participant.status_code == 201
    participant_id = participant.json()["id"]
    assert client.patch(
        f"/api/research/participants/{participant_id}", json={"age": 65}
    ).json()["age"] == 65

    launched = client.post(
        f"/api/research/experiments/{experiment['id']}/launch",
        json={"patient_id": participant_id},
    )
    assert launched.status_code == 201
    first_session = launched.json()["session_id"]
    second_session = _complete_current_session(client, db_session, first_session)
    assert second_session is not None and second_session != first_session
    assert _complete_current_session(client, db_session, second_session) is None
    assert client.post(f"/api/sessions/{second_session}/finish").status_code == 200

    results = client.get("/api/research/results").json()
    experiment_results = [row for row in results if row["experience"] == "Parcours mémoire modifié"]
    assert len(experiment_results) == 2
    assert all(row["est_fictif"] for row in experiment_results)

    assert client.delete(f"/api/research/participants/{participant_id}").status_code == 204
    assert client.get("/api/research/participants").json() == []
    assert client.delete(f"/api/research/experiments/{experiment['id']}").status_code == 409


def test_private_scientific_data_requires_researcher_session(anonymous_client):
    response = anonymous_client.get("/patients")
    assert response.status_code == 401
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
