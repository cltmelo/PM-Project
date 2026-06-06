"""File utility functions."""
import os
from pathlib import Path


def ensure_dir(path: str) -> str:
    """Ensure a directory exists."""
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


def validate_file(path: str, must_exist: bool = True) -> Path:
    """Validate that a file exists."""
    file_path = Path(path)
    if must_exist and not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return file_path


def get_file_size(path: str) -> float:
    """Get file size in MB."""
    return os.path.getsize(path) / (1024 * 1024)