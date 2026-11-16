"""PySide6 desktop interface for local PII masking and restoration."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Optional, Union

from PySide6.QtCore import QObject, QThread, Qt, QUrl, Signal, Slot
from PySide6.QtCore import QMimeData
from PySide6.QtGui import QDesktopServices, QDrag
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.queue import FileQueue, SUPPORTED_EXTENSIONS
from engine import MaskingConfig, load_mapping, restore


APP_STYLE = """
QMainWindow { background: #f4f6fa; }
QWidget { color: #172033; font-size: 13px; }
QLabel#title { font-size: 27px; font-weight: 700; }
QLabel#subtitle { color: #667085; font-size: 14px; }
QLabel#sectionTitle { font-size: 16px; font-weight: 700; }
QLabel#hint { color: #667085; }
QPushButton { padding: 9px 15px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; }
QPushButton:hover { background: #edf3ff; border-color: #4778d0; }
QPushButton#primary { color: #fff; background: #2468c8; border-color: #2468c8; font-weight: 700; }
QPushButton#primary:hover { background: #1755ad; }
QPushButton:disabled { color: #98a2b3; background: #eef1f5; }
QListWidget, QTextEdit { background: #fff; border: 1px solid #cfd8e6; border-radius: 10px; padding: 6px; }
QListWidget#dropZone { border: 2px dashed #aebfdc; }
QListWidget#dropZone[dragging="true"] { border-color: #2468c8; background: #f1f6ff; }
QListWidget::item { padding: 9px 7px; border-bottom: 1px solid #eef1f6; }
QListWidget::item:selected { color: #172033; background: #eaf1ff; }
QTabWidget::pane { border: 1px solid #d6deeb; border-radius: 10px; background: #fff; }
QTabBar::tab { min-width: 150px; padding: 12px 24px; color: #667085; }
QTabBar::tab:selected { color: #1755ad; font-weight: 700; border-bottom: 3px solid #2468c8; }
"""


class FileDropList(QListWidget):
    pathsDropped = Signal(list)

    def __init__(self, placeholder: str, extensions: Optional[set[str]] = None) -> None:
        super().__init__()
        self.placeholder = placeholder
        self.extensions = extensions
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDropIndicatorShown(False)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(190)
        self._drag_start_position = None
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self.clear()
        item = QListWidgetItem(self.placeholder)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setForeground(Qt.GlobalColor.gray)
        self.addItem(item)

    def set_paths(self, paths: Iterable[Path], empty_text: Optional[str] = None) -> None:
        self.clear()
        paths = list(paths)
        if not paths:
            item = QListWidgetItem(empty_text or self.placeholder)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.gray)
            self.addItem(item)
            return
        for path in paths:
            item = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.addItem(item)

    def _paths_from_urls(self, urls) -> list[Path]:
        paths: list[Path] = []
        for url in urls:
            path = Path(url.toLocalFile())
            if path.is_dir():
                paths.extend(p for p in path.rglob("*") if p.is_file())
            elif path.is_file():
                paths.append(path)
        if self.extensions is not None:
            paths = [p for p in paths if p.suffix.lower() in self.extensions]
        return paths

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            self.setProperty("dragging", True)
            self.style().unpolish(self)
            self.style().polish(self)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        paths = self._paths_from_urls(event.mimeData().urls())
        if paths:
            self.pathsDropped.emit(paths)
        event.acceptProposedAction()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_start_position is not None:
            distance = (event.position().toPoint() - self._drag_start_position).manhattanLength()
            if distance >= QApplication.startDragDistance():
                item = self.itemAt(self._drag_start_position)
                path = item.data(Qt.ItemDataRole.UserRole) if item else None
                if path:
                    mime = QMimeData()
                    mime.setUrls([QUrl.fromLocalFile(path)])
                    drag = QDrag(self)
                    drag.setMimeData(mime)
                    drag.exec(Qt.DropAction.CopyAction)
                    self._drag_start_position = None
                    return
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        item = self.itemAt(event.position().toPoint())
        path = item.data(Qt.ItemDataRole.UserRole) if item else None
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        super().mouseDoubleClickEvent(event)


class MaskWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal()

    def __init__(self, queue: FileQueue):
        super().__init__()
        self.queue = queue
        self.config = MaskingConfig(enable_ner=True)

    @Slot()
    def run(self) -> None:
        waiting = self.queue.waiting_items()
        total = len(waiting)
        for index, item in enumerate(waiting, 1):
            self.queue.process_one(item, self.config)
            self.progress.emit(index, total, str(item.path))
        self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.queue = FileQueue()
        self.thread: Optional[QThread] = None
        self.worker: Optional[MaskWorker] = None
        self.setWindowTitle("De-identification")
        self.resize(1000, 700)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()
        self._refresh_mask_lists()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)
        title = QLabel("De-identification")
        title.setObjectName("title")
        subtitle = QLabel("Обезличьте документы перед отправкой и верните данные после ответа нейросети.")
        subtitle.setObjectName("subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(self._build_mask_tab(), 1)
        self.setCentralWidget(central)

    def _build_mask_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(20, 20, 20, 20)
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        left_title = self._label("Документы для обезличивания")
        right_title = self._label("Готовые файлы")
        left_hint = self._hint("Перетащите файлы или папку сюда, либо добавьте их через Finder.")
        right_hint = self._hint("После обработки здесь появятся файлы с токенами. Их можно открыть двойным щелчком.")
        left_hint.setFixedHeight(40)
        right_hint.setFixedHeight(40)
        grid.addWidget(left_title, 0, 0)
        grid.addWidget(right_title, 0, 1)
        grid.addWidget(left_hint, 1, 0)
        grid.addWidget(right_hint, 1, 1)

        self.source_list = FileDropList("Перетащите сюда исходные документы", set(SUPPORTED_EXTENSIONS))
        self.clean_list = FileDropList("Готовые файлы появятся здесь", set(SUPPORTED_EXTENSIONS))
        for file_list in (self.source_list, self.clean_list):
            file_list.setFixedHeight(300)
        self.source_list.pathsDropped.connect(self._add_paths)
        self.clean_list.pathsDropped.connect(self._add_clean_files)
        grid.addWidget(self.source_list, 2, 0)
        grid.addWidget(self.clean_list, 2, 1)

        add = QPushButton("Добавить файлы")
        add.clicked.connect(self._choose_files)
        remove = QPushButton("Убрать выбранные")
        remove.clicked.connect(self._remove_selected)
        source_buttons = QHBoxLayout()
        source_buttons.addWidget(add)
        source_buttons.addWidget(remove)
        grid.addLayout(source_buttons, 3, 0)
        grid.addWidget(self._hint("Файлы *_keys.json сохраняются рядом с исходными."), 3, 1)
        root.addLayout(grid, 1)

        bottom = QHBoxLayout()
        self.status_label = QLabel("Добавьте документы для начала")
        self.mask_button = QPushButton("Обезличить файлы")
        self.mask_button.setObjectName("primary")
        self.mask_button.clicked.connect(self._start_masking)
        self.progress = self._build_progress()
        self.progress.hide()
        bottom.addWidget(self.status_label, 1)
        bottom.addWidget(self.progress)
        bottom.addWidget(self.mask_button)
        root.addLayout(bottom)
        return tab

    def _build_restore_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(20, 20, 20, 20)
        columns = QHBoxLayout()
        columns.setSpacing(18)

        token_column = QVBoxLayout()
        token_column.addWidget(self._label("Файлы с токенами"))
        token_column.addWidget(self._hint("Добавьте один или несколько _clean-файлов, полученных после ответа нейросети."))
        self.restore_token_list = FileDropList("Перетащите сюда текстовые файлы с токенами", {".txt", ".md", ".csv"})
        self.restore_token_list.pathsDropped.connect(self._add_restore_tokens)
        token_column.addWidget(self.restore_token_list, 1)
        token_buttons = QHBoxLayout()
        add_tokens = QPushButton("Добавить файлы")
        add_tokens.clicked.connect(self._choose_restore_tokens)
        remove_tokens = QPushButton("Убрать выбранные")
        remove_tokens.clicked.connect(lambda: self._remove_restore_selected(self.restore_token_list, self.restore_token_paths))
        token_buttons.addWidget(add_tokens)
        token_buttons.addWidget(remove_tokens)
        token_column.addLayout(token_buttons)

        key_column = QVBoxLayout()
        key_column.addWidget(self._label("Файлы ключей"))
        key_column.addWidget(self._hint("Добавьте один или несколько *_keys.json. Ключ подберется по имени файла."))
        self.restore_key_list = FileDropList("Перетащите сюда файлы *_keys.json", {".json"})
        self.restore_key_list.pathsDropped.connect(self._add_restore_keys)
        key_column.addWidget(self.restore_key_list, 1)
        key_buttons = QHBoxLayout()
        add_keys = QPushButton("Добавить ключи")
        add_keys.clicked.connect(self._choose_restore_keys)
        remove_keys = QPushButton("Убрать выбранные")
        remove_keys.clicked.connect(lambda: self._remove_restore_selected(self.restore_key_list, self.restore_key_paths))
        key_buttons.addWidget(add_keys)
        key_buttons.addWidget(remove_keys)
        key_column.addLayout(key_buttons)
        columns.addLayout(token_column, 1)
        columns.addLayout(key_column, 1)
        root.addLayout(columns, 1)

        self.restore_status = QLabel("Добавьте файлы с токенами и ключи")
        self.restore_status.setObjectName("hint")
        root.addWidget(self.restore_status)
        self.restore_output = QTextEdit()
        self.restore_output.setReadOnly(True)
        self.restore_output.setPlaceholderText("Здесь появятся расшифрованные файлы")
        self.restore_output.hide()
        root.addWidget(self.restore_output, 1)
        actions = QHBoxLayout()
        actions.addStretch()
        restore_button = QPushButton("Расшифровать файлы")
        restore_button.setObjectName("primary")
        restore_button.clicked.connect(self._restore_files)
        actions.addWidget(restore_button)
        root.addLayout(actions)
        return tab

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    @staticmethod
    def _hint(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("hint")
        label.setWordWrap(True)
        return label

    @staticmethod
    def _build_progress():
        from PySide6.QtWidgets import QProgressBar
        progress = QProgressBar()
        progress.setMinimumWidth(180)
        progress.setTextVisible(True)
        return progress

    def _choose_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Добавить документы", "", "Документы (*.docx *.xlsx *.pptx *.pdf *.txt *.md *.csv)")
        self._add_paths(files)

    def _add_paths(self, paths: Iterable[Union[str, Path]]) -> None:
        expanded: list[Path] = []
        for raw in paths:
            path = Path(raw)
            if path.is_dir():
                expanded.extend(p for p in path.rglob("*") if p.is_file())
            else:
                expanded.append(path)
        added = self.queue.add(expanded)
        self._refresh_mask_lists()
        if added:
            self.status_label.setText(f"Добавлено файлов: {len(added)}")

    def _add_clean_files(self, paths: Iterable[Path]) -> None:
        self._add_paths(paths)

    def _refresh_mask_lists(self) -> None:
        self.source_list.set_paths([item.path for item in self.queue.items], "Перетащите исходные документы сюда")
        outputs = [item.result.output_path for item in self.queue.items if item.result]
        self.clean_list.set_paths(outputs, "Готовые файлы появятся здесь")
        for index, item in enumerate(self.queue.items):
            if index < self.source_list.count() and item.status.value != "ожидает":
                self.source_list.item(index).setText(f"{item.path.name}  —  {item.status.value}")

    def _remove_selected(self) -> None:
        self.queue.remove(index.row() for index in self.source_list.selectedIndexes())
        self._refresh_mask_lists()

    def _start_masking(self) -> None:
        if self.thread is not None and self.thread.isRunning():
            return
        waiting = self.queue.waiting_items()
        if not waiting:
            QMessageBox.information(self, "Нет файлов", "Добавьте документы для обезличивания.")
            return
        self.mask_button.setEnabled(False)
        self.progress.setRange(0, len(waiting))
        self.progress.setValue(0)
        self.progress.show()
        self.worker = MaskWorker(self.queue)
        self.thread = QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self._clear_worker)
        self.thread.start()

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, path: str) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.status_label.setText(f"Обработано {current} из {total}: {Path(path).name}")
        self._refresh_mask_lists()

    @Slot()
    def _on_finished(self) -> None:
        self._refresh_mask_lists()
        self.mask_button.setEnabled(True)
        self.progress.hide()
        completed = sum(item.status.value == "обработан" for item in self.queue.items)
        failed = [item for item in self.queue.items if item.status.value == "ошибка"]
        if failed:
            details = "; ".join(f"{item.path.name}: {item.error}" for item in failed)
            self.status_label.setText(
                f"Создано файлов: {completed}. Ошибок: {len(failed)} — {details}"
            )
        else:
            self.status_label.setText(
                f"Готово. Создано файлов: {completed}. Проверьте файлы справа."
            )

    def _clear_worker(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
        if self.thread is not None:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None

    def _choose_restore_tokens(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Добавить файлы с токенами", "", "Текстовые файлы (*.txt *.md *.csv)")
        self._add_restore_tokens(files)

    def _choose_restore_keys(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Добавить файлы ключей", "", "Ключи (*_keys.json *.json)")
        self._add_restore_keys(files)

    def _add_restore_tokens(self, paths: Iterable[Union[str, Path]]) -> None:
        for raw in paths:
            path = Path(raw)
            if path.is_file() and path not in self.restore_token_paths:
                self.restore_token_paths.append(path)
        self._refresh_restore_lists()

    def _add_restore_keys(self, paths: Iterable[Union[str, Path]]) -> None:
        for raw in paths:
            path = Path(raw)
            if path.is_file() and path not in self.restore_key_paths:
                self.restore_key_paths.append(path)
        self._refresh_restore_lists()

    def _refresh_restore_lists(self) -> None:
        self.restore_token_list.set_paths(self.restore_token_paths, "Перетащите сюда файлы с токенами")
        self.restore_key_list.set_paths(self.restore_key_paths, "Перетащите сюда файлы *_keys.json")

    def _remove_restore_selected(self, widget: QListWidget, paths: list[Path]) -> None:
        selected = {index.row() for index in widget.selectedIndexes()}
        paths[:] = [path for index, path in enumerate(paths) if index not in selected]
        self._refresh_restore_lists()

    @staticmethod
    def _key_for_token(token_path: Path, keys: list[Path]) -> Optional[Path]:
        if len(keys) == 1:
            return keys[0]
        stem = token_path.stem.removesuffix("_clean")
        expected = f"{stem}_keys.json"
        return next((path for path in keys if path.name == expected), None)

    @staticmethod
    def _read_text(path: Path) -> str:
        data = path.read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "cp1251", "mac_cyrillic", "latin-1"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Не удалось определить кодировку файла: {path.name}")

    def _restore_files(self) -> None:
        if not self.restore_token_paths:
            QMessageBox.information(self, "Нет файлов", "Добавьте файлы с токенами.")
            return
        if not self.restore_key_paths:
            QMessageBox.information(self, "Нет ключей", "Добавьте хотя бы один файл *_keys.json.")
            return
        outputs: list[str] = []
        errors: list[str] = []
        for token_path in self.restore_token_paths:
            key_path = self._key_for_token(token_path, self.restore_key_paths)
            if key_path is None:
                errors.append(f"{token_path.name}: не найден подходящий ключ")
                continue
            try:
                result = restore(self._read_text(token_path), load_mapping(key_path))
                output = token_path.with_name(token_path.stem + "_restored.txt")
                output.write_text(result.text, encoding="utf-8")
                outputs.append(f"{output.name} — замен: {result.replacements}, не найдено: {len(result.missing_tokens)}")
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(f"{token_path.name}: {exc}")
        self.restore_output.setPlainText("\n".join(outputs + errors))
        self.restore_output.show()
        self.restore_status.setText(f"Обработано файлов: {len(outputs)}" + (f". Ошибок: {len(errors)}" if errors else ""))


def run() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
