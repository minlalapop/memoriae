from app.cognitive.adaptation import ParametresAdaptatifs, StrategieAdaptative


def test_high_performance_increases_difficulty_until_maximum():
    strategy = StrategieAdaptative(ParametresAdaptatifs(maximum_essais=4))
    first = strategy.decider([0.9], 0)
    last = strategy.decider([0.9, 1.0, 0.8, 0.9], 3)
    assert first.continuer is True
    assert first.action == "continuer_augmenter"
    assert first.niveau_suivant == 1
    assert last.continuer is False
    assert last.action == "arreter_maximum"


def test_single_error_does_not_stop_test():
    decision = StrategieAdaptative().decider([1.0, 0.2], 1)
    assert decision.continuer is True
    assert decision.action == "continuer_reduire"


def test_persistent_task_decline_stops_after_several_low_trials():
    strategy = StrategieAdaptative()
    before = strategy.decider([1.0, 0.9, 0.4], 2)
    decline = strategy.decider([1.0, 0.9, 0.4, 0.3], 1)
    assert before.continuer is True
    assert decline.continuer is False
    assert decline.action == "arreter_baisse_persistante_tache"


def test_intermediate_performance_keeps_same_level():
    decision = StrategieAdaptative().decider([0.6], 2)
    assert decision.continuer is True
    assert decision.action == "continuer_maintenir"
    assert decision.niveau_suivant == 2


def test_fixed_trajectory_stops_at_requested_count():
    strategy = StrategieAdaptative()
    ongoing = strategy.decider([1.0, 0.0], 1, mode="fixe", nombre_essais_fixe=3)
    finished = strategy.decider(
        [1.0, 0.0, 0.5], 2, mode="fixe", nombre_essais_fixe=3
    )
    assert ongoing.action == "continuer_fixe"
    assert finished.continuer is False
    assert finished.action == "arreter_nombre_fixe"
