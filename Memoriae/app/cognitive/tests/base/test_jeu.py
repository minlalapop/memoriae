from abc import ABC

from app.cognitive.tests.base.test_cognitif import TestCognitif


class TestJeu(TestCognitif, ABC):
    """Spécialisation abstraite des protocoles à interaction ordonnée."""
