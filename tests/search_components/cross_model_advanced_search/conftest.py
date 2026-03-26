from __future__ import annotations

import os
import sys

from pathlib import Path

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bcap.settings")
django.setup()

sys.path.insert(0, str(Path(__file__).resolve().parent))
