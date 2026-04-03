import importlib.util
from importlib.machinery import SourceFileLoader
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "glimmer-ui"


def load_module():
    loader = SourceFileLoader("glimmer_ui", str(MODULE_PATH))
    spec = importlib.util.spec_from_loader("glimmer_ui", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class GlimmerUIIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_build_index_dedupes_legacy_auto_entries_and_aggregates_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            sessions_dir = glimmer_dir / "sessions"
            sessions_dir.mkdir(parents=True)

            write_jsonl(
                glimmer_dir / "log.jsonl",
                [
                    {
                        "timestamp": "2026-04-03T10:00:00+00:00",
                        "companion": "Glimmer",
                        "text": "Auto bubble",
                    },
                    {
                        "timestamp": "2026-04-03T11:00:00+00:00",
                        "companion": "Vy",
                        "text": "Manual bubble",
                    },
                ],
            )

            write_jsonl(
                glimmer_dir / "events.jsonl",
                [
                    {
                        "timestamp": "2026-04-03T10:00:00+00:00",
                        "companion": "Glimmer",
                        "text": "Auto bubble",
                        "source": "auto",
                        "bubble_seq": 1,
                        "session_id": "sess-1",
                        "cwd": "/work/alpha",
                        "project_root": "/work/alpha",
                        "project_name": "alpha",
                        "git_branch": "main",
                        "is_repo_root": True,
                        "trigger_type": "buddy_pet",
                        "trigger_confidence": "exact",
                    }
                ],
            )

            (sessions_dir / "sess-1.json").write_text(
                json.dumps(
                    {
                        "session_id": "sess-1",
                        "started_at": "2026-04-03T09:59:00+00:00",
                        "ended_at": "2026-04-03T10:05:00+00:00",
                        "companion": "Glimmer",
                        "cwd": "/work/alpha",
                        "project_root": "/work/alpha",
                        "project_name": "alpha",
                        "git_branch": "main",
                        "is_repo_root": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            index = self.module.build_index(glimmer_dir)

            self.assertEqual(index["overview"]["bubble_count"], 2)
            self.assertEqual(index["overview"]["session_count"], 1)
            self.assertEqual(index["overview"]["project_count"], 1)
            self.assertEqual(index["bubbles"][0]["text"], "Manual bubble")
            self.assertEqual(index["bubbles"][1]["trigger_type"], "buddy_pet")
            self.assertEqual(index["sessions"][0]["project_label"], "alpha")
            self.assertEqual(index["sessions"][0]["bubble_count"], 1)
            self.assertEqual(index["projects"][0]["project_label"], "alpha")
            self.assertEqual(index["projects"][0]["bubble_count"], 1)


if __name__ == "__main__":
    unittest.main()
