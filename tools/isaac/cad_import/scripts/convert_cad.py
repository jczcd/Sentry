#!/usr/bin/env python3
"""Convert the supplied Sentry STEP assembly to editable USD using Isaac Sim's HOOPS Core converter.

Run with Isaac Sim's Python environment, for example:
    /path/to/isaac-sim/python.sh scripts/convert_cad.py
"""
from pathlib import Path
import argparse
import asyncio
import json
import sys


def parse_args():
    here = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=str(here / "source" / "Sentry.step"))
    p.add_argument("--output", default=str(here / "output" / "Sentry_raw.usd"))
    p.add_argument("--tess-lod", type=int, default=1, choices=range(0, 5), metavar="0..4")
    p.add_argument("--headless", action="store_true", default=True)
    p.add_argument("--no-materials", action="store_true")
    return p.parse_args()


args = parse_args()
input_path = Path(args.input).resolve()
output_path = Path(args.output).resolve()
output_path.parent.mkdir(parents=True, exist_ok=True)

if not input_path.exists():
    raise SystemExit(f"Input STEP not found: {input_path}")

# IMPORTANT: Omniverse/pxr imports must happen after SimulationApp starts.
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": bool(args.headless)})

try:
    import omni.kit.app

    app = omni.kit.app.get_app()
    ext_mgr = app.get_extension_manager()

    # HOOPS Core does the actual STEP -> USD conversion. The GUI extension is optional.
    ext_mgr.set_extension_enabled_immediate("omni.kit.converter.hoops_core", True)
    for _ in range(20):
        simulation_app.update()

    import omni.converter.hoops
    from omni.kit.converter.hoops_core import HoopsOptions, get_instance, is_format_supported

    if not is_format_supported(str(input_path)):
        raise RuntimeError(f"HOOPS Core reports unsupported input format: {input_path.suffix}")

    converter = get_instance()
    if converter is None:
        raise RuntimeError(
            "HOOPS Core converter did not initialize. Open Isaac Sim > Window > Extensions and verify "
            "that omni.kit.converter.hoops_core / CAD Converter is installed."
        )

    options = HoopsOptions()
    # Editable references are preferable here: repeated CAD parts remain shared while still modifiable.
    options.instancingStyle = omni.converter.hoops.InstancingStyle.eReference
    options.compositionStyle = omni.converter.hoops.CompositionStyle.eNone
    options.filterStyle = omni.converter.hoops.FilterStyle.eOmit
    options.tessLOD = int(args.tess_lod)
    options.useMaterials = not args.no_materials
    options.useNormals = True
    options.convertMetadata = True
    options.convertCurves = False
    options.reportProgress = True

    async def do_convert():
        return await converter.create_converter_task(
            str(input_path), str(output_path), options.toArgs()
        )

    loop = asyncio.get_event_loop()
    output_url, status = loop.run_until_complete(do_convert())
    for _ in range(10):
        simulation_app.update()

    error_code = int(getattr(status, "error_code", -1))
    error_msg = str(getattr(status, "error_msg", ""))
    if error_code != 0 or not output_url:
        raise RuntimeError(f"CAD conversion failed: code={error_code}, msg={error_msg}")

    print(f"[OK] CAD -> USD: {output_url}")

    # Create a lightweight wrapper stage that gives the imported asset a stable /Sentry root.
    from pxr import Usd, UsdGeom

    raw_stage = Usd.Stage.Open(str(output_path))
    if raw_stage is None:
        raise RuntimeError(f"Converted USD could not be opened: {output_path}")
    raw_default = raw_stage.GetDefaultPrim()
    if not raw_default or not raw_default.IsValid():
        # Fallback: first root prim.
        roots = list(raw_stage.GetPseudoRoot().GetChildren())
        if not roots:
            raise RuntimeError("Converted USD has no root prims")
        raw_default = roots[0]

    wrapper_path = output_path.parent / "Sentry.usda"
    wrapper = Usd.Stage.CreateNew(str(wrapper_path))
    root = UsdGeom.Xform.Define(wrapper, "/Sentry").GetPrim()
    root.GetReferences().AddReference("./" + output_path.name, raw_default.GetPath())
    wrapper.SetDefaultPrim(root)
    UsdGeom.SetStageUpAxis(wrapper, UsdGeom.Tokens.z)
    wrapper.GetRootLayer().Save()

    # Record conversion metadata for later debugging.
    meta = {
        "input": str(input_path),
        "raw_usd": str(output_path),
        "wrapper_usda": str(wrapper_path),
        "raw_default_prim": str(raw_default.GetPath()),
        "tess_lod": args.tess_lod,
        "instancing_style": "Reference",
        "composition_style": "Monolithic"
    }
    (output_path.parent / "conversion_result.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] Wrapper stage: {wrapper_path}")
    print("[NEXT] Run scripts/inspect_links.py with the same Isaac Sim Python environment.")
finally:
    simulation_app.close()
