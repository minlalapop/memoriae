from app import models
from app.auth import hash_password


def _configure_researcher(monkeypatch):
    monkeypatch.setenv("MEMORIAE_RESEARCHER_USERNAME", "chercheur")
    monkeypatch.setenv(
        "MEMORIAE_RESEARCHER_PASSWORD_HASH",
        hash_password("mot-de-passe-recherche", salt=b"0123456789abcdef"),
    )


def test_complete_researcher_participant_experiment_path(
    anonymous_client, db_session, monkeypatch
):
    client = anonymous_client
    _configure_researcher(monkeypatch)
    assert client.get("/api/research/experiments").status_code == 401
    assert client.get("/chercheur").status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"username": "chercheur", "password": "incorrect"},
    ).status_code == 401

    login = client.post(
        "/api/auth/login",
        json={
            "username": "chercheur",
            "password": "mot-de-passe-recherche",
        },
    )
    assert login.status_code == 200
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "SameSite=lax" in login.headers["set-cookie"]
    assert client.get("/chercheur").status_code == 200

    created = client.post(
        "/api/research/experiments",
        json={
            "nom": "Associations sémantiques",
            "test_type": "associatif",
            "seed_base": 700,
            "parametres": {
                "nombre_items": 3,
                "nombre_options": 2,
                "duree_presentation_ms": 2000,
            },
        },
    )
    assert created.status_code == 201
    experiment = created.json()
    assert experiment["code"].startswith("MEM-")

    assert client.post(
        "/api/experiments/join",
        json={"code": "CODE-INVALIDE", "consentement": True},
    ).status_code == 404
    assert client.post(
        "/api/experiments/join",
        json={"code": experiment["code"], "consentement": False},
    ).status_code == 422

    joined = client.post(
        "/api/experiments/join",
        json={"code": experiment["code"].lower(), "consentement": True},
    )
    assert joined.status_code == 201
    session_id = joined.json()["session_id"]
    assert joined.json()["pseudonyme"].startswith("P-")
    assert "memoriae_participant" in joined.headers["set-cookie"]

    manipulated = client.get("/api/sessions/session-inconnue/next")
    assert manipulated.status_code == 403

    first = client.get(f"/api/sessions/{session_id}/next")
    assert first.status_code == 200
    assert "attendu" not in first.text
    trial = first.json()["essai"]
    submitted = client.post(
        f"/api/sessions/{session_id}/responses",
        json={"essai_index": trial["essai_index"], "reponse": {"continue": True}},
    )
    assert submitted.status_code == 200
    repeated = client.post(
        f"/api/sessions/{session_id}/responses",
        json={"essai_index": trial["essai_index"], "reponse": {"continue": True}},
    )
    assert repeated.status_code == 409

    while True:
        current = client.get(f"/api/sessions/{session_id}/next").json()
        if current["terminee"]:
            break
        db_session.expire_all()
        stored = db_session.get(models.SessionTest, session_id)
        expected = stored.essais[current["essai"]["essai_index"]]["attendu"]
        response = client.post(
            f"/api/sessions/{session_id}/responses",
            json={
                "essai_index": current["essai"]["essai_index"],
                "reponse": expected,
                "temps_reponse_ms": 850,
            },
        )
        assert response.status_code == 200

    finished = client.post(f"/api/sessions/{session_id}/finish", json={})
    assert finished.status_code == 200
    results = client.get("/api/research/results")
    assert results.status_code == 200
    assert results.json()[0]["score"] == 1.0
    detail = client.get(f"/api/research/results/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["type_test"] == "associatif"
    export = client.get("/api/research/export")
    assert export.status_code == 200
    assert "reconnaissance_indicee" in export.text

    assert client.post("/api/auth/logout", json={}).status_code == 204
    assert client.get("/api/research/results").status_code == 401
    assert client.get("/chercheur/resultats").status_code == 401


def test_associative_protocol_is_reproducible_and_records_cue_type():
    from app.cognitive import TestAssociatif

    test = TestAssociatif()
    parameters = {
        "nombre_items": 4,
        "nombre_options": 3,
        "duree_presentation_ms": 3000,
    }
    first = test.generer_essais(91, parameters)
    assert first == test.generer_essais(91, parameters)
    assert first[1]["condition"] == "reconnaissance_indicee"
    result = test.evaluer(first[1], first[1]["attendu"])
    assert result.score == 1.0
    assert result.mesures["type_indice"] == "semantique"
    assert result.mesures["strategie_indice"] == "regles"
