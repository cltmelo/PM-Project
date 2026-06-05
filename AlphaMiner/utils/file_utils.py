"""
File utility functions for path validation and directory management.
"""

import os
from pathlib import Path
from typing import Optional


def ensure_dir(path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to create
        
    Returns:
        The absolute path of the directory
        
    Raises:
        OSError: If directory creation fails
    """
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


def validate_file(path: str, must_exist: bool = True) -> Path:
    """
    Validate that a file exists and return its Path object.
    
    Args:
        path: Path to the file to validate
        must_exist: Whether the file must already exist
        
    Returns:
        Path object for the validated file
        
    Raises:
        FileNotFoundError: If must_exist=True and file doesn't exist
    """
    file_path = Path(path)
    
    if must_exist and not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    return file_path


def get_file_size(path: str) -> float:
    """
    Get the size of a file in megabytes.
    
    Args:
        path: Path to the file
        
    Returns:
        File size in MB
    """
    size_bytes = os.path.getsize(path)
    return size_bytes / (1024 * 1024)


def get_output_path(output_dir: str, filename: str) -> str:
    """
    Construct a full output path.
    
    Args:
        output_dir: Output directory
        filename: Name of the output file
        
    Returns:
        Full path combining directory and filename
    """
    ensure_dir(output_dir)
    return os.path.join(output_dir, filename)