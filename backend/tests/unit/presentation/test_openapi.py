"""The OpenAPI dump CLI: the backend side of the generated TypeScript client."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tv_insight.presentation.openapi import main


def test_writes_the_document_to_a_file(tmp_path: Path) -> None:
    destination = tmp_path / "openapi.json"

    assert main([str(destination)]) == 0

    document = json.loads(destination.read_text(encoding="utf-8"))
    assert document["openapi"].startswith("3.")
    assert "/api/series/search" in document["paths"]
    # Sorted keys keep the file diff-friendly for the generated client check.
    assert destination.read_text(encoding="utf-8").splitlines()[1].startswith('  "components"')


def test_writes_the_document_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0

    assert '"openapi"' in capsys.readouterr().out
