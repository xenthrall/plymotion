"""Natural (human) sort ordering for filenames.

Splits a filename into text/number chunks and compares numbers by value, so
"frame2.png" sorts before "frame10.png" — plain lexicographic sort would put
"frame10.png" first. Used anywhere frame or image sequence order matters.
"""

from __future__ import annotations

import re
from pathlib import Path

_CHUNK_RE = re.compile(r"(\d+)")


def natural_sort_key(path: Path) -> list[object]:
    return [
        int(chunk) if chunk.isdigit() else chunk.lower()
        for chunk in _CHUNK_RE.split(path.name)
    ]
