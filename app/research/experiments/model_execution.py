from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.cognitive import TESTS_DISPONIBLES
from app.cognitive.tests.test_fashion_mnist import TestFashionMnist
from app.memory.models.memoriae_v2 import MemoriaeV2
from app.persistence import models

STIMULI_ROOT = Path(__file__).parents[2] / "cognitive" / "stimuli" / "fashion_mnist"


@lru_cache(maxsize=1)
def memoriae_v2() -> MemoriaeV2:
    return MemoriaeV2()


def execute_memoriae_v2(session: Session, experiment_id: str) -> models.ExecutionModele:
    experiment = session.scalar(
        select(models.Experience)
        .options(selectinload(models.Experience.etapes))
        .where(models.Experience.id == experiment_id)
    )
    if experiment is None:
        raise LookupError("Expérience introuvable")
    compatible_steps = [
        step for step in experiment.etapes if step.test_type == "fashion_mnist_partiel"
    ]
    if not compatible_steps:
        raise ValueError("Cette expérience ne contient aucun test compatible avec Memoriae V2")

    model = memoriae_v2()
    execution = models.ExecutionModele(
        experiment_id=experiment.id,
        model_id="memoriae_v2",
        model_version=model.version,
        protocol_version=TestFashionMnist.version,
        configuration={
            "experiment_id": experiment.id,
            "model": "Memoriae V2",
            "model_version": model.version,
            "beta": model.beta,
            "latent_dim": model.latent_dim,
            "checkpoint_memories": model.checkpoint_memories,
            "checkpoint_sha256": model.checkpoint_sha256,
            "steps": [],
        },
        statut="terminee",
    )
    session.add(execution)
    trial_index = 0
    configuration_steps: list[dict[str, Any]] = []
    test = TESTS_DISPONIBLES["fashion_mnist_partiel"]
    image_by_id = {image["id"]: image for image in test._images}
    for step in compatible_steps:
        seed = experiment.seed_base + step.seed_offset
        trials = test.generer_essais(seed, step.parametres)
        stored = trials[0]["stimulus"]["images"]
        images = [
            (image["id"], STIMULI_ROOT / Path(image_by_id[image["id"]]["src"]).name)
            for image in stored
        ]
        step_snapshot = {
            "step_id": step.id,
            "seed": seed,
            "parameters": dict(step.parametres),
            "stimulus_ids": [identifier for identifier, _ in images],
            "stimuli_version": test.stimuli_version,
            "trial_order": [
                {
                    "order": trial["stimulus"]["trial_order"],
                    "stimulus_id": trial["attendu"]["choix"],
                    "mask_ratio": trial["stimulus"]["mask_ratio"],
                    "candidate_ids": [
                        image["id"] for image in trial["stimulus"]["propositions"]
                    ],
                }
                for trial in trials[1:]
            ],
        }
        configuration_steps.append(step_snapshot)
        model_trials = [
            {
                "target_id": trial["attendu"]["choix"],
                "candidate_ids": [
                    image["id"] for image in trial["stimulus"]["propositions"]
                ],
                "mask_ratio": trial["stimulus"]["mask_ratio"],
                "mask_side": trial["stimulus"]["mask_side"],
                "trial_order": trial["stimulus"]["trial_order"],
            }
            for trial in trials[1:]
        ]
        for result in model.run_protocol(images, model_trials):
            execution.resultats.append(
                models.ResultatModele(
                    essai_index=trial_index,
                    stimulus_id=result["stimulus_id"],
                    predicted_stimulus_id=result["predicted_stimulus_id"],
                    correcte=result["correct"],
                    mse=result["mse"],
                    mesures={
                        "mask_ratio": result["mask_ratio"],
                        "mask_side": result["mask_side"],
                        "beta": result["beta"],
                        "memory_size": result["memory_size"],
                        "step_id": step.id,
                        "trial_order": result["trial_order"],
                        "candidate_ids": result["candidate_ids"],
                        "reconstruction_png_base64": result[
                            "reconstruction_png_base64"
                        ],
                    },
                )
            )
            trial_index += 1
    execution.configuration = {**execution.configuration, "steps": configuration_steps}
    session.commit()
    session.refresh(execution)
    return execution


def execution_payload(execution: models.ExecutionModele) -> dict[str, Any]:
    accuracy = (
        sum(result.correcte for result in execution.resultats) / len(execution.resultats)
        if execution.resultats
        else None
    )
    mse = (
        sum(result.mse for result in execution.resultats) / len(execution.resultats)
        if execution.resultats
        else None
    )
    by_mask = {}
    for ratio in (0.25, 0.5, 0.75):
        results = [
            result
            for result in execution.resultats
            if float(result.mesures.get("mask_ratio", 0)) == ratio
        ]
        by_mask[str(ratio)] = {
            "trials": len(results),
            "accuracy": (
                sum(result.correcte for result in results) / len(results) if results else None
            ),
            "mse": sum(result.mse for result in results) / len(results) if results else None,
        }
    return {
        "id": execution.id,
        "experiment_id": execution.experiment_id,
        "model_id": execution.model_id,
        "model_name": execution.configuration["model"],
        "model_version": execution.model_version,
        "protocol_version": execution.protocol_version,
        "configuration": execution.configuration,
        "statut": execution.statut,
        "created_at": execution.created_at,
        "accuracy": accuracy,
        "mse": mse,
        "nombre_essais": len(execution.resultats),
        "by_mask": by_mask,
        "resultats": [
            {
                "essai_index": result.essai_index,
                "stimulus_id": result.stimulus_id,
                "predicted_stimulus_id": result.predicted_stimulus_id,
                "correcte": result.correcte,
                "mse": result.mse,
                "mesures": result.mesures,
            }
            for result in execution.resultats
        ],
    }


def comparison_payload(session: Session, experiment_id: str) -> dict[str, Any]:
    experiment = session.get(models.Experience, experiment_id)
    if experiment is None:
        raise LookupError("Expérience introuvable")
    human_answers = list(
        session.scalars(
            select(models.ReponseSession)
            .join(models.SessionTest)
            .join(
                models.ExecutionEtape,
                models.ExecutionEtape.session_id == models.SessionTest.id,
            )
            .join(models.ParticipantAccess)
            .where(
                models.ParticipantAccess.experiment_id == experiment_id,
                models.SessionTest.test_type == "fashion_mnist_partiel",
                models.ReponseSession.score.is_not(None),
            )
        )
    )
    participant_count = session.scalar(
        select(func.count(func.distinct(models.ParticipantAccess.id)))
        .join(models.ExecutionEtape)
        .join(models.SessionTest)
        .where(
            models.ParticipantAccess.experiment_id == experiment_id,
            models.SessionTest.test_type == "fashion_mnist_partiel",
        )
    ) or 0
    model_execution = session.scalar(
        select(models.ExecutionModele)
        .options(selectinload(models.ExecutionModele.resultats))
        .where(
            models.ExecutionModele.experiment_id == experiment_id,
            models.ExecutionModele.model_id == "memoriae_v2",
        )
        .order_by(models.ExecutionModele.created_at.desc())
    )
    by_stimulus: dict[str, dict[str, Any]] = {}
    for answer in human_answers:
        stimulus_id = (answer.mesures or {}).get("stimulus_id")
        if stimulus_id:
            item = by_stimulus.setdefault(
                stimulus_id, {"stimulus_id": stimulus_id, "mask_ratio": (answer.mesures or {}).get("mask_ratio"),
                              "human_trials": 0, "human_errors": 0, "human_correct": 0,
                              "model_trials": 0, "model_errors": 0, "model_correct": 0}
            )
            item["human_trials"] += 1
            item["human_errors"] += int(not answer.correcte)
            item["human_correct"] += int(bool(answer.correcte))
    if model_execution:
        for result in model_execution.resultats:
            item = by_stimulus.setdefault(
                result.stimulus_id,
                {"stimulus_id": result.stimulus_id, "mask_ratio": result.mesures.get("mask_ratio"),
                 "human_trials": 0, "human_errors": 0, "human_correct": 0,
                 "model_trials": 0, "model_errors": 0, "model_correct": 0},
            )
            item["model_trials"] += 1
            item["model_errors"] += int(not result.correcte)
            item["model_correct"] += int(bool(result.correcte))
    human_accuracy = (
        sum(bool(answer.correcte) for answer in human_answers) / len(human_answers)
        if human_answers
        else None
    )
    human_by_mask = {}
    for ratio in (0.25, 0.5, 0.75):
        answers = [
            answer
            for answer in human_answers
            if float((answer.mesures or {}).get("mask_ratio", 0)) == ratio
        ]
        human_by_mask[str(ratio)] = {
            "trials": len(answers),
            "accuracy": (
                sum(bool(answer.correcte) for answer in answers) / len(answers)
                if answers
                else None
            ),
        }
    fashion_images = {
        image["id"]: {"src": image["src"], "label": image["label"]}
        for image in TestFashionMnist._images
    }
    stimulus_rows = []
    for item in sorted(by_stimulus.values(), key=lambda row: row["stimulus_id"]):
        stimulus_rows.append({**item, **fashion_images.get(item["stimulus_id"], {})})
    divergences = [
        item["stimulus_id"]
        for item in stimulus_rows
        if item["human_trials"]
        and item["model_trials"]
        and ((item["human_correct"] / item["human_trials"]) >= 0.5)
        != (item["model_correct"] > 0)
    ]
    return {
        "experiment_id": experiment.id,
        "experiment_name": experiment.nom,
        "human": {
            "participants": participant_count,
            "trials": len(human_answers),
            "accuracy": human_accuracy,
            "status": "disponible" if human_answers else "Données insuffisantes",
            "by_mask": human_by_mask,
        },
        "model": execution_payload(model_execution) if model_execution else None,
        "by_stimulus": stimulus_rows,
        "divergent_stimulus_ids": divergences,
    }
