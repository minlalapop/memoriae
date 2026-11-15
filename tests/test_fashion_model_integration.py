import pytest

from app.cognitive.tests.test_fashion_mnist import TestFashionMnist


class _FakeMemoriaeV2:
    version = "2.0"
    beta = 1000.0
    latent_dim = 64
    checkpoint_memories = 128
    checkpoint_sha256 = "test-checkpoint"

    def run_protocol(self, images, trials):
        identifiers = {identifier for identifier, _ in images}
        results = []
        for trial in trials:
            assert trial["target_id"] in identifiers
            assert trial["target_id"] in trial["candidate_ids"]
            assert len(trial["candidate_ids"]) == 4
            results.append(
                {
                    "stimulus_id": trial["target_id"],
                    "predicted_stimulus_id": trial["target_id"],
                    "correct": True,
                    "mse": 0.0125,
                    "reconstruction_png_base64": "fake-png",
                    "mask_ratio": trial["mask_ratio"],
                    "mask_side": trial["mask_side"],
                    "trial_order": trial["trial_order"],
                    "candidate_ids": trial["candidate_ids"],
                    "beta": self.beta,
                    "memory_size": len(images),
                }
            )
        return results


def test_fashion_protocol_is_reproducible_and_hides_expected_answer():
    test = TestFashionMnist()
    first = test.generer_essais(91, test.parametres_defaut)
    second = test.generer_essais(91, test.parametres_defaut)
    assert first == second
    assert len(first[0]["stimulus"]["images"]) == 12
    assert len(first) == 13
    ratios = [trial["stimulus"]["mask_ratio"] for trial in first[1:]]
    assert {ratio: ratios.count(ratio) for ratio in set(ratios)} == {
        0.25: 4,
        0.5: 4,
        0.75: 4,
    }
    assert len({trial["attendu"]["choix"] for trial in first[1:]}) == 12
    for order, trial in enumerate(first[1:], start=1):
        assert trial["stimulus"]["mask_side"] == "right"
        assert trial["stimulus"]["trial_order"] == order
        assert "attendu" not in trial["stimulus"]
        assert "id" not in trial["stimulus"]["image_partielle"]
        assert len(trial["stimulus"]["propositions"]) == 4
        assert trial["attendu"]["choix"] in {
            image["id"] for image in trial["stimulus"]["propositions"]
        }


def test_model_and_completed_researcher_participant_are_compared(
    client, db_session, monkeypatch
):
    from app import models
    from app.research.experiments import model_execution

    monkeypatch.setattr(model_execution, "memoriae_v2", lambda: _FakeMemoriaeV2())
    created = client.post(
        "/api/research/experiments",
        json={
            "nom": "Images partielles",
            "seed_base": 42,
            "etapes": [
                {
                    "test_type": "fashion_mnist_partiel",
                    "parametres": TestFashionMnist.parametres_defaut,
                    "seed_offset": 0,
                }
            ],
        },
    )
    assert created.status_code == 201
    experiment = created.json()
    compatible = client.get("/api/research/models/memoriae_v2/experiments")
    assert [item["id"] for item in compatible.json()] == [experiment["id"]]

    executed = client.post(
        "/api/research/models/memoriae_v2/execute",
        json={"experiment_id": experiment["id"]},
    )
    assert executed.status_code == 201
    result = executed.json()
    assert result["accuracy"] == 1.0
    assert result["mse"] == pytest.approx(0.0125)
    assert result["nombre_essais"] == 12
    assert result["configuration"]["steps"][0]["stimulus_ids"]
    before_human = client.get(
        f"/api/research/experiments/{experiment['id']}/comparison"
    ).json()
    assert before_human["human"]["status"] == "Données insuffisantes"
    assert before_human["human"]["accuracy"] is None
    participant = client.post(
        "/api/research/participants",
        json={"nom": "Modele", "prenom": "Participant", "age": 40},
    )
    assert participant.status_code == 201
    launched = client.post(
        f"/api/research/experiments/{experiment['id']}/launch",
        json={"patient_id": participant.json()["id"]},
    )
    assert launched.status_code == 201
    human_session = db_session.get(models.SessionTest, launched.json()["session_id"])
    human_ids = [image["id"] for image in human_session.essais[0]["stimulus"]["images"]]
    assert human_ids == result["configuration"]["steps"][0]["stimulus_ids"]
    session_id = human_session.id
    while True:
        current = client.get(f"/api/sessions/{session_id}/next").json()
        if current["terminee"]:
            break
        trial = current["essai"]
        expected = human_session.essais[trial["essai_index"]]["attendu"]
        answer = {"continue": True} if expected is None else expected
        submitted = client.post(
            f"/api/sessions/{session_id}/responses",
            json={"essai_index": trial["essai_index"], "reponse": answer},
        )
        assert submitted.status_code == 200
    assert client.post(f"/api/sessions/{session_id}/finish").status_code == 200
    comparison = client.get(
        f"/api/research/experiments/{experiment['id']}/comparison"
    )
    assert comparison.status_code == 200
    assert comparison.json()["human"] == {
        "participants": 1,
        "trials": 12,
        "accuracy": 1.0,
        "status": "disponible",
        "by_mask": {
            "0.25": {"trials": 4, "accuracy": 1.0},
            "0.5": {"trials": 4, "accuracy": 1.0},
            "0.75": {"trials": 4, "accuracy": 1.0},
        },
    }
    assert comparison.json()["model"]["accuracy"] == 1.0
