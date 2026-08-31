"""Vendored allenai/IFBench constraint checkers (Apache-2.0, see LICENSE).

Files are byte-identical to github.com/allenai/IFBench (instructions.py,
instructions_util.py, instructions_registry.py). They use flat intra-package
imports (`import instructions_util`), so the package dir goes on sys.path.
Importing this package needs nltk + emoji + syllapy (see requirements.txt);
nltk corpora download once into .nltk_data/ here on first checker use.
"""
from __future__ import annotations

import sys
from pathlib import Path

_dir = str(Path(__file__).resolve().parent)
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from instructions_registry import INSTRUCTION_DICT  # noqa: E402

__all__ = ["INSTRUCTION_DICT"]
