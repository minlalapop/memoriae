import pytest

from app.cognitive import (
    TestJeu,
    TestMemoireVisuelle,
    TestQuiz,
    TestRappel,
    TestReconnaissanceVisuelle,
    TestVisuospatial,
)


@pytest.mark.parametrize(
    ("test", "parametres"),
    [
        (TestRappel(), {"nombre_items": 5}),
        (TestVisuospatial(), {"mode": "adaptatif", "maximum_essais": 6}),
        (
            TestReconnaissanceVisuelle(),
            {"mode": "fixe", "difficulte": "moyen", "nombre_propositions": 4},
        ),
    ],
)
def test_generation_is_reproducible_with_fixed_seed(test, parametres):
    assert test.generer_essais(1234, parametres) == test.generer_essais(1234, parametres)


def test_protocols_follow_quiz_and_game_abstractions():
    assert isinstance(TestRappel(), TestQuiz)
    assert isinstance(TestReconnaissanceVisuelle(), TestQuiz)
    assert isinstance(TestMemoireVisuelle(), TestQuiz)
    assert isinstance(TestVisuospatial(), TestJeu)


def test_scores_are_deterministic_and_explicit():
    rappel = TestRappel()
    essais_rappel = rappel.generer_essais(7, {"nombre_items": 4})
    attendus = essais_rappel[1]["attendu"]["items"]
    resultat_rappel = rappel.evaluer(
        essais_rappel[1], {"items": [attendus[0], attendus[1], "intrus"]}
    )
    assert resultat_rappel.score == 0.5
    assert resultat_rappel.mesures == {"items_corrects": 2, "total": 4}

    visuospatial = TestVisuospatial()
    essai_spatial = visuospatial.generer_bloc(
        9, 1, 0, visuospatial.parametres_defaut
    )[1]
    positions = essai_spatial["attendu"]["positions"]
    resultat_spatial = visuospatial.evaluer(
        essai_spatial, {"positions": [positions[0], positions[2], positions[1]]}
    )
    assert resultat_spatial.score == pytest.approx(1 / 3)
    assert resultat_spatial.mesures["positions_presentes"] == 3
    assert resultat_spatial.mesures["ordre_exact"] is False

    visuel = TestReconnaissanceVisuelle()
    essai_visuel = visuel.generer_essais(
        11, {"mode": "adaptatif", "nombre_propositions": 4}
    )[1]
    resultat_visuel = visuel.evaluer(
        essai_visuel, {"choix": essai_visuel["attendu"]["choix"]}
    )
    assert resultat_visuel.score == 1.0
    assert resultat_visuel.correcte is True

    images = TestMemoireVisuelle()
    essai_images = images.generer_essais(19, images.parametres_defaut)[1]
    resultat_images = images.evaluer(essai_images, essai_images["attendu"])
    assert resultat_images.score == 1.0
    assert resultat_images.mesures["nombre_cibles"] == 1
    assert essai_images["stimulus"]["stimuli_version"] == "memoriae-objets-v1"
    assert all(
        proposition["src"].startswith("/stimuli/objets/")
        for proposition in essai_images["stimulus"]["propositions"]
    )


def test_visual_pattern_difficulty_changes_symbols_and_distractors():
    test = TestReconnaissanceVisuelle()
    easy = test.generer_essais(
        31, {**test.parametres_defaut, "difficulte": "facile"}
    )
    hard = test.generer_essais(
        31, {**test.parametres_defaut, "difficulte": "difficile"}
    )
    easy_symbols = [symbol for row in easy[0]["stimulus"]["matrice"] for symbol in row if symbol]
    hard_symbols = [symbol for row in hard[0]["stimulus"]["matrice"] for symbol in row if symbol]
    assert len(easy_symbols) == 1
    assert len(hard_symbols) == 2
    assert set(easy_symbols) <= set(test._symboles_par_difficulte["facile"])
    assert all(
        sum(bool(symbol) for row in option for symbol in row) == 1
        for option in easy[1]["stimulus"]["propositions"]
    )

