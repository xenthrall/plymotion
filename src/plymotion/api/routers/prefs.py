"""Persisted client preferences (pywebview doesn't keep localStorage between runs)."""

from __future__ import annotations

from fastapi import APIRouter

from plymotion.api.schemas import Prefs, PrefsPatch
from plymotion.core import library

router = APIRouter(tags=["prefs"])


def _load() -> Prefs:
    stored = library.load_prefs()
    known = {k: v for k, v in stored.items() if k in Prefs.model_fields}
    try:
        return Prefs.model_validate(known)
    except ValueError:
        return Prefs()


@router.get("/prefs", response_model=Prefs)
def get_prefs() -> Prefs:
    return _load()


@router.patch("/prefs", response_model=Prefs)
def patch_prefs(body: PrefsPatch) -> Prefs:
    merged = _load().model_copy(update=body.model_dump(exclude_none=True))
    library.update_prefs(**merged.model_dump())
    return merged
