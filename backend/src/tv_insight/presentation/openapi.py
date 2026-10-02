"""Dump the OpenAPI document without starting a server.

``python -m tv_insight.presentation.openapi [path]`` writes the JSON contract to
``path`` (or to stdout when no path is given). The frontend's generated
TypeScript types are produced from this document, so the API contract has a
single machine-readable source of truth instead of two hand-maintained files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tv_insight.presentation.app import create_app


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    # ``app.openapi()`` builds the document from the routers and response models,
    # so no lifespan (and therefore no database, container or network) is needed.
    document = create_app().openapi()
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args:
        Path(args[0]).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
