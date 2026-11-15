from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistance import (
    AucunIndiceError,
    EtatRecuperationError,
    RecuperationIntrouvableError,
    ServiceRecuperation,
)
from app.auth import require_researcher
from app.cognitive import ReponseInvalideError
from app.cognitive.patient import Patient
from app.memory import GestionnaireMemoire, PatientIntrouvableError, SouvenirIntrouvableError
from app.persistence import models as persistence_models
from app.persistence import schemas
from app.persistence.database import get_session
from app.research import (
    GestionnaireTests,
    SessionIntrouvableError,
    SoumissionInterditeError,
    TypeTestInconnuError,
    exporter_resultats,
)
from app.research.api import router as research_router

app = FastAPI(title="Memoriae", version="0.5.0")
FRONTEND_DIR = Path(__file__).parents[1] / "frontend"
STIMULI_DIR = Path(__file__).parent / "cognitive" / "stimuli"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount("/stimuli", StaticFiles(directory=STIMULI_DIR), name="stimuli")
app.include_router(research_router)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; object-src 'none'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'"
    )
    return response


@app.get("/", include_in_schema=False)
def laboratory_interface() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "index.html")


@app.get("/participer", include_in_schema=False)
def join_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "participer.html")


@app.get("/experience", include_in_schema=False)
def experiment_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "experience.html")


@app.get("/connexion", include_in_schema=False)
def login_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "connexion.html")


@app.get("/chercheur", include_in_schema=False)
def researcher_page(_researcher=Depends(require_researcher)) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "chercheur.html")


@app.get("/chercheur/resultats", include_in_schema=False)
def researcher_results_page(_researcher=Depends(require_researcher)) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "chercheur_resultats.html")


@app.get("/chercheur/modeles", include_in_schema=False)
def researcher_models_page(_researcher=Depends(require_researcher)) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "chercheur_modeles.html")


def memory_manager(session: Session = Depends(get_session)) -> GestionnaireMemoire:
    return GestionnaireMemoire(session)


def test_manager(session: Session = Depends(get_session)) -> GestionnaireTests:
    return GestionnaireTests(session)


def recovery_service(session: Session = Depends(get_session)) -> ServiceRecuperation:
    return ServiceRecuperation(session)


def experiment_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SessionIntrouvableError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, SoumissionInterditeError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


def recovery_error(exc: Exception) -> HTTPException:
    if isinstance(exc, RecuperationIntrouvableError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/patients", response_model=schemas.PatientRead, status_code=status.HTTP_201_CREATED,
          dependencies=[Depends(require_researcher)])
def create_patient(data: schemas.PatientCreate, session: Session = Depends(get_session)):
    patient = Patient(**data.model_dump())
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@app.get("/patients", response_model=list[schemas.PatientRead], dependencies=[Depends(require_researcher)])
def list_patients(session: Session = Depends(get_session)):
    return list(session.scalars(select(Patient).order_by(Patient.created_at)))


@app.get("/patients/{patient_id}", response_model=schemas.PatientRead, dependencies=[Depends(require_researcher)])
def get_patient(patient_id: str, session: Session = Depends(get_session)):
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    return patient


@app.patch("/patients/{patient_id}", response_model=schemas.PatientRead, dependencies=[Depends(require_researcher)])
def update_patient(
    patient_id: str, data: schemas.PatientUpdate, session: Session = Depends(get_session)
):
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    if patient.date_consentement is not None and not patient.consentement:
        raise HTTPException(status_code=422, detail="Consentement incohérent")
    session.commit()
    session.refresh(patient)
    return patient


@app.delete("/patients/{patient_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_researcher)])
def delete_patient(patient_id: str, session: Session = Depends(get_session)) -> Response:
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    if patient.sessions:
        raise HTTPException(
            status_code=409,
            detail="Ce patient possède des sessions de test et ne peut pas être supprimé",
        )
    session.delete(patient)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/patients/{patient_id}/souvenirs",
    response_model=schemas.SouvenirRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_researcher)],
)
def create_souvenir(
    patient_id: str,
    data: schemas.SouvenirCreate,
    manager: GestionnaireMemoire = Depends(memory_manager),
):
    try:
        return manager.ajouter_souvenir(patient_id, data)
    except PatientIntrouvableError as exc:
        raise HTTPException(status_code=404, detail="Patient introuvable") from exc


@app.get("/patients/{patient_id}/souvenirs", response_model=list[schemas.SouvenirRead], dependencies=[Depends(require_researcher)])
def list_souvenirs(
    patient_id: str, manager: GestionnaireMemoire = Depends(memory_manager)
):
    try:
        return manager.lister_souvenirs(patient_id)
    except PatientIntrouvableError as exc:
        raise HTTPException(status_code=404, detail="Patient introuvable") from exc


@app.get("/souvenirs/{souvenir_id}", response_model=schemas.SouvenirRead, dependencies=[Depends(require_researcher)])
def get_souvenir(
    souvenir_id: str, manager: GestionnaireMemoire = Depends(memory_manager)
):
    try:
        return manager.rechercher_souvenir(souvenir_id)
    except SouvenirIntrouvableError as exc:
        raise HTTPException(status_code=404, detail="Souvenir introuvable") from exc


@app.patch("/souvenirs/{souvenir_id}", response_model=schemas.SouvenirRead, dependencies=[Depends(require_researcher)])
def update_souvenir(
    souvenir_id: str,
    data: schemas.SouvenirUpdate,
    manager: GestionnaireMemoire = Depends(memory_manager),
):
    try:
        return manager.modifier_souvenir(souvenir_id, data)
    except SouvenirIntrouvableError as exc:
        raise HTTPException(status_code=404, detail="Souvenir introuvable") from exc


@app.delete("/souvenirs/{souvenir_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_researcher)])
def delete_souvenir(
    souvenir_id: str,
    manager: GestionnaireMemoire = Depends(memory_manager),
) -> Response:
    try:
        manager.supprimer_souvenir(souvenir_id)
    except SouvenirIntrouvableError as exc:
        raise HTTPException(status_code=404, detail="Souvenir introuvable") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/souvenirs/{souvenir_id}/validation", response_model=schemas.SouvenirRead, dependencies=[Depends(require_researcher)])
def validate_souvenir(
    souvenir_id: str,
    data: schemas.ValidationSouvenir,
    manager: GestionnaireMemoire = Depends(memory_manager),
):
    try:
        return manager.valider_souvenir(souvenir_id, data)
    except SouvenirIntrouvableError as exc:
        raise HTTPException(status_code=404, detail="Souvenir introuvable") from exc


@app.get("/tests-cognitifs")
def list_cognitive_tests(manager: GestionnaireTests = Depends(test_manager)):
    return manager.lister_tests()


@app.post(
    "/sessions-test",
    response_model=schemas.SessionTestRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_researcher)],
)
def start_test_session(
    data: schemas.SessionTestCreate,
    manager: GestionnaireTests = Depends(test_manager),
):
    try:
        return manager.demarrer(data)
    except (SessionIntrouvableError, TypeTestInconnuError, ReponseInvalideError) as exc:
        raise experiment_error(exc) from exc


@app.get(
    "/sessions-test/{session_id}/essai-courant",
    response_model=schemas.EssaiCourantRead,
    dependencies=[Depends(require_researcher)],
)
def get_current_trial(
    session_id: str,
    manager: GestionnaireTests = Depends(test_manager),
):
    try:
        essai = manager.essai_courant(session_id)
        if essai is None:
            raise SoumissionInterditeError("La session est terminée")
        return essai
    except (SessionIntrouvableError, SoumissionInterditeError) as exc:
        raise experiment_error(exc) from exc


@app.post(
    "/sessions-test/{session_id}/reponses",
    response_model=schemas.EvaluationEssaiRead,
    dependencies=[Depends(require_researcher)],
)
def submit_trial_response(
    session_id: str,
    data: schemas.SoumissionEssai,
    manager: GestionnaireTests = Depends(test_manager),
):
    try:
        session_test, reponse = manager.soumettre(session_id, data)
        terminee = session_test.statut == "terminee"
        return {
            "session_id": session_id,
            "essai_index": reponse.essai_index,
            "condition": reponse.condition,
            "score": reponse.score,
            "correcte": reponse.correcte,
            "mesures": reponse.mesures or {},
            "temps_reponse_ms": reponse.temps_reponse_ms,
            "session_terminee": terminee,
            "prochain_essai_index": None if terminee else session_test.essai_courant,
        }
    except (SessionIntrouvableError, SoumissionInterditeError, ReponseInvalideError) as exc:
        raise experiment_error(exc) from exc


@app.get(
    "/sessions-test/{session_id}/resultats",
    response_model=schemas.ResultatsSessionRead,
    dependencies=[Depends(require_researcher)],
)
def get_session_results(
    session_id: str,
    manager: GestionnaireTests = Depends(test_manager),
):
    try:
        return manager.resultats(session_id)
    except SessionIntrouvableError as exc:
        raise experiment_error(exc) from exc


@app.get(
    "/patients/{patient_id}/sessions-test",
    response_model=list[schemas.SessionTestRead],
    dependencies=[Depends(require_researcher)],
)
def list_test_sessions(patient_id: str, session: Session = Depends(get_session)):
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    query = (
        select(persistence_models.SessionTest)
        .where(persistence_models.SessionTest.patient_id == patient_id)
        .order_by(persistence_models.SessionTest.started_at.desc())
    )
    return list(session.scalars(query))


@app.get("/sessions-test/{session_id}/export/{format_export}", dependencies=[Depends(require_researcher)])
def export_session_results(
    session_id: str,
    format_export: str,
    session: Session = Depends(get_session),
):
    try:
        contenu, media_type = exporter_resultats(session, session_id, format_export)
    except SessionIntrouvableError as exc:
        raise experiment_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(
        content=contenu,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="session-{session_id}.{format_export}"'
        },
    )


@app.get(
    "/patients/{patient_id}/profil-cognitif",
    response_model=schemas.ProfilCognitifRead,
    dependencies=[Depends(require_researcher)],
)
def get_cognitive_profile(
    patient_id: str,
    manager: GestionnaireTests = Depends(test_manager),
):
    try:
        return manager.profil(patient_id)
    except SessionIntrouvableError as exc:
        raise experiment_error(exc) from exc


@app.post(
    "/patients/{patient_id}/recuperations",
    response_model=schemas.RecuperationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_researcher)],
)
def start_recovery(
    patient_id: str,
    data: schemas.RecuperationCreate,
    service: ServiceRecuperation = Depends(recovery_service),
):
    try:
        return service.demarrer(patient_id, data.souvenir_id)
    except RecuperationIntrouvableError as exc:
        raise recovery_error(exc) from exc


@app.get(
    "/patients/{patient_id}/recuperations/{session_id}/indice",
    response_model=schemas.IndiceRecuperationRead,
    dependencies=[Depends(require_researcher)],
)
def get_recovery_cue(
    patient_id: str,
    session_id: str,
    service: ServiceRecuperation = Depends(recovery_service),
):
    try:
        return service.obtenir_indice(patient_id, session_id)
    except (RecuperationIntrouvableError, EtatRecuperationError, AucunIndiceError) as exc:
        raise recovery_error(exc) from exc


@app.post(
    "/patients/{patient_id}/recuperations/{session_id}/feedback",
    response_model=schemas.FeedbackRecuperationRead,
    dependencies=[Depends(require_researcher)],
)
def submit_recovery_feedback(
    patient_id: str,
    session_id: str,
    data: schemas.FeedbackRecuperationCreate,
    service: ServiceRecuperation = Depends(recovery_service),
):
    try:
        tentative, candidat = service.enregistrer_feedback(
            patient_id,
            session_id,
            data.tentative_id,
            data.feedback,
            data.reponse_patient,
            data.souvenir_evoque,
        )
        return {
            "tentative_id": tentative.id,
            "feedback": tentative.feedback,
            "candidat_id": candidat.id if candidat else None,
        }
    except (RecuperationIntrouvableError, EtatRecuperationError) as exc:
        raise recovery_error(exc) from exc


@app.post(
    "/patients/{patient_id}/recuperations/{session_id}/terminer",
    response_model=schemas.HistoriqueRecuperationRead,
    dependencies=[Depends(require_researcher)],
)
def finish_recovery(
    patient_id: str,
    session_id: str,
    data: schemas.TerminaisonRecuperationCreate,
    service: ServiceRecuperation = Depends(recovery_service),
):
    try:
        return service.terminer(patient_id, session_id, data.resultat)
    except (RecuperationIntrouvableError, EtatRecuperationError) as exc:
        raise recovery_error(exc) from exc


@app.get(
    "/patients/{patient_id}/recuperations/{session_id}",
    response_model=schemas.HistoriqueRecuperationRead,
    dependencies=[Depends(require_researcher)],
)
def get_recovery_history(
    patient_id: str,
    session_id: str,
    service: ServiceRecuperation = Depends(recovery_service),
):
    try:
        return service.historique(patient_id, session_id)
    except RecuperationIntrouvableError as exc:
        raise recovery_error(exc) from exc


@app.get(
    "/patients/{patient_id}/recuperations/{session_id}/memoire-externe",
    response_model=schemas.MemoireExterneRead,
    dependencies=[Depends(require_researcher)],
)
def consult_external_memory(
    patient_id: str,
    session_id: str,
    service: ServiceRecuperation = Depends(recovery_service),
):
    try:
        return service.consulter_memoire_externe(patient_id, session_id)
    except RecuperationIntrouvableError as exc:
        raise recovery_error(exc) from exc

