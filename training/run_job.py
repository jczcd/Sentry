#!/usr/bin/env python3
"""Validated training-job adapter used by the ROS 2 training manager."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

import yaml


WORKSPACE = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--run-name", required=True)
    return parser.parse_args()


def below(root: Path, value: str, *, must_exist: bool = True) -> Path:
    path = Path(os.path.expandvars(value)).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve(strict=must_exist)
    root = root.resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"path escapes {root}: {path}")
    return path


def offline_command(config: dict, run_name: str) -> tuple[list[str], Path]:
    repository = below(WORKSPACE, str(config["repository"]))
    trainer = below(repository, str(config["trainer_config"]))
    data = below(repository, str(config["data"]))
    output_root = below(
        WORKSPACE, str(config.get("output_root", "artifacts/policies")),
        must_exist=False
    )
    output_root.mkdir(parents=True, exist_ok=True)
    output = below(output_root, run_name, must_exist=False)
    command = [
        sys.executable,
        "-m",
        "rm_rl.train.train_offline",
        "--config",
        str(trainer),
        "--data",
        str(data),
        "--out",
        str(output),
    ]
    return command, repository


def isaac_lab_command(config: dict) -> tuple[list[str], Path]:
    root_text = os.path.expandvars(str(config["isaac_lab_root"]))
    if "$" in root_text or not root_text:
        raise ValueError("set ISAACLAB_ROOT before starting the job")
    root = Path(root_text).expanduser().resolve(strict=True)
    launcher = root / "isaaclab.sh"
    script = below(root, str(config["script"]))
    task = str(config["task"])
    if not task.startswith("Sentinel-"):
        raise ValueError("only Sentinel-* Isaac Lab tasks are allowed")
    command = [str(launcher), "-p", str(script), "--task", task]
    if bool(config.get("headless", True)):
        command.append("--headless")
    if "num_envs" in config:
        count = int(config["num_envs"])
        if not 1 <= count <= 16384:
            raise ValueError("num_envs is out of range")
        command += ["--num_envs", str(count)]
    extra = config.get("extra_args", [])
    if not isinstance(extra, list) or not all(isinstance(x, str) for x in extra):
        raise ValueError("extra_args must be a list of strings")
    command.extend(extra)
    return command, root


def main() -> int:
    args = parse_args()
    config_path = args.config.expanduser().resolve(strict=True)
    with config_path.open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise SystemExit("job config must be a mapping")
    kind = config.get("kind")
    if kind == "offline_rmuc":
        command, cwd = offline_command(config, args.run_name)
    elif kind == "isaac_lab":
        command, cwd = isaac_lab_command(config)
    else:
        raise SystemExit(f"unsupported job kind: {kind!r}")
    print("training command:", " ".join(command), flush=True)
    return subprocess.run(command, cwd=cwd, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
