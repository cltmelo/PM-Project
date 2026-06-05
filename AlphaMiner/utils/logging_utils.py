"""
Logging and console output utilities.
"""

from typing import Optional, Any
from datetime import datetime


def print_header(text: str, width: int = 70) -> None:
    """Print a section header with decorative borders."""
    border = "=" * width
    print(f"\n{border}")
    print(text.center(width))
    print(border)


def print_stage(stage_num: int, stage_name: str, width: int = 70) -> None:
    """Print a stage header with stage number."""
    border = "=" * width
    stage_text = f"STAGE {stage_num}: {stage_name}"
    print(f"\n{border}")
    print(stage_text)
    print(border)


def print_info(key: str, value: Any, indent: int = 4) -> None:
    """Print an info line with consistent formatting."""
    spacer = " " * indent
    if isinstance(value, float):
        print(f"{spacer}• {key}: {value:.2f}")
    elif isinstance(value, int):
        print(f"{spacer}• {key}: {value:,}")
    else:
        print(f"{spacer}• {key}: {value}")


def print_success(message: str, indent: int = 4) -> None:
    """Print a success message."""
    spacer = " " * indent
    print(f"{spacer}✅ {message}")


def print_warning(message: str, indent: int = 4) -> None:
    """Print a warning message."""
    spacer = " " * indent
    print(f"{spacer}⚠️ {message}")


def print_error(message: str, indent: int = 4) -> None:
    """Print an error message."""
    spacer = " " * indent
    print(f"{spacer}❌ {message}")


def print_timing(start_time: datetime, end_time: Optional[datetime] = None) -> None:
    """Print timing information."""
    end = end_time or datetime.now()
    duration = (end - start_time).total_seconds()
    print(f"\n⏱️  Duration: {duration:.2f} seconds")