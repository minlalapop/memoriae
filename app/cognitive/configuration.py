from typing import Any

VERSION_PROTOCOLLES = "2.0"

PARAMETRES_PROTOCOLLES: dict[str, dict[str, Any]] = {
    "rappel": {"nombre_items": 4, "difficulte_mots": "facile"},
    "visuospatial": {
        "mode": "adaptatif",
        "difficulte": "facile",
        "nombre_essais": 5,
        "maximum_essais": 8,
    },
    "reconnaissance_visuelle": {
        "mode": "adaptatif",
        "difficulte": "facile",
        "nombre_essais": 5,
        "maximum_essais": 8,
        "nombre_propositions": 4,
    },
    "memoire_visuelle": {
        "mode": "adaptatif",
        "difficulte": "facile",
        "nombre_essais": 5,
        "maximum_essais": 8,
    },
    "associatif": {
        "nombre_items": 4,
        "nombre_options": 3,
        "duree_presentation_ms": 5000,
    },
    "fashion_mnist_partiel": {
        "nombre_images": 12,
        "essais_par_niveau": 4,
        "niveaux_masquage": [0.25, 0.5, 0.75],
        "duree_presentation_ms": 8000,
        "mask_side": "right",
    },
}
