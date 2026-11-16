"""File queue model for the desktop MVP.

This module deliberately has no Qt dependency so queue behavior can be tested
in a headless environment and reused by another UI later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional, Union

from engine import MaskResult, MaskingConfig, mask


SUPPORTED_EXTENSIONS = frozenset({".docx", ".xlsx", ".pptx", ".pdf", ".txt", ".md", ".csv"})


class QueueStatus(str, Enum):
    WAITING = "ожидает"
    PROCESSING = "обрабатывается"
    DONE = "обработан"
    ERROR = "ошибка"


@dataclass
class QueueItem:
    path: Path
    status: QueueStatus = QueueStatus.WAITING
    error: Optional[str] = None
    result: Optional[MaskResult] = None


@dataclass
class FileQueue:
    items: list[QueueItem] = field(default_factory=list)

    def add(self, paths: Iterable[Union[str, Path]]) -> list[QueueItem]:
        """Add valid files, skipping duplicates and unsupported extensions."""
        added: list[QueueItem] = []
        known = {item.path.resolve() for item in self.items}
        for raw_path in paths:
            path = Path(raw_path)
            resolved = path.resolve()
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if resolved in known:
                continue
            item = QueueItem(path=path)
            self.items.append(item)
            added.append(item)
            known.add(resolved)
        return added

    def remove(self, indexes: Iterable[int]) -> None:
        """Remove queue items by index, ignoring stale indexes safely."""
        selected = {index for index in indexes if 0 <= index < len(self.items)}
        self.items = [item for index, item in enumerate(self.items) if index not in selected]

    def clear_finished(self) -> None:
        self.items = [
            item for item in self.items
            if item.status not in (QueueStatus.DONE, QueueStatus.ERROR)
        ]

    def process_one(
        self,
        item: QueueItem,
        config: Optional[MaskingConfig] = None,
    ) -> QueueItem:
        """Process one item and retain a user-safe error message in the item."""
        if item not in self.items:
            raise ValueError("Элемент отсутствует в очереди")
        item.status = QueueStatus.PROCESSING
        item.error = None
        item.result = None
        try:
            item.result = mask(item.path, config)
        except Exception as exc:  # boundary for UI; engine errors remain typed
            item.status = QueueStatus.ERROR
            item.error = str(exc) or "Неизвестная ошибка обработки"
            return item
        item.status = QueueStatus.DONE
        return item

    def waiting_items(self) -> list[QueueItem]:
        return [item for item in self.items if item.status == QueueStatus.WAITING]
