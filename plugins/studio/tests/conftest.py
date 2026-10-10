# SPDX-License-Identifier: MIT
"""Suchpfad für die Resolve-Skripte und den Fake; Fixture ``resolve``."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HIER = Path(__file__).resolve().parent
SKRIPTE = HIER.parent / "skills" / "resolve-schnitt" / "scripts"
for pfad in (SKRIPTE, HIER):
    if str(pfad) not in sys.path:
        sys.path.insert(0, str(pfad))

import resolve_fake  # noqa: E402


@pytest.fixture
def resolve():
    return resolve_fake.Resolve()
