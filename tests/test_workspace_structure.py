from __future__ import annotations

from pathlib import Path
import importlib.util
import py_compile
import unittest
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceStructureTest(unittest.TestCase):
    def test_ros_packages_are_parseable(self) -> None:
        packages = list((ROOT / "ros2_ws" / "src").glob("*/package.xml"))
        self.assertEqual(len(packages), 5)
        names = set()
        for package in packages:
            tree = ET.parse(package)
            name = tree.findtext("name")
            self.assertTrue(name)
            names.add(name)
        self.assertEqual(
            names,
            {
                "sentinel_interfaces",
                "sentinel_core",
                "sentinel_description",
                "sentinel_navigation",
                "sentinel_bringup",
            },
        )

    def test_python_entrypoints_compile(self) -> None:
        roots = [
            ROOT / "ros2_ws" / "src",
            ROOT / "isaac_sim" / "scripts",
            ROOT / "tools" / "common",
            ROOT / "training",
        ]
        failures = []
        for base in roots:
            for path in base.rglob("*.py"):
                if "RMUC-OfflineRL" in path.parts:
                    continue
                try:
                    py_compile.compile(str(path), doraise=True)
                except py_compile.PyCompileError as exc:
                    failures.append(f"{path}: {exc}")
        self.assertEqual(failures, [])

    def test_navigation_config_and_map(self) -> None:
        config = yaml.safe_load(
            (ROOT / "ros2_ws" / "src" / "sentinel_navigation"
             / "config" / "nav2.yaml").read_text(encoding="utf-8")
        )
        controller = config["controller_server"]["ros__parameters"]
        self.assertEqual(
            controller["FollowPath"]["plugin"],
            "nav2_mppi_controller::MPPIController",
        )
        self.assertEqual(controller["FollowPath"]["motion_model"], "Omni")
        self.assertFalse(controller["enable_stamped_cmd_vel"])
        map_png = (
            ROOT / "ros2_ws" / "src" / "sentinel_navigation"
            / "map" / "rmuc2024.png"
        )
        self.assertTrue(map_png.is_file())
        self.assertTrue(map_png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
        ET.parse(ROOT / "config" / "fastdds.xml")

    def test_no_legacy_absolute_home_path(self) -> None:
        offenders = []
        for path in (ROOT / "ros2_ws").rglob("*"):
            if path.is_file() and path.suffix in {
                ".py",
                ".xml",
                ".yaml",
                ".yml",
                ".txt",
            }:
                text = path.read_text(encoding="utf-8", errors="replace")
                if "/home/awaker" in text or "/home/awaker1" in text:
                    offenders.append(path)
        self.assertEqual(offenders, [])

    def test_asset_import_rejects_cross_platform_traversal(self) -> None:
        script = ROOT / "tools" / "common" / "import_isaac_rm.py"
        spec = importlib.util.spec_from_file_location("import_isaac_rm", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaises(ValueError):
            module.wanted("../RMUC2024.usd")
        with self.assertRaises(ValueError):
            module.wanted(r"..\RMUC2024.usd")
        self.assertTrue(module.wanted("RMUC2024.usd"))
        self.assertTrue(module.wanted("RMUC_sim_nav/robot/body.usd"))


if __name__ == "__main__":
    unittest.main()
