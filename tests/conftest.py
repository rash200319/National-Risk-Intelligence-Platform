import sys
from pathlib import Path


def _add_backend_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    candidate_paths = [repo_root / "app", repo_root / "backend"]
    for path in candidate_paths:
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))


_add_backend_to_path()
