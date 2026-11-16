"""Application-facing API for the de-Identification engine."""

from .masker import Masker
from .api import (
    DependencyError,
    EngineError,
    InputFileError,
    ProcessingError,
    KeysFormatError,
    MaskResult,
    MaskingConfig,
    RestoreResult,
    UnsupportedFormatError,
    load_mapping,
    mask,
    restore,
)

__all__ = [
    "DependencyError",
    "EngineError",
    "InputFileError",
    "ProcessingError",
    "KeysFormatError",
    "Masker",
    "MaskResult",
    "MaskingConfig",
    "RestoreResult",
    "UnsupportedFormatError",
    "load_mapping",
    "mask",
    "restore",
]
