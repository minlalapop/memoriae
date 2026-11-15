def _create_patient(client, name):
    response = client.post("/patients", json={"nom": name, "consentement": True})
    assert response.status_code == 201
    return response.json()


def test_laboratory_interface_and_assets_are_served(anonymous_client):
    client = anonymous_client
    page = client.get("/")
    assert page.status_code == 200
    assert "Expériences sur la mémoire humaine" in page.text
    assert client.get("/participer").status_code == 200
    assert client.get("/experience").status_code == 200
    assert client.get("/connexion").status_code == 200
    assert client.get("/chercheur").status_code == 401
    assert client.get("/chercheur/resultats").status_code == 401
    assert client.get("/chercheur/modeles").status_code == 401
    assert client.get("/static/css/base.css").status_code == 200
    assert client.get("/static/css/forms.css").status_code == 200
    assert client.get("/static/css/tests.css").status_code == 200
    script = client.get("/static/js/experience.js")
    assert script.status_code == 200
    assert "temps_reponse_ms:presentation ? null" in script.text
    grid_script = client.get("/static/js/tests/visuospatial.js").text
    pattern_script = client.get("/static/js/tests/motifs.js").text
    assert "grid-columns-" in grid_script
    assert "grid-columns-" in pattern_script
    assert 'style="grid-template-columns' not in grid_script
    assert 'style="grid-template-columns' not in pattern_script
    for module in (
        "api.js",
        "app.js",
        "participant.js",
        "connexion.js",
        "chercheur.js",
        "chercheur_resultats.js",
        "chercheur_modeles.js",
        "tests/associatif.js",
        "tests/rappel.js",
        "tests/visuospatial.js",
        "tests/motifs.js",
        "tests/images.js",
        "tests/fashion.js",
    ):
        assert client.get(f"/static/js/{module}").status_code == 200
    image = client.get("/stimuli/objets/01_pomme.png")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"


def test_patient_test_sessions_can_be_listed_without_exposing_other_patients(client):
    first = _create_patient(client, "Sujet WEB-001")
    second = _create_patient(client, "Sujet WEB-002")
    started = client.post(
        "/sessions-test",
        json={
            "patient_id": first["id"],
            "protocole": "interface-web-test",
            "type_test": "visuospatial",
            "seed": 17,
            "parametres": {
                "mode": "fixe",
                "nombre_essais": 3,
                "difficulte": "facile",
            },
        },
    )
    assert started.status_code == 201

    first_sessions = client.get(f"/patients/{first['id']}/sessions-test")
    second_sessions = client.get(f"/patients/{second['id']}/sessions-test")
    assert first_sessions.status_code == 200
    assert [session["id"] for session in first_sessions.json()] == [started.json()["id"]]
    assert second_sessions.status_code == 200
    assert second_sessions.json() == []
