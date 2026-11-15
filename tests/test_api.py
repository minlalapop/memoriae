def create_patient(client):
    response = client.post(
        "/patients",
        json={"nom": "Patiente recherche", "age": 72, "consentement": True},
    )
    assert response.status_code == 201
    return response.json()


def test_create_memory_is_never_automatically_verified(client):
    patient = create_patient(client)
    response = client.post(
        f"/patients/{patient['id']}/souvenirs",
        json={
            "description": "Promenade près du lac",
            "date_evenement": "2019-05-12",
            "provenance": "patient",
            "statut_verification": "declare",
            "elements": [{"type": "texte", "contenu": "Il faisait beau"}],
            "indices": [
                {"type": "lieu", "contenu": "lac", "score_pertinence": 0.8}
            ],
        },
    )
    assert response.status_code == 201
    memory = response.json()
    assert memory["statut_verification"] == "declare"
    assert memory["source_validation"] is None
    assert len(memory["elements"]) == 1
    assert len(memory["indices"]) == 1

    forbidden = client.post(
        f"/patients/{patient['id']}/souvenirs",
        json={
            "description": "Réponse du patient",
            "provenance": "patient",
            "statut_verification": "verifie",
        },
    )
    assert forbidden.status_code == 422


def test_explicit_validation_records_its_source(client):
    patient = create_patient(client)
    created = client.post(
        f"/patients/{patient['id']}/souvenirs",
        json={"description": "Anniversaire familial", "provenance": "proche"},
    ).json()

    response = client.post(
        f"/souvenirs/{created['id']}/validation",
        json={"source_validation": "Album familial daté, référence A-12"},
    )
    assert response.status_code == 200
    validated = response.json()
    assert validated["statut_verification"] == "verifie"
    assert validated["verified_at"] is not None
    assert validated["source_validation"].startswith("Album familial")

    updated = client.patch(
        f"/souvenirs/{created['id']}",
        json={"description": "Anniversaire familial confirmé"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"].endswith("confirmé")
    assert updated.json()["statut_verification"] == "verifie"


def test_unknown_patient_returns_404(client):
    response = client.get("/patients/inconnu/souvenirs")
    assert response.status_code == 404

