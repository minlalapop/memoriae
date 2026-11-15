from app import models


def test_future_research_structures_persist_without_test_logic(db_session):
    patient = models.Patient(nom="Sujet 001", consentement=True)
    config = models.ConfigurationExperience(
        nom="protocole-rappel", version="1.0", parametres={"seed": 42, "langue": "fr"}
    )
    db_session.add_all([patient, config])
    db_session.flush()
    session = models.SessionTest(patient_id=patient.id, configuration_id=config.id)
    session.reponses.append(
        models.ReponseSession(contenu="Réponse déclarée par le patient", temps_reponse_ms=1250)
    )
    db_session.add(session)
    db_session.commit()

    saved = db_session.get(models.ReponseSession, session.reponses[0].id)
    assert saved is not None
    assert saved.statut_verification == models.StatutVerification.NON_VERIFIE
    assert config.parametres["seed"] == 42

