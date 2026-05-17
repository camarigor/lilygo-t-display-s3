"""Pre-build check: garante que firmware/include/generated_config.h existe.

PIO roda esse script do dir firmware/ (project root), então paths são
relativos a esse dir.
"""
import os
import sys

config = "include/generated_config.h"
if not os.path.isfile(config):
    print(f"\n✗ firmware/{config} não existe.")
    print("  Rode scripts/generate-envs.sh primeiro a partir do root do repo.\n")
    sys.exit(1)
