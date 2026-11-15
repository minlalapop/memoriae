from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import secrets
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth.service import (
    COOKIE_RESEARCHER,
    create_researcher_session,
    delete_researcher_session,
    require_researcher,
    verify_researcher_credentials,
)
from app.cognitive import TESTS_DISPONIBLES, ReponseInvalideError
from app.cognitive.patient import Patient
from app.memory.models.memoriae_v2 import ModelUnavailableError, model_status
from app.persistence import models, schemas
from app.persistence.database import get_session, utc_now
from app.research.experiments.gestionnaire_tests import (
    GestionnaireTests,
    SoumissionInterditeError,
)
from app.research.experiments.model_execution import (
    comparison_payload,
    execute_memoriae_v2,
    execution_payload,
)

router = APIRouter()
COOKIE_PARTICIPANT = "memoriae_participant"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=500)


class ExperienceStepInput(BaseModel):
    test_type: str = Field(min_length=1, max_length=50)
    parametres: dict[str, Any] = Field(default_factory=dict)
    seed_offset: int = 0


class ExperienceCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    etapes: list[ExperienceStepInput] = Field(default_factory=list, max_length=20)
    test_type: str | None = Field(default=None, min_length=1, max_length=50)
    parametres: dict[str, Any] = Field(default_factory=dict)
    seed_base: int = 0
    active: bool = True

    @model_validator(mode="after")
    def at_least_one_step(self):
        if not self.etapes and not self.test_type:
            raise ValueError("Ajoutez au moins un test")
        return self


class ExperienceUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    etapes: list[ExperienceStepInput] | None = Field(default=None, min_length=1, max_length=20)
    parametres: dict[str, Any] | None = None
    seed_base: int | None = None
    active: bool | None = None


class JoinRequest(BaseModel):
    code: str = Field(min_length=3, max_length=20)
    consentement: bool


class ParticipantFictifCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=200)
    prenom: str | None = Field(default=None, max_length=200)
    age: int | None = Field(default=None, ge=0, le=130)


class ParticipantFictifUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=200)
    prenom: str | None = Field(default=None, max_length=200)
    age: int | None = Field(default=None, ge=0, le=130)


class LaunchRequest(BaseModel):
    patient_id: str


class ModelExecutionRequest(BaseModel):
    experiment_id: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _secure_cookie() -> bool:
    return os.getenv("MEMORIAE_ENV", "development").casefold() == "production"


def _experience_payload(experience: models.Experience) -> dict[str, Any]:
    steps = experience.etapes or []
    return {
        "id": experience.id,
        "nom": experience.nom,
        "description": experience.description,
        "code": experience.code,
        "test_type": experience.test_type,
        "protocol_version": experience.protocol_version,
        "parametres": experience.parametres,
        "seed_base": experience.seed_base,
        "active": experience.active,
        "etapes": [
            {
                "id": step.id,
                "position": step.position,
                "test_type": step.test_type,
                "parametres": step.parametres,
                "seed_offset": step.seed_offset,
            }
            for step in steps
        ],
        "created_at": experience.created_at,
        "updated_at": experience.updated_at,
    }


def _new_experiment_code(session: Session) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(20):
        code = "MEM-" + "".join(secrets.choice(alphabet) for _ in range(6))
        if session.scalar(select(models.Experience.id).where(models.Experience.code == code)) is None:
            return code
    raise HTTPException(status_code=503, detail="Impossible de générer un code unique")


def _validate_protocol(test_type: str, parameters: dict[str, Any], seed: int):
    test = TESTS_DISPONIBLES.get(test_type)
    if test is None:
        raise HTTPException(status_code=422, detail="Protocole inconnu")
    effective = {**test.parametres_defaut, **parameters}
    try:
        test.generer_essais(seed, effective)
    except ReponseInvalideError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return test, effective


def _validated_steps(
    inputs: list[ExperienceStepInput], seed: int
) -> list[tuple[Any, dict[str, Any], int]]:
    validated = []
    for step in inputs:
        test, effective = _validate_protocol(
            step.test_type, step.parametres, seed + step.seed_offset
        )
        validated.append((test, effective, step.seed_offset))
    return validated


def _replace_steps(
    experience: models.Experience,
    validated: list[tuple[Any, dict[str, Any], int]],
) -> None:
    experience.etapes.clear()
    for position, (test, parameters, seed_offset) in enumerate(validated):
        experience.etapes.append(
            models.EtapeExperience(
                position=position,
                test_type=test.type_test,
                protocol_version=test.version,
                parametres=parameters,
                seed_offset=seed_offset,
            )
        )
    first_test, first_parameters, _ = validated[0]
    experience.test_type = first_test.type_test
    experience.protocol_version = first_test.version
    experience.parametres = first_parameters


def _participant_payload(patient: Patient) -> dict[str, Any]:
    return {
        "id": patient.id,
        "nom": patient.nom,
        "prenom": patient.prenom,
        "age": patient.age,
        "created_at": patient.created_at,
    }


def _participant_access(
    session: Session, session_id: str, token: str | None
) -> models.ParticipantAccess:
    if not token:
        raise HTTPException(status_code=401, detail="Session participante requise")
    access = session.scalar(
        select(models.ParticipantAccess)
        .outerjoin(
            models.ExecutionEtape,
            models.ExecutionEtape.participant_access_id == models.ParticipantAccess.id,
        )
        .where(
            or_(
                models.ParticipantAccess.session_id == session_id,
                models.ExecutionEtape.session_id == session_id,
            ),
            models.ParticipantAccess.token_hash == _hash_token(token),
            models.ParticipantAccess.expires_at > utc_now(),
        )
    )
    if access is None:
        raise HTTPException(status_code=403, detail="Accès participant invalide")
    return access


def _start_participation(
    session: Session,
    experience: models.Experience,
    patient: Patient,
    pseudonym: str,
    participation_number: int,
    synthetic: bool,
) -> tuple[str, models.ParticipantAccess, list[models.SessionTest]]:
    steps = experience.etapes
    if not steps:
        raise HTTPException(status_code=409, detail="Cette expérience ne contient aucun test")
    test_sessions = []
    for step in steps:
        test_sessions.append(
            GestionnaireTests(session).demarrer(
                schemas.SessionTestCreate(
                    patient_id=patient.id,
                    protocole=f"{experience.nom} · étape {step.position + 1}",
                    type_test=step.test_type,
                    seed=experience.seed_base + step.seed_offset,
                    parametres=step.parametres,
                )
            )
        )
    token = secrets.token_urlsafe(32)
    access = models.ParticipantAccess(
        experiment_id=experience.id,
        patient_id=patient.id,
        session_id=test_sessions[0].id,
        pseudonyme=pseudonym,
        est_fictif=synthetic,
        token_hash=_hash_token(token),
        consented_at=utc_now(),
        expires_at=utc_now() + timedelta(hours=24),
    )
    session.add(access)
    session.flush()
    for step, test_session in zip(steps, test_sessions):
        session.add(
            models.ExecutionEtape(
                participant_access_id=access.id,
                etape_id=step.id,
                session_id=test_session.id,
                position=step.position,
            )
        )
    session.commit()
    return token, access, test_sessions


def _set_participant_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_PARTICIPANT,
        token,
        httponly=True,
        samesite="lax",
        secure=_secure_cookie(),
        max_age=24 * 60 * 60,
    )


@router.post("/api/auth/login")
def login(data: LoginRequest, response: Response, session: Session = Depends(get_session)):
    if not verify_researcher_credentials(data.username, data.password):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    token, stored = create_researcher_session(session, data.username)
    response.set_cookie(
        COOKIE_RESEARCHER,
        token,
        httponly=True,
        samesite="lax",
        secure=_secure_cookie(),
        max_age=int(os.getenv("MEMORIAE_RESEARCHER_SESSION_HOURS", "8")) * 3600,
    )
    return {"username": stored.username, "expires_at": stored.expires_at}


@router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    token: str | None = Cookie(default=None, alias=COOKIE_RESEARCHER),
    session: Session = Depends(get_session),
):
    delete_researcher_session(session, token)
    response.delete_cookie(COOKIE_RESEARCHER)
    return Response(status_code=204, headers=response.headers)


@router.get("/api/auth/me")
def auth_me(researcher=Depends(require_researcher)):
    return {"username": researcher.username, "expires_at": researcher.expires_at}


@router.get("/api/research/experiments")
def list_experiments(
    _researcher=Depends(require_researcher), session: Session = Depends(get_session)
):
    return [
        _experience_payload(experience)
        for experience in session.scalars(
            select(models.Experience)
            .options(selectinload(models.Experience.etapes))
            .order_by(models.Experience.created_at.desc())
        )
    ]


@router.post("/api/research/experiments", status_code=201)
def create_experiment(
    data: ExperienceCreate,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    inputs = data.etapes or [
        ExperienceStepInput(test_type=data.test_type, parametres=data.parametres)
    ]
    validated = _validated_steps(inputs, data.seed_base)
    first_test, first_parameters, _ = validated[0]
    experience = models.Experience(
        nom=data.nom,
        description=data.description,
        code=_new_experiment_code(session),
        test_type=first_test.type_test,
        protocol_version=first_test.version,
        parametres=first_parameters,
        seed_base=data.seed_base,
        active=data.active,
    )
    _replace_steps(experience, validated)
    session.add(experience)
    session.commit()
    session.refresh(experience)
    return _experience_payload(experience)


@router.get("/api/research/experiments/{experiment_id}")
def get_experiment(
    experiment_id: str,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    experience = session.scalar(
        select(models.Experience)
        .options(selectinload(models.Experience.etapes))
        .where(models.Experience.id == experiment_id)
    )
    if experience is None:
        raise HTTPException(status_code=404, detail="Expérience introuvable")
    return _experience_payload(experience)


@router.patch("/api/research/experiments/{experiment_id}")
def update_experiment(
    experiment_id: str,
    data: ExperienceUpdate,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    experience = session.scalar(
        select(models.Experience)
        .options(selectinload(models.Experience.etapes))
        .where(models.Experience.id == experiment_id)
    )
    if experience is None:
        raise HTTPException(status_code=404, detail="Expérience introuvable")
    updates = data.model_dump(exclude_unset=True)
    seed = updates.get("seed_base", experience.seed_base)
    new_steps = updates.pop("etapes", None)
    effective = None
    if new_steps is not None:
        validated = _validated_steps(
            [ExperienceStepInput.model_validate(step) for step in new_steps], seed
        )
        for current_step in list(experience.etapes):
            session.delete(current_step)
        experience.etapes.clear()
        session.flush()
        _replace_steps(experience, validated)
    elif "parametres" in updates:
        _, effective = _validate_protocol(
            experience.test_type, updates["parametres"], seed
        )
    for field, value in updates.items():
        setattr(experience, field, effective if field == "parametres" else value)
    session.commit()
    session.refresh(experience)
    return _experience_payload(experience)


@router.delete("/api/research/experiments/{experiment_id}", status_code=204)
def delete_experiment(
    experiment_id: str,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    experience = session.get(models.Experience, experiment_id)
    if experience is None:
        raise HTTPException(status_code=404, detail="Expérience introuvable")
    if experience.participations:
        raise HTTPException(
            status_code=409,
            detail="Cette expérience possède des sessions. Désactivez-la pour conserver l'historique.",
        )
    session.delete(experience)
    session.commit()
    return Response(status_code=204)


@router.post("/api/research/experiments/{experiment_id}/duplicate", status_code=201)
def duplicate_experiment(
    experiment_id: str,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    source = session.scalar(
        select(models.Experience)
        .options(selectinload(models.Experience.etapes))
        .where(models.Experience.id == experiment_id)
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Expérience introuvable")
    copy = models.Experience(
        nom=f"{source.nom} (copie)", description=source.description,
        code=_new_experiment_code(session), test_type=source.test_type,
        protocol_version=source.protocol_version, parametres=dict(source.parametres),
        seed_base=source.seed_base, active=False,
    )
    copy.etapes = [
        models.EtapeExperience(
            position=step.position, test_type=step.test_type,
            protocol_version=step.protocol_version, parametres=dict(step.parametres),
            seed_offset=step.seed_offset,
        )
        for step in source.etapes
    ]
    session.add(copy)
    session.commit()
    session.refresh(copy)
    return _experience_payload(copy)


@router.get("/api/research/participants")
def list_synthetic_participants(
    _researcher=Depends(require_researcher), session: Session = Depends(get_session)
):
    patients = session.scalars(
        select(Patient).where(
            Patient.est_fictif.is_(True), Patient.archived_at.is_(None)
        ).order_by(Patient.nom, Patient.prenom)
    )
    return [_participant_payload(patient) for patient in patients]


@router.get("/api/research/models")
def list_memory_models(_researcher=Depends(require_researcher)):
    return [model_status()]


@router.get("/api/research/models/memoriae_v2/experiments")
def compatible_model_experiments(
    _researcher=Depends(require_researcher), session: Session = Depends(get_session)
):
    experiments = session.scalars(
        select(models.Experience)
        .options(selectinload(models.Experience.etapes))
        .order_by(models.Experience.created_at.desc())
    )
    return [
        _experience_payload(experiment)
        for experiment in experiments
        if any(step.test_type == "fashion_mnist_partiel" for step in experiment.etapes)
    ]


@router.post("/api/research/models/memoriae_v2/execute", status_code=201)
def run_memoriae_v2(
    data: ModelExecutionRequest,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    try:
        execution = execute_memoriae_v2(session, data.experiment_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return execution_payload(execution)


@router.get("/api/research/experiments/{experiment_id}/comparison")
def experiment_comparison(
    experiment_id: str,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    try:
        return comparison_payload(session, experiment_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/api/research/participants", status_code=201)
def create_synthetic_participant(
    data: ParticipantFictifCreate,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    patient = Patient(
        **data.model_dump(), est_fictif=True, consentement=True, date_consentement=utc_now()
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return _participant_payload(patient)


@router.patch("/api/research/participants/{patient_id}")
def update_synthetic_participant(
    patient_id: str,
    data: ParticipantFictifUpdate,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    patient = session.get(Patient, patient_id)
    if patient is None or not patient.est_fictif or patient.archived_at is not None:
        raise HTTPException(status_code=404, detail="Participant introuvable")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    session.commit()
    session.refresh(patient)
    return _participant_payload(patient)


@router.delete("/api/research/participants/{patient_id}", status_code=204)
def archive_synthetic_participant(
    patient_id: str,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    patient = session.get(Patient, patient_id)
    if patient is None or not patient.est_fictif or patient.archived_at is not None:
        raise HTTPException(status_code=404, detail="Participant introuvable")
    patient.archived_at = utc_now()
    session.commit()
    return Response(status_code=204)


@router.post("/api/experiments/join", status_code=201)
def join_experiment(data: JoinRequest, response: Response, session: Session = Depends(get_session)):
    if not data.consentement:
        raise HTTPException(status_code=422, detail="Le consentement est requis")
    experience = session.scalar(
        select(models.Experience).options(selectinload(models.Experience.etapes)).where(
            func.upper(models.Experience.code) == data.code.strip().upper(),
            models.Experience.active.is_(True),
        )
    )
    if experience is None:
        raise HTTPException(status_code=404, detail="Code d'expérience invalide ou inactif")
    participation_number = session.scalar(
        select(func.count(models.ParticipantAccess.id)).where(
            models.ParticipantAccess.experiment_id == experience.id
        )
    ) or 0
    pseudonym = f"P-{secrets.token_hex(3).upper()}"
    participant = Patient(
        nom=pseudonym,
        consentement=True,
        date_consentement=utc_now(),
    )
    session.add(participant)
    session.commit()
    session.refresh(participant)
    token, _access, test_sessions = _start_participation(
        session, experience, participant, pseudonym, participation_number, False
    )
    _set_participant_cookie(response, token)
    return {
        "session_id": test_sessions[0].id,
        "pseudonyme": pseudonym,
        "experience": experience.nom,
        "nombre_etapes": len(test_sessions),
    }


@router.post("/api/research/experiments/{experiment_id}/launch", status_code=201)
def launch_with_synthetic_participant(
    experiment_id: str,
    data: LaunchRequest,
    response: Response,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    experience = session.scalar(
        select(models.Experience)
        .options(selectinload(models.Experience.etapes))
        .where(models.Experience.id == experiment_id)
    )
    patient = session.get(Patient, data.patient_id)
    if experience is None:
        raise HTTPException(status_code=404, detail="Expérience introuvable")
    if patient is None or not patient.est_fictif or patient.archived_at is not None:
        raise HTTPException(status_code=404, detail="Participant actif introuvable")
    participation_number = session.scalar(
        select(func.count(models.ParticipantAccess.id)).where(
            models.ParticipantAccess.experiment_id == experience.id
        )
    ) or 0
    display_name = " ".join(part for part in (patient.prenom, patient.nom) if part)
    token, _access, test_sessions = _start_participation(
        session, experience, patient, display_name, participation_number, True
    )
    _set_participant_cookie(response, token)
    return {
        "session_id": test_sessions[0].id,
        "participant": display_name,
        "experience": experience.nom,
        "nombre_etapes": len(test_sessions),
    }


@router.get("/api/sessions/{session_id}/next")
def participant_next(
    session_id: str,
    token: str | None = Cookie(default=None, alias=COOKIE_PARTICIPANT),
    session: Session = Depends(get_session),
):
    access = _participant_access(session, session_id, token)
    test_session = session.get(models.SessionTest, session_id)
    trial = GestionnaireTests(session).essai_courant(session_id)
    if trial is None:
        execution = session.scalar(
            select(models.ExecutionEtape).where(models.ExecutionEtape.session_id == session_id)
        )
        if execution is not None:
            next_execution = session.scalar(
                select(models.ExecutionEtape).where(
                    models.ExecutionEtape.participant_access_id == access.id,
                    models.ExecutionEtape.position == execution.position + 1,
                )
            )
            if next_execution is not None:
                return {
                    "terminee": False,
                    "changement_etape": True,
                    "session_id": next_execution.session_id,
                    "etape": next_execution.position + 1,
                    "nombre_etapes": len(access.executions),
                }
    return {
        "terminee": trial is None,
        "changement_etape": False,
        "essai": trial,
        "test_type": test_session.test_type,
        "progression": {
            "courant": test_session.essai_courant + 1,
            "total": len(test_session.essais),
        },
    }


@router.post("/api/sessions/{session_id}/responses")
def participant_response(
    session_id: str,
    data: schemas.SoumissionEssai,
    token: str | None = Cookie(default=None, alias=COOKIE_PARTICIPANT),
    session: Session = Depends(get_session),
):
    _participant_access(session, session_id, token)
    try:
        test_session, answer = GestionnaireTests(session).soumettre(session_id, data)
    except (SoumissionInterditeError, ReponseInvalideError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "essai_index": answer.essai_index,
        "session_terminee": test_session.statut == "terminee",
    }


@router.post("/api/sessions/{session_id}/finish")
def participant_finish(
    session_id: str,
    response: Response,
    token: str | None = Cookie(default=None, alias=COOKIE_PARTICIPANT),
    session: Session = Depends(get_session),
):
    access = _participant_access(session, session_id, token)
    test_session = session.get(models.SessionTest, session_id)
    unfinished = any(
        execution.session_test.statut != "terminee" for execution in access.executions
    )
    if test_session is None or test_session.statut != "terminee" or unfinished:
        raise HTTPException(status_code=409, detail="L'expérience n'est pas terminée")
    if access.finished_at is None:
        access.finished_at = utc_now()
        session.commit()
    response.delete_cookie(COOKIE_PARTICIPANT)
    return {"terminee": True}


def _research_results(session: Session):
    query = (
        select(models.ParticipantAccess)
        .options(
            selectinload(models.ParticipantAccess.experiment),
            selectinload(models.ParticipantAccess.session_test).selectinload(
                models.SessionTest.reponses
            ),
            selectinload(models.ParticipantAccess.executions)
            .selectinload(models.ExecutionEtape.session_test)
            .selectinload(models.SessionTest.reponses),
        )
        .order_by(models.ParticipantAccess.created_at.desc())
    )
    rows = []
    for access in session.scalars(query):
        executions = access.executions or []
        if executions:
            rows.extend((access, execution.session_test) for execution in executions)
        else:
            rows.append((access, access.session_test))
    return rows


@router.get("/api/research/results")
def research_results(
    _researcher=Depends(require_researcher), session: Session = Depends(get_session)
):
    payload = []
    for access, test_session in _research_results(session):
        scores = [answer.score for answer in test_session.reponses if answer.score is not None]
        payload.append(
            {
                "session_id": test_session.id,
                "experiment_id": access.experiment_id,
                "pseudonyme": access.pseudonyme,
                "experience": access.experiment.nom,
                "code": access.experiment.code,
                "test_type": test_session.test_type,
                "est_fictif": access.est_fictif,
                "statut": test_session.statut,
                "score": sum(scores) / len(scores) if scores else None,
                "started_at": test_session.started_at,
                "finished_at": access.finished_at,
            }
        )
    return payload


@router.get("/api/research/results/{session_id}")
def research_result_detail(
    session_id: str,
    _researcher=Depends(require_researcher),
    session: Session = Depends(get_session),
):
    access = session.scalar(
        select(models.ParticipantAccess)
        .outerjoin(models.ExecutionEtape)
        .where(or_(
            models.ParticipantAccess.session_id == session_id,
            models.ExecutionEtape.session_id == session_id,
        ))
    )
    if access is None:
        raise HTTPException(status_code=404, detail="Résultat introuvable")
    return GestionnaireTests(session).resultats(session_id)


@router.get("/api/research/export")
def research_export(
    _researcher=Depends(require_researcher), session: Session = Depends(get_session)
):
    output = io.StringIO()
    fields = [
        "session_id", "pseudonyme", "est_fictif", "experience", "code", "test_type", "seed",
        "essai_index", "condition", "stimulus", "reponse", "attendu", "score",
        "correcte", "temps_reponse_ms", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for access, test_session in _research_results(session):
        for answer in test_session.reponses:
            writer.writerow(
                {
                    "session_id": test_session.id,
                    "pseudonyme": access.pseudonyme,
                    "est_fictif": access.est_fictif,
                    "experience": access.experiment.nom,
                    "code": access.experiment.code,
                    "test_type": test_session.test_type,
                    "seed": test_session.seed,
                    "essai_index": answer.essai_index,
                    "condition": answer.condition,
                    "stimulus": json.dumps(answer.stimulus, ensure_ascii=False),
                    "reponse": answer.contenu,
                    "attendu": json.dumps(answer.reponse_attendue, ensure_ascii=False),
                    "score": answer.score,
                    "correcte": answer.correcte,
                    "temps_reponse_ms": answer.temps_reponse_ms,
                    "created_at": answer.created_at.isoformat(),
                }
            )
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="memoriae-resultats.csv"'},
    )
