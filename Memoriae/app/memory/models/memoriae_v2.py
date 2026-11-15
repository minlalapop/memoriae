from __future__ import annotations

import base64
import io
from pathlib import Path
from threading import Lock
from typing import Any

from app.memory.models.memory_model import MemoryModel

CHECKPOINT_PATH = Path(__file__).parent / "checkpoints" / "memoriae_v2.pt"
CHECKPOINT_SHA256 = "667c34d4a65be9152432b11cdfe7e166aa0cd96ffd0edec1293c047fecac1702"

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from PIL import Image
    from torchvision.transforms.functional import pil_to_tensor
except ImportError:  # Les dépendances du modèle sont optionnelles pour le backend standard.
    torch = nn = F = Image = pil_to_tensor = None


class ModelUnavailableError(RuntimeError):
    pass


if nn is not None:

    class MemoriaeEncoder(nn.Module):
        def __init__(self, latent_dim: int = 64) -> None:
            super().__init__()
            self.network = nn.Sequential(
                nn.Flatten(),
                nn.Linear(784, 256),
                nn.ReLU(),
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.Linear(128, latent_dim),
            )

        def forward(self, images):
            return self.network(images)


    class MemoriaeDecoder(nn.Module):
        def __init__(self, latent_dim: int = 64) -> None:
            super().__init__()
            self.network = nn.Sequential(
                nn.Linear(latent_dim, 128),
                nn.ReLU(),
                nn.Linear(128, 256),
                nn.ReLU(),
                nn.Linear(256, 784),
                nn.Sigmoid(),
                nn.Unflatten(1, (1, 28, 28)),
            )

        def forward(self, latent):
            return self.network(latent)


    class ModernHopfieldMemory(nn.Module):
        def __init__(self, beta: float = 1000.0) -> None:
            super().__init__()
            self.beta = beta
            self.register_buffer("patterns", torch.empty(0, 64))

        def store(self, latents) -> None:
            self.patterns = latents.detach().clone()

        def retrieve_with_weights(self, query):
            keys = F.normalize(self.patterns, dim=1)
            queries = F.normalize(query, dim=1)
            weights = F.softmax(self.beta * (queries @ keys.T), dim=1)
            return weights @ self.patterns, weights

        def forward(self, query):
            return self.retrieve_with_weights(query)[0]


    class _MemoriaeAssociative(nn.Module):
        def __init__(self, latent_dim: int = 64, beta: float = 1000.0) -> None:
            super().__init__()
            self.encoder = MemoriaeEncoder(latent_dim)
            self.decoder = MemoriaeDecoder(latent_dim)
            self.memory = ModernHopfieldMemory(beta)


class MemoriaeV2(MemoryModel):
    """Adaptateur d'inférence du checkpoint V2, indépendant de FastAPI et SQLAlchemy."""

    name = "Memoriae V2"
    version = "2.0"
    compatible_test_types = {"fashion_mnist_partiel"}
    checkpoint_sha256 = CHECKPOINT_SHA256

    def __init__(self, checkpoint_path: Path = CHECKPOINT_PATH) -> None:
        if torch is None:
            raise ModelUnavailableError(
                "Les dépendances optionnelles du modèle ne sont pas installées"
            )
        if not checkpoint_path.is_file():
            raise ModelUnavailableError("Le checkpoint Memoriae V2 est absent")
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        latent_dim = int(checkpoint["latent_dim"])
        beta = float(checkpoint["beta"])
        if latent_dim != 64 or int(checkpoint["num_memories"]) != 128 or beta != 1000.0:
            raise ModelUnavailableError("Le checkpoint Memoriae V2 est incompatible")
        self.model = _MemoriaeAssociative(latent_dim, beta)
        state = dict(checkpoint["model_state_dict"])
        stored_patterns = state.pop("memory.patterns")
        missing, unexpected = self.model.load_state_dict(state, strict=False)
        if missing != ["memory.patterns"] or unexpected:
            raise ModelUnavailableError("Le checkpoint Memoriae V2 est incomplet")
        self.model.memory.store(stored_patterns)
        self.model.eval()
        self.beta = beta
        self.latent_dim = latent_dim
        self.checkpoint_memories = int(checkpoint["num_memories"])
        self._lock = Lock()

    def encode(self, representations: list[Any]) -> None:
        images = torch.stack(representations)
        with torch.no_grad():
            self.model.memory.store(self.model.encoder(images))

    def retrieve(self, query: Any, limit: int = 1) -> list[Any]:
        del limit
        with torch.no_grad():
            latent = self.model.encoder(query.unsqueeze(0))
            retrieved, weights = self.model.memory.retrieve_with_weights(latent)
            reconstruction = self.model.decoder(retrieved)[0]
        return [reconstruction, weights[0]]

    @staticmethod
    def load_image(path: Path):
        with Image.open(path) as image:
            grayscale = image.convert("L")
            return pil_to_tensor(grayscale).to(dtype=torch.float32) / 255.0

    def run_recognition(
        self,
        images: list[tuple[str, Path]],
        target_id: str,
        mask_ratio: float = 0.5,
        mask_side: str = "right",
        candidate_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if candidate_ids is None:
            candidate_ids = [target_id, *[
                identifier for identifier, _ in images if identifier != target_id
            ][:3]]
        return self.run_protocol(
            images,
            [
                {
                    "target_id": target_id,
                    "candidate_ids": candidate_ids,
                    "mask_ratio": mask_ratio,
                    "mask_side": mask_side,
                    "trial_order": 1,
                }
            ],
        )[0]

    def run_protocol(
        self,
        images: list[tuple[str, Path]],
        trials: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        identifiers = [identifier for identifier, _ in images]
        tensors = [self.load_image(path) for _, path in images]
        results = []
        with self._lock:
            self.encode(tensors)
            for trial in trials:
                target_id = trial["target_id"]
                candidate_ids = trial["candidate_ids"]
                mask_ratio = float(trial["mask_ratio"])
                mask_side = trial["mask_side"]
                if mask_ratio not in {0.25, 0.5, 0.75} or mask_side != "right":
                    raise ValueError("Masque expérimental incompatible avec Memoriae V2")
                if target_id not in identifiers or not set(candidate_ids) <= set(identifiers):
                    raise ValueError("Stimulus absent de la banque expérimentale")
                if target_id not in candidate_ids or len(candidate_ids) != 4:
                    raise ValueError("Chaque essai doit proposer quatre choix dont la cible")
                target_index = identifiers.index(target_id)
                partial = tensors[target_index].clone()
                masked_columns = round(28 * mask_ratio)
                partial[:, :, 28 - masked_columns :] = 0
                reconstruction, weights = self.retrieve(partial)
                candidate_indices = [identifiers.index(identifier) for identifier in candidate_ids]
                predicted_index = max(
                    candidate_indices, key=lambda index: float(weights[index].item())
                )
                mse = float(F.mse_loss(reconstruction, tensors[target_index]).item())
                results.append(
                    {
                        "stimulus_id": target_id,
                        "predicted_stimulus_id": identifiers[predicted_index],
                        "correct": predicted_index == target_index,
                        "mse": mse,
                        "reconstruction_png_base64": self._png_base64(reconstruction),
                        "mask_ratio": mask_ratio,
                        "mask_side": mask_side,
                        "trial_order": trial["trial_order"],
                        "candidate_ids": list(candidate_ids),
                        "beta": self.beta,
                        "memory_size": len(images),
                    }
                )
        return results

    @staticmethod
    def _png_base64(tensor) -> str:
        values = tensor.detach().clamp(0, 1).mul(255).round().to(torch.uint8).flatten().tolist()
        image = Image.frombytes("L", (28, 28), bytes(values))
        output = io.BytesIO()
        image.save(output, format="PNG", optimize=True)
        return base64.b64encode(output.getvalue()).decode("ascii")


def model_status() -> dict[str, Any]:
    available = torch is not None and CHECKPOINT_PATH.is_file()
    return {
        "id": "memoriae_v2",
        "name": MemoriaeV2.name,
        "version": MemoriaeV2.version,
        "available": available,
        "status": "prêt" if available else "dépendances du modèle non installées",
        "compatible_test_types": sorted(MemoriaeV2.compatible_test_types),
        "checkpoint_sha256": CHECKPOINT_SHA256,
    }
