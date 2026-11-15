from demo import executer_demo


def test_complete_synthetic_research_path_is_persistent_and_reproducible():
    summary = executer_demo(afficher=False)

    assert summary["donnees"] == "entièrement synthétiques"
    assert len(summary["tests"]) == 2
    assert {test["seed"] for test in summary["tests"]} == {101, 202}
    assert all(test["version"] == "2.0" for test in summary["tests"])
    assert summary["profil_descriptif"]["rappel"]["conditions"]["rappel_indice"][
        "score_moyen"
    ] == 1.0
    assert summary["recuperation"]["strategie"] == "indices_categoriels"
    assert summary["recuperation"]["resultat"] == "retrouve"
    assert len(summary["recuperation"]["indices"]) == 3
    assert summary["memoire_externe"]["statut"] == "verifie"
    assert summary["reproductibilite"] == {
        "stimuli_regeneres_identiques": True,
        "sessions_retrouvees": 2,
        "parametres_et_seeds_persistes": True,
    }
