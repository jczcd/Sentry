"""Isaac Lab DirectRLEnv asset adapter template.

This module deliberately requires a caller-supplied, calibrated ArticulationCfg.
It defines the stable dimensions and lifecycle hooks without inventing wheel
joint names or physics values for the uploaded legacy asset.
"""

from __future__ import annotations

from collections.abc import Sequence

import torch

import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.envs import DirectRLEnv, DirectRLEnvCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sim import SimulationCfg
from isaaclab.sim.spawners.from_files import GroundPlaneCfg, spawn_ground_plane
from isaaclab.utils import configclass


@configclass
class SentinelTacticalEnvCfg(DirectRLEnvCfg):
    decimation = 120
    episode_length_s = 450.0
    action_space = 10
    observation_space = 161
    state_space = 0
    sim: SimulationCfg = SimulationCfg(dt=1.0 / 120.0, render_interval=12)
    scene: InteractiveSceneCfg = InteractiveSceneCfg(
        num_envs=256,
        env_spacing=35.0,
        replicate_physics=True,
        clone_in_fabric=True,
    )
    # Set this to a validated ArticulationCfg before constructing the env.
    robot_cfg: ArticulationCfg | None = None


class SentinelTacticalEnv(DirectRLEnv):
    cfg: SentinelTacticalEnvCfg

    def __init__(
        self,
        cfg: SentinelTacticalEnvCfg,
        render_mode: str | None = None,
        **kwargs,
    ):
        if cfg.robot_cfg is None:
            raise ValueError(
                "robot_cfg is required; do not train on guessed joints/inertias"
            )
        super().__init__(cfg, render_mode, **kwargs)
        self.actions = torch.zeros((self.num_envs, 10), device=self.device)
        # Populate this buffer from the same 161-D builder used in deployment.
        self.policy_observation = torch.zeros(
            (self.num_envs, 161), device=self.device
        )

    def _setup_scene(self) -> None:
        assert self.cfg.robot_cfg is not None
        self.robot = Articulation(self.cfg.robot_cfg)
        spawn_ground_plane("/World/ground", GroundPlaneCfg())
        self.scene.clone_environments(copy_from_source=False)
        if self.device == "cpu":
            self.scene.filter_collisions(global_prim_paths=[])
        self.scene.articulations["sentinel"] = self.robot
        light = sim_utils.DomeLightCfg(
            intensity=2000.0, color=(0.75, 0.75, 0.75)
        )
        light.func("/World/Light", light)

    def _pre_physics_step(self, actions: torch.Tensor) -> None:
        self.actions = torch.clamp(actions.clone(), -1.0, 1.0)

    def _apply_action(self) -> None:
        # Connect actions[:, :2] to a deterministic omni-base controller here.
        # The discrete fire/target heads must never write physics actuators.
        raise NotImplementedError("bind the calibrated omni-base controller")

    def _get_observations(self) -> dict:
        return {"policy": self.policy_observation}

    def _get_rewards(self) -> torch.Tensor:
        raise NotImplementedError("bind referee/game-state reward terms")

    def _get_dones(self) -> tuple[torch.Tensor, torch.Tensor]:
        timeout = self.episode_length_buf >= self.max_episode_length - 1
        terminated = torch.zeros_like(timeout)
        return terminated, timeout

    def _reset_idx(self, env_ids: Sequence[int] | None) -> None:
        super()._reset_idx(env_ids)
        # Reset robot, opponents, referee state and observation history here.
