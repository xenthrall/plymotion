"""HTTP API (FastAPI) consumed by the web client."""

from plymotion.api.app import create_app
from plymotion.api.config import ApiConfig

__all__ = ["ApiConfig", "create_app"]
