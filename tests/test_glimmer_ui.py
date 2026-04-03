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


def build_archive_fixture(module, glimmer_dir: Path, *, mattered: dict | None = None) -> str:
    sessions_dir = glimmer_dir / "sessions"
    sessions_dir.mkdir(parents=True)

    event_entry = {
        "timestamp": "2026-04-03T10:00:00+00:00",
        "companion": "Glimmer",
        "text": "This is the bubble worth remembering.",
        "source": "auto",
        "bubble_seq": 1,
        "session_id": "sess-1",
        "cwd": "/work/alpha",
        "project_root": "/work/alpha",
        "project_name": "alpha",
        "git_branch": "main",
        "is_repo_root": True,
        "trigger_type": "post_prompt",
        "trigger_confidence": "heuristic",
    }

    write_jsonl(glimmer_dir / "events.jsonl", [event_entry])
    write_jsonl(glimmer_dir / "log.jsonl", [])
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

    bubble_id = module.bubble_id(event_entry)
    if mattered is not None:
        (glimmer_dir / "mattered.json").write_text(
            json.dumps({bubble_id: mattered}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return bubble_id


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
            self.assertEqual(index["overview"]["mattered_count"], 0)
            self.assertEqual(index["bubbles"][0]["text"], "Manual bubble")
            self.assertEqual(index["bubbles"][1]["trigger_type"], "buddy_pet")
            self.assertEqual(index["sessions"][0]["project_label"], "alpha")
            self.assertEqual(index["sessions"][0]["bubble_count"], 1)
            self.assertEqual(index["sessions"][0]["mattered_count"], 0)
            self.assertEqual(index["projects"][0]["project_label"], "alpha")
            self.assertEqual(index["projects"][0]["bubble_count"], 1)
            self.assertEqual(index["projects"][0]["mattered_count"], 0)

    def test_build_index_merges_mattered_notes_into_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_archive_fixture(
                self.module,
                glimmer_dir,
                mattered={
                    "note": "This changed the direction.",
                    "marked_at": "2026-04-03T11:00:00+00:00",
                    "updated_at": "2026-04-03T11:05:00+00:00",
                    "review_state": "open",
                    "reviewed_at": "2026-04-03T11:07:00+00:00",
                },
            )

            index = self.module.build_index(glimmer_dir)

            self.assertEqual(index["overview"]["mattered_count"], 1)
            self.assertTrue(index["bubbles"][0]["mattered"])
            self.assertEqual(index["bubbles"][0]["matter_note"], "This changed the direction.")
            self.assertEqual(index["bubbles"][0]["review_state"], "open")
            self.assertEqual(index["bubbles"][0]["reviewed_at"], "2026-04-03T11:07:00+00:00")
            self.assertEqual(index["sessions"][0]["mattered_count"], 1)
            self.assertEqual(index["projects"][0]["mattered_count"], 1)


class GlimmerUIApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_build_mattered_review_search_and_bubble_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            bubble_id = build_archive_fixture(
                self.module,
                glimmer_dir,
                mattered={
                    "note": "This changed the direction.",
                    "marked_at": "2026-04-03T11:00:00+00:00",
                    "updated_at": "2026-04-03T11:05:00+00:00",
                    "review_state": "open",
                    "reviewed_at": "2026-04-03T11:07:00+00:00",
                },
            )

            index = self.module.build_index(glimmer_dir)
            mattered = self.module.build_mattered_view(index)
            review = self.module.build_review_view(index)
            search = self.module.build_search_view(index, "direction")
            bubble = self.module.build_bubble_view(index, bubble_id)

            self.assertEqual(mattered["count"], 1)
            self.assertEqual(mattered["counts"]["open"], 1)
            self.assertEqual(mattered["bubbles"][0]["id"], bubble_id)
            self.assertEqual(review["counts"]["open"], 1)
            self.assertEqual(review["groups"]["open"][0]["id"], bubble_id)
            self.assertEqual(search["count"], 1)
            self.assertEqual(search["bubbles"][0]["id"], bubble_id)
            self.assertEqual(bubble["bubble"]["id"], bubble_id)
            self.assertEqual(bubble["session"]["session_id"], "sess-1")
            self.assertEqual(bubble["project"]["project_key"], "alpha")

    def test_upsert_matter_defaults_review_state_to_unreviewed(self):
        bubble_id = "bubble-123"
        matters = {}

        matter = self.module.upsert_matter(
            matters,
            bubble_id,
            marked=True,
            note="Worth revisiting later.",
            now="2026-04-03T11:10:00+00:00",
        )

        self.assertEqual(matter["review_state"], "unreviewed")
        self.assertIsNone(matter["reviewed_at"])
        self.assertEqual(matters[bubble_id]["review_state"], "unreviewed")
        self.assertEqual(matters[bubble_id]["marked_at"], "2026-04-03T11:10:00+00:00")

    def test_update_review_state_updates_matter_metadata(self):
        bubble_id = "bubble-123"
        matters = {
            bubble_id: {
                "note": "Keep this around.",
                "marked_at": "2026-04-03T11:00:00+00:00",
                "updated_at": "2026-04-03T11:05:00+00:00",
                "review_state": "unreviewed",
                "reviewed_at": None,
            }
        }

        matter = self.module.update_review_state(
            matters,
            bubble_id,
            "used",
            now="2026-04-03T11:20:00+00:00",
        )

        self.assertEqual(matter["review_state"], "used")
        self.assertEqual(matter["reviewed_at"], "2026-04-03T11:20:00+00:00")
        self.assertEqual(matters[bubble_id]["updated_at"], "2026-04-03T11:20:00+00:00")

    def test_update_review_state_requires_existing_matter(self):
        with self.assertRaises(KeyError):
            self.module.update_review_state({}, "missing", "used")


if __name__ == "__main__":
    unittest.main()
