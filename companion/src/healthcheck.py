"""Healthcheck pra Docker HEALTHCHECK directive.

Exit codes:
  0 = healthy (health file existe + foi tocado nos últimos STALE_SECONDS)
  1 = file missing
  2 = file stale
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

HEALTH_FILE = Path(os.environ.get("HEALTH_FILE", "/tmp/companion-health"))
STALE_SECONDS = 90


def main() -> int:
    if not HEALTH_FILE.is_file():
        return 1
    age = time.time() - HEALTH_FILE.stat().st_mtime
    if age > STALE_SECONDS:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
