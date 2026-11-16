import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.queue import FileQueue, QueueStatus  # noqa: E402


class FileQueueTests(unittest.TestCase):
    def test_add_skips_unsupported_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = root / "договор.txt"
            text.write_text("Телефон +7 999 123-45-67", encoding="utf-8")
            (root / "image.png").write_bytes(b"png")

            queue = FileQueue()
            added = queue.add([text, text, root / "image.png", root / "missing.txt"])

            self.assertEqual([item.path for item in added], [text])
            self.assertEqual(len(queue.items), 1)
            self.assertEqual(queue.items[0].status, QueueStatus.WAITING)

    def test_process_one_sets_done_and_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.txt"
            source.write_text("Телефон +7 999 123-45-67", encoding="utf-8")
            queue = FileQueue()
            item = queue.add([source])[0]

            queue.process_one(item)

            self.assertEqual(item.status, QueueStatus.DONE)
            self.assertIsNotNone(item.result)
            self.assertEqual(item.result.output_path.name, "input_clean.txt")

    def test_process_one_retains_error_and_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.txt"
            source.write_text("ok", encoding="utf-8")
            queue = FileQueue()
            item = queue.add([source])[0]
            source.unlink()

            queue.process_one(item)

            self.assertEqual(item.status, QueueStatus.ERROR)
            self.assertIn("Файл не найден", item.error)

    def test_remove_and_clear_finished(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = []
            for index in range(3):
                path = root / f"{index}.txt"
                path.write_text("ok", encoding="utf-8")
                paths.append(path)
            queue = FileQueue()
            queue.add(paths)
            queue.items[0].status = QueueStatus.DONE
            queue.items[1].status = QueueStatus.ERROR

            queue.remove([2])
            queue.clear_finished()

            self.assertEqual(queue.items, [])


if __name__ == "__main__":
    unittest.main()
