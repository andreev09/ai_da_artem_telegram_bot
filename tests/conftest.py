"""Настройки общие для тестов проекта."""

from __future__ import annotations

import sys
from pathlib import Path

# Обеспечиваем доступность корня репозитория в PYTHONPATH, чтобы модули можно было импортировать.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)
