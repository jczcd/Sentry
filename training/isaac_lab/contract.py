"""Dependency-light contract shared by Isaac Lab adapters and unit tests."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


OBSERVATION_DIM = 161
ACTION_DIM = 10
TARGET_CLASSES = 7
NO_TARGET = 6


@dataclass(frozen=True, slots=True)
class TacticalAction:
    goal_dx_m: float
    goal_dy_m: float
    weapons_free_probability: float
    target_probabilities: tuple[float, ...]

    @property
    def target_slot(self) -> int:
        return max(range(TARGET_CLASSES), key=self.target_probabilities.__getitem__)


@dataclass(frozen=True, slots=True)
class RewardTerms:
    progress_m: float = 0.0
    team_damage: float = 0.0
    outpost_damage: float = 0.0
    survival: float = 0.0
    collision: float = 0.0
    out_of_bounds: float = 0.0
    overheated: float = 0.0
    wasted_fire: float = 0.0

    def total(self) -> float:
        return (
            2.0 * self.progress_m
            + 1.0 * self.team_damage
            + 3.0 * self.outpost_damage
            + 0.02 * self.survival
            - 2.0 * self.collision
            - 5.0 * self.out_of_bounds
            - 0.5 * self.overheated
            - 0.1 * self.wasted_fire
        )


def validate_observation(features: Sequence[float]) -> tuple[float, ...]:
    if len(features) != OBSERVATION_DIM:
        raise ValueError(
            f"observation has {len(features)} values; expected {OBSERVATION_DIM}"
        )
    output = tuple(float(value) for value in features)
    if not all(math.isfinite(value) for value in output):
        raise ValueError("observation contains NaN or infinity")
    return output


def softmax(values: Sequence[float]) -> tuple[float, ...]:
    if len(values) != TARGET_CLASSES:
        raise ValueError("target head must contain seven logits")
    logits = [float(value) for value in values]
    if not all(math.isfinite(value) for value in logits):
        raise ValueError("target logits contain NaN or infinity")
    offset = max(logits)
    weights = [math.exp(value - offset) for value in logits]
    total = sum(weights)
    return tuple(value / total for value in weights)


def decode_continuous_heads(
    values: Sequence[float],
    *,
    goal_scale_m: tuple[float, float] = (7.5, 8.0),
) -> TacticalAction:
    """Decode a generic continuous RL head into the deployed mixed action.

    Offline RMUC checkpoints already perform this head decoding internally.
    This helper is intended for Isaac Lab libraries that expose one continuous
    action tensor.
    """

    if len(values) != ACTION_DIM:
        raise ValueError(f"action has {len(values)} values; expected {ACTION_DIM}")
    action = [float(value) for value in values]
    if not all(math.isfinite(value) for value in action):
        raise ValueError("action contains NaN or infinity")
    goal_x = min(max(action[0], -1.0), 1.0) * goal_scale_m[0]
    goal_y = min(max(action[1], -1.0), 1.0) * goal_scale_m[1]
    fire = 1.0 / (1.0 + math.exp(-min(max(action[2], -30.0), 30.0)))
    return TacticalAction(goal_x, goal_y, fire, softmax(action[3:10]))
