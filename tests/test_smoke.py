"""Smoke tests for package and command-line availability."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import point_audit


def test_package_imports() -> None:
    """The package can be imported without optional AI dependencies."""
    assert point_audit.__version__ == "0.1.0"


def test_cli_help() -> None:
    """The module CLI exposes help and exits successfully."""
    project_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    source_path = str(project_root / "src")
    current_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{source_path}{os.pathsep}{current_pythonpath}" if current_pythonpath else source_path
    )

    result = subprocess.run(
        [sys.executable, "-m", "point_audit", "--help"],
        cwd=project_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "usage: point_audit" in result.stdout

