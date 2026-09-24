"""Write the API's OpenAPI schema for the web client's type generation.

    uv run python -m plymotion.api.export_openapi [output]   # default: frontend/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from plymotion.api import ApiConfig, create_app


def main() -> None:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "frontend/openapi.json")
    schema = create_app(ApiConfig(port=0, dev=True, static_dir=None)).openapi()
    output.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
    print(f"OpenAPI schema written to {output}")


if __name__ == "__main__":
    main()
