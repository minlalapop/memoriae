from inspect import isabstract

import pytest

from app.assistance import (
    ActiviteAssistance,
    MoteurAdaptation,
    SelecteurIndices,
    ServiceRecuperation,
)
from app.cognitive import (
    AnalyseCognitive,
    Patient,
    ProfilCognitif,
    ResultatTest,
    TestCognitif,
    TestJeu,
    TestQuiz,
    TestRappel,
    TestReconnaissanceVisuelle,
    TestVisuospatial,
)
from app.memory import (
    ElementMemoire,
    GestionnaireMemoire,
    Indice,
    MemoireExterne,
    MemoryModel,
    Souvenir,
)
from app.memory.models.hopfield import HopfieldNetwork
from app.research import GestionnaireTests, ProtocoleEvaluation
from app.simulation import ModeleMemoireAltere, PatientVirtuel, SimulateurDeficits


def test_classes_majeures_ont_des_modules_dedies():
    classes = {
        Patient: "app.cognitive.patient",
        Souvenir: "app.memory.external.souvenir",
        ElementMemoire: "app.memory.external.element_memoire",
        Indice: "app.memory.external.indice",
        MemoireExterne: "app.memory.external.memoire_externe",
        ResultatTest: "app.cognitive.assessment.resultat_test",
        ProfilCognitif: "app.cognitive.assessment.profil_cognitif",
        AnalyseCognitive: "app.cognitive.assessment.analyse_cognitive",
        MoteurAdaptation: "app.assistance.adaptation.moteur_adaptation",
        SelecteurIndices: "app.assistance.retrieval.selecteur_indices",
        ServiceRecuperation: "app.assistance.retrieval.service_recuperation",
        ActiviteAssistance: "app.assistance.activities.activite_assistance",
        MemoryModel: "app.memory.models.memory_model",
        HopfieldNetwork: "app.memory.models.hopfield.hopfield_network",
        GestionnaireMemoire: "app.memory.external.gestionnaire_memoire",
        GestionnaireTests: "app.research.experiments.gestionnaire_tests",
        ProtocoleEvaluation: "app.research.protocols.protocole_evaluation",
        PatientVirtuel: "app.simulation.agents.patient_virtuel",
        SimulateurDeficits: "app.simulation.impairments.simulateur_deficits",
        ModeleMemoireAltere: "app.simulation.models.modele_memoire_altere",
    }
    assert {classe.__module__: module for classe, module in classes.items()} == {
        module: module for module in classes.values()
    }


def test_hierarchie_cognitive_uml_est_effective():
    assert isabstract(TestCognitif)
    assert isabstract(TestQuiz)
    assert isabstract(TestJeu)
    assert issubclass(TestRappel, TestQuiz)
    assert issubclass(TestReconnaissanceVisuelle, TestQuiz)
    assert issubclass(TestVisuospatial, TestJeu)


def test_extensions_futures_ne_simulent_aucun_algorithme():
    appels = [
        lambda: HopfieldNetwork().encode([]),
        lambda: ActiviteAssistance().generer_activite({}),
        lambda: ProtocoleEvaluation().executer({}),
        lambda: PatientVirtuel().repondre(None),
        lambda: SimulateurDeficits().appliquer(None),
        lambda: ModeleMemoireAltere().retrieve(None),
    ]
    for appel in appels:
        with pytest.raises(NotImplementedError):
            appel()
