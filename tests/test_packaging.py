from __future__ import annotations

import subprocess
import zipfile


def test_wheel_contains_console_entrypoint_runtime_package(tmp_path):
    subprocess.run(["uv", "build", "--out-dir", str(tmp_path)], check=True)
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1

    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())

    assert "compshare/__init__.py" in names
    assert "compshare_cli/__init__.py" in names
    assert "compshare_cli/cli.py" in names
