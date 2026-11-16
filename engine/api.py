"""Stable API around the existing de_Identification.py implementation.

This first extraction changes the dependency boundary, not the masking rules.
"""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Union

import de_Identification


class EngineError(Exception):
    """Base class for expected engine errors."""


class InputFileError(EngineError):
    """The input file is missing or cannot be read."""


class UnsupportedFormatError(EngineError):
    """The input extension is not supported by the prototype."""


class DependencyError(EngineError):
    """An optional processor dependency is unavailable."""


class ProcessingError(EngineError):
    """The file is supported but cannot be processed."""


class KeysFormatError(EngineError):
    """The replacement key has an invalid structure."""


@dataclass(frozen=True)
class MaskingConfig:
    """Configuration boundary reserved for extracted rules and NER settings."""

    enable_ner: bool = True


@dataclass(frozen=True)
class MaskResult:
    """Artifacts and statistics produced by one masking operation."""

    source_path: Path
    output_path: Path
    keys_path: Path
    mapping: Mapping[str, str]
    counters: Mapping[str, int]

    @property
    def unique_entities(self) -> int:
        return len(self.mapping)

    @property
    def total_entities(self) -> int:
        return sum(self.counters.values())


@dataclass(frozen=True)
class RestoreResult:
    """Text restored from replacement tokens."""

    text: str
    replacements: int
    missing_tokens: tuple[str, ...]


def _validate_input(path: Path) -> None:
    if not path.exists():
        raise InputFileError(f"Файл не найден: {path}")
    if not path.is_file():
        raise InputFileError(f"Это не файл: {path}")


def mask(
    path: Union[str, Path], config: Optional[MaskingConfig] = None
) -> MaskResult:
    """Mask one supported file using the existing prototype processors."""
    source = Path(path)
    _validate_input(source)
    masker = de_Identification.Masker(
        enable_ner=True if config is None else config.enable_ner
    )
    processors = {
        ".docx": de_Identification.process_docx,
        ".xlsx": de_Identification.process_xlsx,
        ".pptx": de_Identification.process_pptx,
        ".pdf": de_Identification.process_pdf,
        ".txt": de_Identification.process_text,
        ".md": de_Identification.process_text,
        ".csv": de_Identification.process_text,
    }
    try:
        processor = processors[source.suffix.lower()]
    except KeyError as exc:
        raise UnsupportedFormatError(
            f"Неизвестный формат {source.suffix or '<без расширения>'}"
        ) from exc

    try:
        output = processor(source, masker)
    except ImportError as exc:
        raise DependencyError(
            f"Не установлена зависимость для формата {source.suffix}: {exc.name}"
        ) from exc
    except SystemExit as exc:
        raise ProcessingError(str(exc)) from exc
    except (zipfile.BadZipFile, ValueError) as exc:
        raise ProcessingError(f"Не удалось прочитать файл: {source}") from exc
    except (OSError, UnicodeError) as exc:
        raise InputFileError(f"Не удалось обработать файл: {source}") from exc

    keys_path = source.with_name(source.stem + "_keys.json")
    keys_path.write_text(
        json.dumps({"mapping": masker.mapping}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return MaskResult(
        source_path=source,
        output_path=output,
        keys_path=keys_path,
        mapping=dict(masker.mapping),
        counters=dict(masker.counters),
    )


def _token_pattern(token: str) -> re.Pattern[str]:
    label, number = token.strip("[]").rsplit("_", 1)
    return re.compile(
        r"[\[\(\«\"']?"
        + re.escape(label)
        + r"[\s_]??"
        + re.escape(number)
        + r"[\]\)\»\"']?"
    )


def restore(text: str, mapping: Mapping[str, str]) -> RestoreResult:
    """Restore tokens using the current legacy key format.

    Missing values are reported by token, not by real value, so callers can
    display diagnostics without exposing personal data in logs.
    """
    restored = text
    replacements = 0
    missing: list[str] = []
    for real_value, token in mapping.items():
        try:
            pattern = _token_pattern(token)
        except (AttributeError, ValueError) as exc:
            raise KeysFormatError(f"Некорректный токен ключа: {token!r}") from exc
        restored, count = pattern.subn(lambda _match: real_value, restored)
        replacements += count
        if count == 0:
            missing.append(token)
    return RestoreResult(restored, replacements, tuple(missing))


def load_mapping(path: Union[str, Path]) -> dict[str, str]:
    """Load and validate the legacy ``{"mapping": {real: token}}`` key."""
    keys_path = Path(path)
    try:
        payload = json.loads(keys_path.read_text(encoding="utf-8"))
        mapping = payload["mapping"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError) as exc:
        raise KeysFormatError(f"Не удалось прочитать ключ: {keys_path}") from exc
    if not isinstance(mapping, dict) or not all(
        isinstance(real, str) and isinstance(token, str)
        for real, token in mapping.items()
    ):
        raise KeysFormatError(f"Некорректный формат ключа: {keys_path}")
    return mapping
