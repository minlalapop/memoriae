"""Protocoles cognitifs expérimentaux."""

from app.cognitive.tests.base import TestCognitif, TestJeu, TestQuiz
from app.cognitive.tests.registry import TESTS_DISPONIBLES
from app.cognitive.tests.test_associatif import TestAssociatif
from app.cognitive.tests.test_fashion_mnist import TestFashionMnist
from app.cognitive.tests.test_memoire_visuelle import TestMemoireVisuelle
from app.cognitive.tests.test_rappel import TestRappel
from app.cognitive.tests.test_reconnaissance_visuelle import TestReconnaissanceVisuelle
from app.cognitive.tests.test_visuospatial import TestVisuospatial

__all__ = [
    "TESTS_DISPONIBLES",
    "TestCognitif",
    "TestAssociatif",
    "TestFashionMnist",
    "TestJeu",
    "TestMemoireVisuelle",
    "TestQuiz",
    "TestRappel",
    "TestReconnaissanceVisuelle",
    "TestVisuospatial",
]
