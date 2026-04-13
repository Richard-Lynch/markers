"""
Tests that verify examples/ scripts run without errors.

Run with: pytest tests/test_examples.py -v
"""

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _run_example(filename: str) -> subprocess.CompletedProcess[str]:
    """Run an example script and return the result."""
    script = EXAMPLES_DIR / filename
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize(
    "filename",
    [f.name for f in sorted(EXAMPLES_DIR.glob("*.py"))],
    ids=lambda f: f.removesuffix(".py"),
)
def test_example_runs_without_error(filename: str) -> None:
    result = _run_example(filename)
    assert result.returncode == 0, f"{filename} failed:\nstderr: {result.stderr}\nstdout: {result.stdout}"
