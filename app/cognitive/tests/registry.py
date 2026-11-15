from app.cognitive.tests.base.test_cognitif import TestCognitif
from app.cognitive.tests.test_associatif import TestAssociatif
from app.cognitive.tests.test_fashion_mnist import TestFashionMnist
from app.cognitive.tests.test_memoire_visuelle import TestMemoireVisuelle
from app.cognitive.tests.test_rappel import TestRappel
from app.cognitive.tests.test_reconnaissance_visuelle import TestReconnaissanceVisuelle
from app.cognitive.tests.test_visuospatial import TestVisuospatial

TESTS_DISPONIBLES: dict[str, TestCognitif] = {
    test.type_test: test
    for test in (
        TestRappel(),
        TestVisuospatial(),
        TestReconnaissanceVisuelle(),
        TestMemoireVisuelle(),
        TestAssociatif(),
        TestFashionMnist(),
    )
}
