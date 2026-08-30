#!/usr/bin/env python3
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})
try:
    import omni.kit.app
    m = omni.kit.app.get_app().get_extension_manager()
    m.set_extension_enabled_immediate("omni.kit.converter.hoops_core", True)
    for _ in range(10): app.update()
    try:
        from omni.kit.converter.hoops_core import get_instance, is_format_supported
        print("HOOPS Core import: OK")
        print("Converter instance:", "OK" if get_instance() is not None else "NOT INITIALIZED")
        print("STEP supported:", is_format_supported("dummy.step"))
    except Exception as e:
        print("HOOPS Core import: FAILED")
        print(repr(e))
        raise
finally:
    app.close()
