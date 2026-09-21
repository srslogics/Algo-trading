"""Regenerate the versioned API contract without starting a server."""

import json
from pathlib import Path

from optionlab.api.app import create_app
from optionlab.config import Settings

target = Path(__file__).resolve().parents[1] / "docs/openapi.json"
target.write_text(json.dumps(create_app(Settings(_env_file=None)).openapi(), indent=2) + "\n")
print(target)
