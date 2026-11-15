"""Démonstration synthétique et non clinique du prototype Memoriae."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.assistance import ServiceRecuperation
from app.cognitive import TESTS_DISPONIBLES
from app.database import build_engine, init_db
from app.experiments import GestionnaireTests
from app.services import GestionnaireMemoire


def executer_demo(*, afficher: bool = True) -> dict[str, Any]:
    with TemporaryDirectory(prefix="memoriae-demo-") as dossier:
        chemin_db = Path(dossier) / "demo.db"
        moteur = build_engine(f"sqlite:///{chemin_db}")
        init_db(moteur)
        sessions = sessionmaker(bind=moteur, expire_on_commit=False)

        with sessions() as db:
            patient = models.Patient(
                nom="[SYNTHÉTIQUE] Sujet DEMO-001",
                age=70,
                consentement=True,
            )
            db.add(patient)
            db.commit()
            patient_id = patient.id

            memoire = GestionnaireMemoire(db)
            cible = memoire.ajouter_souvenir(
                patient_id,
                schemas.SouvenirCreate(
                    description="Pique-nique familial fictif au bord du lac",
                    date_evenement="2024-05-12",
                    provenance=models.ProvenanceSouvenir.DOCUMENT,
                    details_provenance="Album synthétique DEMO-A",
                    statut_verification=models.StatutVerification.DECLARE,
                    elements=[
                        schemas.ElementCreate(
                            type=models.TypeElement.TEXTE,
                            contenu="Panier rouge et nappe bleue — donnée synthétique",
                        )
                    ],
                    indices=[
                        schemas.IndiceCreate(
                            type="catégorie",
                            contenu="Une activité familiale extérieure",
                            score_pertinence=0.3,
                        ),
                        schemas.IndiceCreate(
                            type="texte",
                            contenu="Le lieu se trouvait près de l'eau",
                            score_pertinence=0.6,
                        ),
                        schemas.IndiceCreate(
                            type="visuel",
                            contenu="Référence à un panier rouge",
                            score_pertinence=0.9,
                        ),
                    ],
                ),
            )
            memoire.valider_souvenir(
                cible.id,
                schemas.ValidationSouvenir(
                    source_validation="Document synthétique DEMO-A, contrôlé pour la démonstration"
                ),
            )
            secondaire = memoire.ajouter_souvenir(
                patient_id,
                schemas.SouvenirCreate(
                    description="Promenade fictive dans un jardin",
                    provenance=models.ProvenanceSouvenir.PATIENT,
                    statut_verification=models.StatutVerification.DECLARE,
                    indices=[
                        schemas.IndiceCreate(
                            type="texte", contenu="Un espace avec des fleurs", score_pertinence=0.5
                        )
                    ],
                ),
            )
            cible_id = cible.id
            secondaire_id = secondaire.id

            gestion_tests = GestionnaireTests(db)
            session_ids: list[str] = []
            for seed in (101, 202):
                session_test = gestion_tests.demarrer(
                    schemas.SessionTestCreate(
                        patient_id=patient_id,
                        protocole="demo-synthetique-rappel",
                        type_test="rappel",
                        seed=seed,
                        parametres={"nombre_items": 3},
                    )
                )
                session_ids.append(session_test.id)
                reponses_scenarisees = [
                    {"continue": True},
                    {"items": []},
                    {"reponses": session_test.essais[2]["attendu"]["reponses"]},
                    {"items": session_test.essais[3]["attendu"]["items"]},
                ]
                for index, reponse in enumerate(reponses_scenarisees):
                    gestion_tests.soumettre(
                        session_test.id,
                        schemas.SoumissionEssai(essai_index=index, reponse=reponse),
                    )

        # Une nouvelle session SQLAlchemy vérifie la persistance avant l'assistance.
        with sessions() as db:
            gestion_tests = GestionnaireTests(db)
            resultats = [gestion_tests.resultats(session_id) for session_id in session_ids]
            profil = gestion_tests.profil(patient_id)
            stimuli_reproductibles = all(
                db.get(models.SessionTest, session_id).essais
                == TESTS_DISPONIBLES["rappel"].generer_essais(
                    resultat["seed"], {"nombre_items": 3}
                )
                for session_id, resultat in zip(session_ids, resultats)
            )

            recuperation = ServiceRecuperation(db)
            session_recuperation = recuperation.demarrer(patient_id, cible_id)
            recuperation_id = session_recuperation.id
            strategie = session_recuperation.strategie
            justification = session_recuperation.justification_strategie

            premier = recuperation.obtenir_indice(patient_id, recuperation_id)
            recuperation.enregistrer_feedback(
                patient_id,
                recuperation_id,
                premier.id,
                models.FeedbackRecuperation.NON_RETROUVE,
                "Réponse synthétique : aucun rappel.",
                None,
            )

        # La reprise dans une troisième session démontre la continuité de la récupération.
        with sessions() as db:
            recuperation = ServiceRecuperation(db)
            deuxieme = recuperation.obtenir_indice(patient_id, recuperation_id)
            recuperation.enregistrer_feedback(
                patient_id,
                recuperation_id,
                deuxieme.id,
                models.FeedbackRecuperation.NON_RETROUVE,
                "Réponse synthétique : évocation partielle seulement.",
                None,
            )
            troisieme = recuperation.obtenir_indice(patient_id, recuperation_id)
            recuperation.enregistrer_feedback(
                patient_id,
                recuperation_id,
                troisieme.id,
                models.FeedbackRecuperation.RETROUVE,
                "Réponse synthétique : souvenir déclaré retrouvé.",
                None,
            )
            historique = recuperation.terminer(
                patient_id, recuperation_id, models.ResultatRecuperation.RETROUVE
            )
            memoire_externe = recuperation.consulter_memoire_externe(
                patient_id, recuperation_id
            )

            resume = {
                "donnees": "entièrement synthétiques",
                "patient": "[SYNTHÉTIQUE] Sujet DEMO-001",
                "souvenirs": {
                    "nombre": 2,
                    "verifie": cible_id,
                    "non_verifie": secondaire_id,
                },
                "tests": [
                    {
                        "seed": resultat["seed"],
                        "protocole": resultat["protocole"],
                        "version": resultat["version"],
                        "scores": {
                            item["condition"]: item["score"]
                            for item in resultat["resultats"]
                            if item["score"] is not None
                        },
                    }
                    for resultat in resultats
                ],
                "profil_descriptif": profil["performances"],
                "recuperation": {
                    "strategie": strategie,
                    "justification": justification,
                    "indices": [
                        {
                            "ordre": tentative["ordre"],
                            "type": tentative["indice_type"],
                            "niveau_aide": tentative["niveau_aide"],
                            "feedback": tentative["feedback"],
                        }
                        for tentative in historique["tentatives"]
                    ],
                    "resultat": historique["resultat_final"],
                },
                "memoire_externe": {
                    "statut": memoire_externe["statut_verification"],
                    "provenance": memoire_externe["provenance"],
                    "presentation_comme_fait_verifie": memoire_externe[
                        "presentation_comme_fait_verifie"
                    ],
                },
                "reproductibilite": {
                    "stimuli_regeneres_identiques": stimuli_reproductibles,
                    "sessions_retrouvees": len(resultats),
                    "parametres_et_seeds_persistes": all(
                        resultat["parametres"].get("seed") == resultat["seed"]
                        for resultat in resultats
                    ),
                },
                "avertissement": (
                    "Scénario logiciel fictif; aucune conclusion cognitive, médicale ou clinique."
                ),
            }

        moteur.dispose()

    if afficher:
        print("=== Démonstration Memoriae — données synthétiques ===")
        print(json.dumps(resume, ensure_ascii=False, indent=2, default=str))
        print("Base SQLite temporaire supprimée après la démonstration.")
    return resume


if __name__ == "__main__":
    executer_demo()
