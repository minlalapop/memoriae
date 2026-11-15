from abc import ABC

from app.cognitive.tests.base.test_cognitif import TestCognitif


class TestQuiz(TestCognitif, ABC):
    """Spécialisation abstraite des protocoles déclaratifs ou à choix."""
