import importlib.util
from importlib.machinery import SourceFileLoader
import json
import stat
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
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


def build_recurrence_fixture(module, glimmer_dir: Path) -> dict[str, str]:
    sessions_dir = glimmer_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    events = [
        {
            "timestamp": "2026-04-03T10:00:00+00:00",
            "companion": "Glimmer",
            "text": "Earlier context bubble.",
            "source": "auto",
            "bubble_seq": 1,
            "session_id": "sess-1",
            "cwd": "/work/alpha",
            "project_root": "/work/alpha",
            "project_name": "alpha",
            "git_branch": "main",
            "is_repo_root": True,
            "trigger_type": "unknown",
            "trigger_confidence": "none",
        },
        {
            "timestamp": "2026-04-03T10:02:00+00:00",
            "companion": "Glimmer",
            "text": "Direction signal worth remembering.",
            "source": "auto",
            "bubble_seq": 2,
            "session_id": "sess-1",
            "cwd": "/work/alpha",
            "project_root": "/work/alpha",
            "project_name": "alpha",
            "git_branch": "main",
            "is_repo_root": True,
            "trigger_type": "post_prompt",
            "trigger_confidence": "heuristic",
        },
        {
            "timestamp": "2026-04-03T10:03:00+00:00",
            "companion": "Glimmer",
            "text": "Later context bubble with direction signal.",
            "source": "auto",
            "bubble_seq": 3,
            "session_id": "sess-1",
            "cwd": "/work/alpha",
            "project_root": "/work/alpha",
            "project_name": "alpha",
            "git_branch": "main",
            "is_repo_root": True,
            "trigger_type": "unknown",
            "trigger_confidence": "none",
        },
        {
            "timestamp": "2026-04-03T11:10:00+00:00",
            "companion": "Glimmer",
            "text": "Recurring direction signal in beta.",
            "source": "auto",
            "bubble_seq": 1,
            "session_id": "sess-2",
            "cwd": "/work/beta",
            "project_root": "/work/beta",
            "project_name": "beta",
            "git_branch": "main",
            "is_repo_root": True,
            "trigger_type": "unknown",
            "trigger_confidence": "none",
        },
    ]
    write_jsonl(glimmer_dir / "events.jsonl", events)
    write_jsonl(glimmer_dir / "log.jsonl", [])

    manifests = [
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
        {
            "session_id": "sess-2",
            "started_at": "2026-04-03T11:09:00+00:00",
            "ended_at": "2026-04-03T11:12:00+00:00",
            "companion": "Glimmer",
            "cwd": "/work/beta",
            "project_root": "/work/beta",
            "project_name": "beta",
            "git_branch": "main",
            "is_repo_root": True,
        },
    ]
    for manifest in manifests:
        (sessions_dir / f'{manifest["session_id"]}.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    ids = {
        "before": module.bubble_id(events[0]),
        "focus": module.bubble_id(events[1]),
        "after": module.bubble_id(events[2]),
        "beta": module.bubble_id(events[3]),
    }
    (glimmer_dir / "mattered.json").write_text(
        json.dumps(
            {
                ids["focus"]: {
                    "note": "Need review on direction signal",
                    "context": "hint",
                    "marked_at": "2026-04-03T10:06:00+00:00",
                    "updated_at": "2026-04-03T10:06:00+00:00",
                    "review_state": "unreviewed",
                    "reviewed_at": None,
                },
                ids["after"]: {
                    "note": "Direction signal remains open in alpha",
                    "context": "comment",
                    "marked_at": "2026-04-03T10:07:00+00:00",
                    "updated_at": "2026-04-03T10:08:00+00:00",
                    "review_state": "open",
                    "reviewed_at": "2026-04-03T10:08:00+00:00",
                },
                ids["beta"]: {
                    "note": "Direction signal recurring concern in beta",
                    "context": "random",
                    "marked_at": "2026-04-03T11:11:00+00:00",
                    "updated_at": "2026-04-03T11:12:00+00:00",
                    "review_state": "used",
                    "reviewed_at": "2026-04-03T11:12:00+00:00",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return ids


def build_staleness_fixture(module, glimmer_dir: Path) -> dict[str, str]:
    sessions_dir = glimmer_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    events = [
        {
            "timestamp": "2026-03-20T10:00:00+00:00",
            "companion": "Glimmer",
            "text": "Active open thread.",
            "source": "auto",
            "bubble_seq": 1,
            "session_id": "sess-1",
            "cwd": "/work/alpha",
            "project_root": "/work/alpha",
            "project_name": "alpha",
            "git_branch": "main",
            "is_repo_root": True,
            "trigger_type": "unknown",
            "trigger_confidence": "none",
        },
        {
            "timestamp": "2026-03-01T10:00:00+00:00",
            "companion": "Glimmer",
            "text": "Never revisited mattered note.",
            "source": "auto",
            "bubble_seq": 2,
            "session_id": "sess-1",
            "cwd": "/work/alpha",
            "project_root": "/work/alpha",
            "project_name": "alpha",
            "git_branch": "main",
            "is_repo_root": True,
            "trigger_type": "unknown",
            "trigger_confidence": "none",
        },
        {
            "timestamp": "2026-03-02T10:00:00+00:00",
            "companion": "Glimmer",
            "text": "Used once and now cooling off.",
            "source": "auto",
            "bubble_seq": 3,
            "session_id": "sess-1",
            "cwd": "/work/alpha",
            "project_root": "/work/alpha",
            "project_name": "alpha",
            "git_branch": "main",
            "is_repo_root": True,
            "trigger_type": "unknown",
            "trigger_confidence": "none",
        },
        {
            "timestamp": "2026-02-28T10:00:00+00:00",
            "companion": "Glimmer",
            "text": "Frequently resurfaced signal.",
            "source": "auto",
            "bubble_seq": 4,
            "session_id": "sess-1",
            "cwd": "/work/alpha",
            "project_root": "/work/alpha",
            "project_name": "alpha",
            "git_branch": "main",
            "is_repo_root": True,
            "trigger_type": "unknown",
            "trigger_confidence": "none",
        },
    ]
    write_jsonl(glimmer_dir / "events.jsonl", events)
    write_jsonl(glimmer_dir / "log.jsonl", [])
    (sessions_dir / "sess-1.json").write_text(
        json.dumps(
            {
                "session_id": "sess-1",
                "started_at": "2026-02-28T09:59:00+00:00",
                "ended_at": "2026-03-20T10:05:00+00:00",
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

    ids = {
        "active_open": module.bubble_id(events[0]),
        "never_used": module.bubble_id(events[1]),
        "fading_used": module.bubble_id(events[2]),
        "high_use": module.bubble_id(events[3]),
    }
    (glimmer_dir / "mattered.json").write_text(
        json.dumps(
            {
                ids["active_open"]: {
                    "note": "Still in flight.",
                    "marked_at": "2026-03-21T10:00:00+00:00",
                    "updated_at": "2026-03-21T10:00:00+00:00",
                    "review_state": "open",
                    "reviewed_at": "2026-03-21T10:00:00+00:00",
                },
                ids["never_used"]: {
                    "note": "Important but forgotten.",
                    "marked_at": "2026-03-05T10:00:00+00:00",
                    "updated_at": "2026-03-05T10:00:00+00:00",
                    "review_state": "unreviewed",
                    "reviewed_at": None,
                },
                ids["fading_used"]: {
                    "note": "Was useful once.",
                    "marked_at": "2026-03-06T10:00:00+00:00",
                    "updated_at": "2026-03-10T10:00:00+00:00",
                    "review_state": "used",
                    "reviewed_at": "2026-03-10T10:00:00+00:00",
                },
                ids["high_use"]: {
                    "note": "Keeps coming back.",
                    "marked_at": "2026-03-02T10:00:00+00:00",
                    "updated_at": "2026-03-15T10:00:00+00:00",
                    "review_state": "used",
                    "reviewed_at": "2026-03-15T10:00:00+00:00",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (glimmer_dir / "usage.json").write_text(
        json.dumps(
            {
                ids["active_open"]: {
                    "last_used_at": "2026-04-04T10:00:00+00:00",
                    "use_count": 1,
                    "use_sources": ["ui.detail"],
                },
                ids["fading_used"]: {
                    "last_used_at": "2026-03-20T10:00:00+00:00",
                    "use_count": 1,
                    "use_sources": ["mcp.get_bubble"],
                },
                ids["high_use"]: {
                    "last_used_at": "2026-03-10T10:00:00+00:00",
                    "use_count": 4,
                    "use_sources": ["ui.detail", "ui.brief"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return ids


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
                    "context": "hint",
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
            self.assertEqual(index["bubbles"][0]["matter_context"], "hint")
            self.assertEqual(index["bubbles"][0]["review_state"], "active")
            self.assertEqual(index["bubbles"][0]["reviewed_at"], "2026-04-03T11:07:00+00:00")
            self.assertEqual(index["sessions"][0]["mattered_count"], 1)
            self.assertEqual(index["projects"][0]["mattered_count"], 1)

    def test_build_index_merges_usage_into_bubbles(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            bubble_id = build_archive_fixture(self.module, glimmer_dir)
            self.module.save_usage(
                glimmer_dir / self.module.USAGE_FILE,
                {
                    bubble_id: {
                        "last_used_at": "2026-04-05T10:15:00+00:00",
                        "use_count": 4,
                        "use_sources": ["ui.detail", "mcp.get_bubble"],
                    }
                },
            )

            index = self.module.build_index(glimmer_dir)

            self.assertEqual(index["bubbles"][0]["last_used_at"], "2026-04-05T10:15:00+00:00")
            self.assertEqual(index["bubbles"][0]["use_count"], 4)
            self.assertEqual(
                index["bubbles"][0]["use_sources"],
                ["mcp.get_bubble", "ui.detail"],
            )

    def test_build_index_derives_staleness_from_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            ids = build_staleness_fixture(self.module, glimmer_dir)

            index = self.module.build_index(glimmer_dir, now="2026-04-05T12:00:00+00:00")
            by_id = {bubble["id"]: bubble for bubble in index["bubbles"]}

            self.assertEqual(by_id[ids["active_open"]]["staleness_bucket"], "active")
            self.assertEqual(by_id[ids["active_open"]]["days_since_used"], 1)
            self.assertEqual(by_id[ids["never_used"]]["staleness_bucket"], "stale")
            self.assertEqual(by_id[ids["never_used"]]["days_since_mattered"], 31)
            self.assertIn("never revisited", by_id[ids["never_used"]]["staleness_reason"])
            self.assertEqual(by_id[ids["fading_used"]]["staleness_bucket"], "fading")
            self.assertEqual(by_id[ids["fading_used"]]["days_since_used"], 16)
            self.assertEqual(by_id[ids["high_use"]]["staleness_bucket"], "active")
            self.assertEqual(by_id[ids["high_use"]]["use_count"], 4)


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
                    "context": "hint",
                    "marked_at": "2026-04-03T11:00:00+00:00",
                    "updated_at": "2026-04-03T11:05:00+00:00",
                    "review_state": "open",
                    "reviewed_at": "2026-04-03T11:07:00+00:00",
                },
            )

            index = self.module.build_index(glimmer_dir)
            mattered = self.module.build_mattered_view(index)
            review = self.module.build_review_view(index)
            search = self.module.build_search_view(
                index,
                "",
                mattered_only=True,
                review_states=["active"],
                contexts=["hint"],
                has_note=True,
            )
            bubble = self.module.build_bubble_view(index, bubble_id)

            self.assertEqual(mattered["count"], 1)
            self.assertEqual(mattered["counts"]["active"], 1)
            self.assertEqual(mattered["bubbles"][0]["id"], bubble_id)
            self.assertEqual(review["counts"]["active"], 1)
            self.assertEqual(review["groups"]["active"][0]["id"], bubble_id)
            self.assertEqual(search["count"], 1)
            self.assertEqual(search["filters"]["contexts"], ["hint"])
            self.assertEqual(search["bubbles"][0]["id"], bubble_id)
            self.assertEqual(bubble["bubble"]["id"], bubble_id)
            self.assertEqual(bubble["session"]["session_id"], "sess-1")
            self.assertEqual(bubble["project"]["project_key"], "alpha")

    def test_build_search_view_supports_filter_only_queries_and_pagination(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            ids = build_recurrence_fixture(self.module, glimmer_dir)

            index = self.module.build_index(glimmer_dir)
            search = self.module.build_search_view(
                index,
                "",
                mattered_only=True,
                staleness=["active", "fading", "stale"],
                contexts=["comment"],
                has_note=True,
                limit=1,
                offset=0,
            )

            self.assertEqual(search["count"], 1)
            self.assertEqual(search["returned_count"], 1)
            self.assertFalse(search["truncated"])
            self.assertEqual(search["bubbles"][0]["id"], ids["after"])

    def test_normalize_bubble_includes_session_profile(self):
        entry = {
            "timestamp": "2026-04-05T00:00:00+00:00",
            "companion": "Glimmer",
            "text": "hello",
            "session_profile": "pet",
        }
        bubble = self.module.normalize_bubble(entry, "events")
        self.assertEqual(bubble["session_profile"], "pet")

    def test_normalize_bubble_session_profile_none_when_absent(self):
        entry = {
            "timestamp": "2026-04-05T00:00:00+00:00",
            "companion": "Glimmer",
            "text": "hello",
        }
        bubble = self.module.normalize_bubble(entry, "events")
        self.assertIsNone(bubble["session_profile"])

    def test_build_search_view_filters_by_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            sessions_dir = glimmer_dir / "sessions"
            sessions_dir.mkdir(parents=True)

            event_pet = {
                "timestamp": "2026-04-05T10:00:00+00:00",
                "companion": "Glimmer",
                "text": "bubble",
                "source": "auto",
                "bubble_seq": 1,
                "session_id": "pet-sess",
                "cwd": "/work",
                "project_root": "/work",
                "project_name": "work",
                "git_branch": "main",
                "is_repo_root": True,
                "session_profile": "pet",
                "trigger_type": "buddy_pet",
                "trigger_confidence": "exact",
            }

            event_normal = {
                "timestamp": "2026-04-05T11:00:00+00:00",
                "companion": "Glimmer",
                "text": "bubble",
                "source": "auto",
                "bubble_seq": 1,
                "session_id": "normal-sess",
                "cwd": "/work",
                "project_root": "/work",
                "project_name": "work",
                "git_branch": "main",
                "is_repo_root": True,
                "session_profile": None,
                "trigger_type": "unknown",
                "trigger_confidence": "none",
            }

            eventsfile = glimmer_dir / "events.jsonl"
            write_jsonl(eventsfile, [event_pet, event_normal])

            index = self.module.build_index(glimmer_dir)
            search_pet = self.module.build_search_view(index, "bubble", profile="pet")
            search_all = self.module.build_search_view(index, "bubble")

            self.assertEqual(search_pet["count"], 1)
            self.assertEqual(search_pet["bubbles"][0]["session_profile"], "pet")
            self.assertEqual(search_all["count"], 2)

    def test_build_search_view_profile_filter_normalizes_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            sessions_dir = glimmer_dir / "sessions"
            sessions_dir.mkdir(parents=True)

            event = {
                "timestamp": "2026-04-05T10:00:00+00:00",
                "companion": "Glimmer",
                "text": "test",
                "source": "auto",
                "bubble_seq": 1,
                "session_id": "sess",
                "cwd": "/work",
                "project_root": "/work",
                "project_name": "work",
                "git_branch": "main",
                "is_repo_root": True,
                "session_profile": "pet",
                "trigger_type": "unknown",
                "trigger_confidence": "none",
            }

            eventsfile = glimmer_dir / "events.jsonl"
            write_jsonl(eventsfile, [event])

            index = self.module.build_index(glimmer_dir)
            search = self.module.build_search_view(index, "", profile="  PET  ")

            self.assertEqual(search["count"], 1)

    def test_review_and_bubble_views_include_resurface_and_recurrence_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            ids = build_recurrence_fixture(self.module, glimmer_dir)

            index = self.module.build_index(glimmer_dir)
            review = self.module.build_review_view(index)
            bubble = self.module.build_bubble_view(index, ids["focus"])

            self.assertEqual(review["counts"]["mattered"], 3)
            self.assertEqual(
                {hint["key"] for hint in review["hints"]},
                {"needs_review", "oldest_active", "recurring"},
            )
            self.assertEqual(bubble["previous_bubble"]["id"], ids["before"])
            self.assertEqual(bubble["next_bubble"]["id"], ids["after"])
            self.assertEqual(bubble["related_mattered"][0]["id"], ids["after"])
            self.assertEqual(len(bubble["recurrence_matches"]), 2)
            self.assertEqual(bubble["recurrence_matches"][0]["bubble"]["id"], ids["after"])
            self.assertEqual(
                {match["bubble"]["id"] for match in bubble["recurrence_matches"]},
                {ids["after"], ids["beta"]},
            )
            self.assertIn("direction", bubble["recurrence_matches"][0]["shared_tokens"])

    def test_build_brief_view_scopes_to_project_and_infers_from_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            ids = build_recurrence_fixture(self.module, glimmer_dir)

            index = self.module.build_index(glimmer_dir)
            brief = self.module.build_brief_view(index, project="alpha")
            inferred = self.module.build_brief_view(index, cwd="/work/alpha/src")

            self.assertEqual(brief["scope"]["project_key"], "alpha")
            self.assertEqual(brief["scope"]["source"], "project")
            self.assertEqual(brief["summary"]["mattered_count"], 2)
            self.assertEqual(brief["summary"]["active_count"], 1)
            self.assertEqual(brief["summary"]["unreviewed_count"], 1)
            self.assertEqual(brief["top_mattered"][0]["id"], ids["after"])
            self.assertEqual(
                {bubble["id"] for bubble in brief["open_items"]},
                {ids["focus"], ids["after"]},
            )
            self.assertEqual(brief["recurring_signals"][0]["bubble"]["id"], ids["after"])
            self.assertEqual(inferred["scope"]["project_key"], "alpha")
            self.assertEqual(inferred["scope"]["source"], "cwd")

    def test_review_and_brief_surface_staleness(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            ids = build_staleness_fixture(self.module, glimmer_dir)

            index = self.module.build_index(glimmer_dir, now="2026-04-05T12:00:00+00:00")
            review = self.module.build_review_view(index)
            brief = self.module.build_brief_view(index, project="alpha")
            bubble = self.module.build_bubble_view(index, ids["never_used"])

            self.assertEqual(review["staleness_counts"]["active"], 2)
            self.assertEqual(review["staleness_counts"]["fading"], 1)
            self.assertEqual(review["staleness_counts"]["stale"], 1)
            self.assertIn("cooling_off", {hint["key"] for hint in review["hints"]})
            self.assertEqual(brief["summary"]["active_signal_count"], 2)
            self.assertEqual(brief["summary"]["fading_signal_count"], 1)
            self.assertEqual(brief["summary"]["stale_signal_count"], 1)
            self.assertEqual(
                [entry["id"] for entry in brief["resurface_now"]],
                [ids["never_used"], ids["fading_used"]],
            )
            self.assertEqual(bubble["bubble"]["staleness_bucket"], "stale")
            self.assertIn("never revisited", bubble["bubble"]["staleness_reason"])

    def test_upsert_matter_defaults_review_state_to_unreviewed(self):
        bubble_id = "bubble-123"
        matters = {}

        matter = self.module.upsert_matter(
            matters,
            bubble_id,
            marked=True,
            note="Worth revisiting later.",
            context="hint",
            now="2026-04-03T11:10:00+00:00",
        )

        self.assertEqual(matter["review_state"], "unreviewed")
        self.assertEqual(matter["context"], "hint")
        self.assertIsNone(matter["reviewed_at"])
        self.assertEqual(matters[bubble_id]["review_state"], "unreviewed")
        self.assertEqual(matters[bubble_id]["context"], "hint")
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
            "resolved",
            now="2026-04-03T11:20:00+00:00",
        )

        self.assertEqual(matter["review_state"], "resolved")
        self.assertEqual(matter["reviewed_at"], "2026-04-03T11:20:00+00:00")
        self.assertEqual(matters[bubble_id]["updated_at"], "2026-04-03T11:20:00+00:00")

    def test_update_review_state_requires_existing_matter(self):
        with self.assertRaises(KeyError):
            self.module.update_review_state({}, "missing", "resolved")

    def test_update_review_state_accepts_legacy_aliases(self):
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

        self.assertEqual(matter["review_state"], "resolved")

    def test_save_matters_writes_private_file_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            matters_path = glimmer_dir / "mattered.json"

            self.module.save_matters(
                matters_path,
                {
                    "bubble-1": {
                        "note": "Keep this.",
                        "marked_at": "2026-04-03T11:00:00+00:00",
                        "updated_at": "2026-04-03T11:00:00+00:00",
                        "review_state": "open",
                        "reviewed_at": "2026-04-03T11:00:00+00:00",
                    }
                },
            )

            mode = stat.S_IMODE(matters_path.stat().st_mode)
            self.assertEqual(mode, self.module.PRIVATE_FILE_MODE)
            stored = json.loads(matters_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["bubble-1"]["review_state"], "active")
            self.assertEqual(
                list(glimmer_dir.glob(".mattered.json.*.tmp")),
                [],
            )

    def test_save_usage_writes_private_file_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            usage_path = glimmer_dir / "usage.json"

            self.module.save_usage(
                usage_path,
                {
                    "bubble-1": {
                        "last_used_at": "2026-04-05T10:15:00+00:00",
                        "use_count": 2,
                        "use_sources": ["ui.detail"],
                    }
                },
            )

            mode = stat.S_IMODE(usage_path.stat().st_mode)
            self.assertEqual(mode, self.module.PRIVATE_FILE_MODE)
            self.assertEqual(list(glimmer_dir.glob(".usage.json.*.tmp")), [])

    def test_mutate_matters_updates_existing_state_under_one_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            matters_path = glimmer_dir / "mattered.json"

            self.module.save_matters(
                matters_path,
                {
                    "bubble-1": {
                        "note": "Keep this.",
                        "marked_at": "2026-04-03T11:00:00+00:00",
                        "updated_at": "2026-04-03T11:00:00+00:00",
                        "review_state": "open",
                        "reviewed_at": "2026-04-03T11:00:00+00:00",
                    }
                },
            )

            def updater(matters):
                matters["bubble-2"] = {
                    "note": "Add another.",
                    "marked_at": "2026-04-03T11:05:00+00:00",
                    "updated_at": "2026-04-03T11:05:00+00:00",
                    "review_state": "unreviewed",
                    "reviewed_at": None,
                }
                return sorted(matters)

            result = self.module.mutate_matters(matters_path, updater)
            matters = self.module.load_matters(matters_path)

            self.assertEqual(result, ["bubble-1", "bubble-2"])
            self.assertEqual(sorted(matters), ["bubble-1", "bubble-2"])

    def test_mutate_usage_updates_existing_state_under_one_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            usage_path = glimmer_dir / "usage.json"

            self.module.save_usage(
                usage_path,
                {
                    "bubble-1": {
                        "last_used_at": "2026-04-05T10:15:00+00:00",
                        "use_count": 1,
                        "use_sources": ["ui.detail"],
                    }
                },
            )

            def updater(usage):
                usage["bubble-2"] = {
                    "last_used_at": "2026-04-05T10:20:00+00:00",
                    "use_count": 3,
                    "use_sources": ["mcp.get_brief"],
                }
                return sorted(usage)

            result = self.module.mutate_usage(usage_path, updater)
            usage = self.module.load_usage(usage_path)

            self.assertEqual(result, ["bubble-1", "bubble-2"])
            self.assertEqual(sorted(usage), ["bubble-1", "bubble-2"])

    def test_record_usage_dedupes_unknown_ids_and_keeps_sources_unique(self):
        usage = {
            "bubble-1": {
                "last_used_at": "2026-04-05T10:15:00+00:00",
                "use_count": 1,
                "use_sources": ["ui.detail", "not-real"],
            }
        }

        recorded = self.module.record_usage(
            usage,
            ["bubble-1", "bubble-1", "missing", "bubble-2"],
            "ui.detail",
            known_bubble_ids={"bubble-1", "bubble-2"},
            now="2026-04-05T10:30:00+00:00",
        )

        self.assertEqual(recorded, ["bubble-1", "bubble-2"])
        self.assertEqual(usage["bubble-1"]["last_used_at"], "2026-04-05T10:30:00+00:00")
        self.assertEqual(usage["bubble-1"]["use_count"], 2)
        self.assertEqual(usage["bubble-1"]["use_sources"], ["ui.detail"])
        self.assertEqual(usage["bubble-2"]["use_count"], 1)
        self.assertEqual(usage["bubble-2"]["use_sources"], ["ui.detail"])

    def test_bind_host_validation_requires_explicit_remote_opt_in(self):
        self.module.validate_bind_host("127.0.0.1", allow_remote=False)
        self.module.validate_bind_host("localhost", allow_remote=False)
        self.module.validate_bind_host("0.0.0.0", allow_remote=True)

        with self.assertRaises(SystemExit):
            self.module.validate_bind_host("0.0.0.0", allow_remote=False)

    def test_origin_matching_requires_same_host_and_port(self):
        self.assertTrue(
            self.module.origin_matches_host(
                "http://127.0.0.1:8767/api/matters",
                "127.0.0.1:8767",
                8767,
            )
        )
        self.assertTrue(
            self.module.origin_matches_host(
                "http://localhost/api/matters",
                "localhost",
                80,
            )
        )
        self.assertFalse(
            self.module.origin_matches_host(
                "http://evil.example/api/matters",
                "127.0.0.1:8767",
                8767,
            )
        )
        self.assertFalse(
            self.module.origin_matches_host(
                "http://127.0.0.1:9999/api/matters",
                "127.0.0.1:8767",
                8767,
            )
        )

    def test_basic_auth_matching_requires_valid_credentials(self):
        token = "Basic " + __import__("base64").b64encode(
            b"glimmer:secret-token"
        ).decode("ascii")

        self.assertTrue(
            self.module.authorization_matches_basic_auth(
                token,
                "glimmer",
                "secret-token",
            )
        )
        self.assertFalse(
            self.module.authorization_matches_basic_auth(
                token,
                "glimmer",
                "wrong-token",
            )
        )
        self.assertFalse(
            self.module.authorization_matches_basic_auth(
                "Bearer secret-token",
                "glimmer",
                "secret-token",
            )
        )

    def test_remote_auth_requires_password_for_non_loopback_bind(self):
        self.module.validate_remote_auth("127.0.0.1", True, None)
        self.module.validate_remote_auth("0.0.0.0", True, "secret-token")

        with self.assertRaises(SystemExit):
            self.module.validate_remote_auth("0.0.0.0", True, None)

    def test_usage_sources_includes_auto_session_start(self):
        self.assertIn("auto.session_start", self.module.USAGE_SOURCES)

    def test_build_brief_view_filters_by_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            events = [
                {
                    "timestamp": "2026-04-05T10:00:00+00:00",
                    "companion": "Glimmer",
                    "text": "pet moment",
                    "source": "auto",
                    "bubble_seq": 1,
                    "session_id": "sess-pet",
                    "cwd": "/work/alpha",
                    "project_root": "/work/alpha",
                    "project_name": "alpha",
                    "session_profile": "pet",
                    "trigger_type": "unknown",
                    "trigger_confidence": "none",
                },
                {
                    "timestamp": "2026-04-05T10:01:00+00:00",
                    "companion": "Glimmer",
                    "text": "work moment",
                    "source": "auto",
                    "bubble_seq": 2,
                    "session_id": "sess-work",
                    "cwd": "/work/alpha",
                    "project_root": "/work/alpha",
                    "project_name": "alpha",
                    "session_profile": None,
                    "trigger_type": "unknown",
                    "trigger_confidence": "none",
                },
            ]
            write_jsonl(glimmer_dir / "events.jsonl", events)
            write_jsonl(glimmer_dir / "log.jsonl", [])
            (glimmer_dir / "sessions").mkdir()
            index = self.module.build_index(glimmer_dir)
            pet_brief = self.module.build_brief_view(index, project="alpha", profile="pet")
            for bubble in pet_brief.get("top_mattered") or []:
                self.assertEqual(bubble.get("session_profile"), "pet")

    def test_build_brief_view_profile_none_no_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_archive_fixture(self.module, glimmer_dir)
            index = self.module.build_index(glimmer_dir)
            brief = self.module.build_brief_view(index)
            self.assertIn("top_mattered", brief)


class GlimmerUIServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def start_server(self, glimmer_dir: Path, *, auth_password: str | None = None):
        try:
            server = self.module.ThreadingHTTPServer(
                ("127.0.0.1", 0),
                self.module.GlimmerUIHandler,
            )
        except PermissionError:
            self.skipTest("sandbox does not allow local socket binds")
        server.config = {  # type: ignore[attr-defined]
            "glimmer_dir": glimmer_dir,
            "ui_dir": REPO_ROOT / "ui",
            "allow_remote": False,
            "auth_user": "glimmer",
            "auth_password": auth_password,
        }
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 1)
        return server

    def post_json(self, url: str, payload: dict):
        request = urllib.request.Request(
            url,
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        return urllib.request.urlopen(request)

    def test_health_endpoint_returns_security_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = self.start_server(Path(tmp))
            url = f"http://127.0.0.1:{server.server_port}/api/health"

            with urllib.request.urlopen(url) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(payload, {"ok": True})
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    def test_auth_protects_server_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = self.start_server(Path(tmp), auth_password="secret-token")
            url = f"http://127.0.0.1:{server.server_port}/api/health"

            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(url)
            self.assertEqual(ctx.exception.code, 401)

            auth = __import__("base64").b64encode(
                b"glimmer:secret-token"
            ).decode("ascii")
            request = urllib.request.Request(
                url,
                headers={"Authorization": f"Basic {auth}"},
            )
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(payload, {"ok": True})

    def test_brief_and_bubble_detail_record_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            ids = build_recurrence_fixture(self.module, glimmer_dir)
            server = self.start_server(glimmer_dir)

            brief_url = (
                f"http://127.0.0.1:{server.server_port}/api/brief"
                "?project=alpha&source=ui.brief"
            )
            with urllib.request.urlopen(brief_url) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["scope"]["project_key"], "alpha")

            usage = self.module.load_usage(glimmer_dir / self.module.USAGE_FILE)
            self.assertEqual(usage[ids["focus"]]["use_count"], 1)
            self.assertEqual(usage[ids["focus"]]["use_sources"], ["ui.brief"])
            self.assertEqual(usage[ids["after"]]["use_count"], 1)
            self.assertEqual(usage[ids["after"]]["use_sources"], ["ui.brief"])
            self.assertNotIn(ids["beta"], usage)

            bubble_url = (
                f"http://127.0.0.1:{server.server_port}/api/bubbles/{ids['focus']}"
                "?source=ui.search_open"
            )
            with urllib.request.urlopen(bubble_url) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["bubble"]["id"], ids["focus"])

            usage = self.module.load_usage(glimmer_dir / self.module.USAGE_FILE)
            self.assertEqual(usage[ids["focus"]]["use_count"], 2)
            self.assertEqual(
                usage[ids["focus"]]["use_sources"],
                ["ui.brief", "ui.search_open"],
            )

    def test_matter_and_review_post_endpoints_record_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            bubble_id = build_archive_fixture(self.module, glimmer_dir)
            server = self.start_server(glimmer_dir)

            with self.post_json(
                f"http://127.0.0.1:{server.server_port}/api/matters",
                {
                    "bubble_id": bubble_id,
                    "marked": True,
                    "note": "Keep this one.",
                    "context": "comment",
                },
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["matter"]["context"], "comment")

            usage = self.module.load_usage(glimmer_dir / self.module.USAGE_FILE)
            self.assertEqual(usage[bubble_id]["use_count"], 1)
            self.assertEqual(usage[bubble_id]["use_sources"], ["ui.matter_toggle"])
            stored_matters = self.module.load_matters(glimmer_dir / self.module.MATTERS_FILE)
            self.assertEqual(stored_matters[bubble_id]["context"], "comment")

            with self.post_json(
                f"http://127.0.0.1:{server.server_port}/api/review-state",
                {
                    "bubble_id": bubble_id,
                    "review_state": "used",
                },
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["ok"])

            usage = self.module.load_usage(glimmer_dir / self.module.USAGE_FILE)
            self.assertEqual(usage[bubble_id]["use_count"], 2)
            self.assertEqual(
                usage[bubble_id]["use_sources"],
                ["ui.matter_toggle", "ui.review_state"],
            )

    def test_search_endpoint_supports_filter_only_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_archive_fixture(
                self.module,
                glimmer_dir,
                mattered={
                    "note": "This changed the direction.",
                    "context": "hint",
                    "marked_at": "2026-04-03T11:00:00+00:00",
                    "updated_at": "2026-04-03T11:05:00+00:00",
                    "review_state": "open",
                    "reviewed_at": "2026-04-03T11:07:00+00:00",
                },
            )
            server = self.start_server(glimmer_dir)

            search_url = (
                f"http://127.0.0.1:{server.server_port}/api/search"
                "?mattered_only=1&review_state=active&context=hint&has_note=1"
            )
            with urllib.request.urlopen(search_url) as response:
                payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["filters"]["contexts"], ["hint"])
            self.assertEqual(payload["filters"]["review_states"], ["active"])
            self.assertEqual(payload["bubbles"][0]["matter_context"], "hint")


class EmoteStateClassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_derive_state_class_known_verbs(self):
        m = self.module
        self.assertEqual(m.derive_state_class({"emote_verb": "drifts"}), "observing")
        self.assertEqual(m.derive_state_class({"emote_verb": "hovers"}), "observing")
        self.assertEqual(m.derive_state_class({"emote_verb": "flickers"}), "uncertain")
        self.assertEqual(m.derive_state_class({"emote_verb": "phases"}), "transitioning")
        self.assertEqual(m.derive_state_class({"emote_verb": "shimmers"}), "warm")
        self.assertEqual(m.derive_state_class({"emote_verb": "glows"}), "warm")
        self.assertEqual(m.derive_state_class({"emote_verb": "settles"}), "calm")
        self.assertEqual(m.derive_state_class({"emote_verb": "dims"}), "concerned")

    def test_derive_state_class_article(self):
        m = self.module
        self.assertEqual(m.derive_state_class({"emote_verb": "a"}), "unknown")
        self.assertEqual(m.derive_state_class({"emote_verb": "an"}), "unknown")
        self.assertEqual(m.derive_state_class({"emote_verb": "the"}), "unknown")

    def test_derive_state_class_unmapped_verb(self):
        self.assertEqual(self.module.derive_state_class({"emote_verb": "snorts"}), "unknown")

    def test_derive_state_class_missing_verb(self):
        self.assertIsNone(self.module.derive_state_class({"emote_verb": None}))
        self.assertIsNone(self.module.derive_state_class({}))

    def test_normalize_bubble_carries_emote_verb_and_state_class_slot(self):
        entry = {
            "timestamp": "2026-04-05T00:00:00+00:00",
            "companion": "Glimmer",
            "text": "*drifts closer* Hi.",
            "emote_verb": "drifts",
        }
        bubble = self.module.normalize_bubble(entry, "events")
        self.assertEqual(bubble["emote_verb"], "drifts")
        self.assertIsNone(bubble["state_class"])

    def test_normalize_bubble_emote_verb_none_when_absent(self):
        entry = {
            "timestamp": "2026-04-05T00:00:00+00:00",
            "companion": "Glimmer",
            "text": "Plain bubble.",
        }
        bubble = self.module.normalize_bubble(entry, "events")
        self.assertIsNone(bubble["emote_verb"])
        self.assertIsNone(bubble["state_class"])

    def test_build_index_derives_state_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            sessions_dir = glimmer_dir / "sessions"
            sessions_dir.mkdir(parents=True)
            event = {
                "timestamp": "2026-04-05T10:00:00+00:00",
                "companion": "Glimmer",
                "text": "*drifts closer* Observing.",
                "source": "auto",
                "session_id": "s-1",
                "emote_verb": "drifts",
                "trigger_type": "unknown",
                "trigger_confidence": "none",
            }
            write_jsonl(glimmer_dir / "events.jsonl", [event])
            write_jsonl(glimmer_dir / "log.jsonl", [])
            index = self.module.build_index(glimmer_dir)
            bubble = index["bubbles"][0]
            self.assertEqual(bubble["emote_verb"], "drifts")
            self.assertEqual(bubble["state_class"], "observing")

    def test_backward_compat_no_emote_verb(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            sessions_dir = glimmer_dir / "sessions"
            sessions_dir.mkdir(parents=True)
            old_event = {
                "timestamp": "2026-04-03T10:00:00+00:00",
                "companion": "Glimmer",
                "text": "*drifts closer* Old bubble.",
                "source": "auto",
                "session_id": "sess-old",
                "trigger_type": "unknown",
                "trigger_confidence": "none",
            }
            write_jsonl(glimmer_dir / "events.jsonl", [old_event])
            write_jsonl(glimmer_dir / "log.jsonl", [])
            index = self.module.build_index(glimmer_dir)
            bubble = index["bubbles"][0]
            self.assertIsNone(bubble["emote_verb"])
            self.assertIsNone(bubble["state_class"])

    def test_search_state_classes_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            sessions_dir = glimmer_dir / "sessions"
            sessions_dir.mkdir(parents=True)
            events = [
                {
                    "timestamp": "2026-04-05T10:00:00+00:00",
                    "companion": "Glimmer",
                    "text": "*drifts closer* Observing.",
                    "source": "auto",
                    "session_id": "s-1",
                    "emote_verb": "drifts",
                    "trigger_type": "unknown",
                    "trigger_confidence": "none",
                },
                {
                    "timestamp": "2026-04-05T11:00:00+00:00",
                    "companion": "Glimmer",
                    "text": "*flickers with concern* Uncertain.",
                    "source": "auto",
                    "session_id": "s-1",
                    "emote_verb": "flickers",
                    "trigger_type": "unknown",
                    "trigger_confidence": "none",
                },
            ]
            write_jsonl(glimmer_dir / "events.jsonl", events)
            write_jsonl(glimmer_dir / "log.jsonl", [])
            index = self.module.build_index(glimmer_dir)
            result = self.module.build_search_view(index, "", state_classes=["observing"])
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["bubbles"][0]["state_class"], "observing")
            self.assertEqual(result["filters"]["state_classes"], ["observing"])
            result2 = self.module.build_search_view(index, "", state_classes=["uncertain"])
            self.assertEqual(result2["count"], 1)
            self.assertEqual(result2["bubbles"][0]["state_class"], "uncertain")


class EmoteArcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_build_emote_arc_collapses_consecutive(self):
        bubbles = [
            {"state_class": "observing"},
            {"state_class": "observing"},
            {"state_class": "uncertain"},
            {"state_class": "warm"},
            {"state_class": "warm"},
            {"state_class": "warm"},
        ]
        arc = self.module.build_emote_arc(bubbles)
        self.assertEqual(len(arc), 3)
        self.assertEqual(arc[0], {"state": "observing", "count": 2})
        self.assertEqual(arc[1], {"state": "uncertain", "count": 1})
        self.assertEqual(arc[2], {"state": "warm", "count": 3})

    def test_build_emote_arc_skips_none(self):
        bubbles = [
            {"state_class": "observing"},
            {"state_class": None},
            {"state_class": "calm"},
        ]
        arc = self.module.build_emote_arc(bubbles)
        self.assertEqual(len(arc), 2)
        self.assertEqual(arc[0]["state"], "observing")
        self.assertEqual(arc[1]["state"], "calm")

    def test_build_emote_arc_empty(self):
        self.assertEqual(self.module.build_emote_arc([]), [])

    def test_session_includes_emote_arc(self):
        m = self.module
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            (glimmer_dir / "sessions").mkdir()
            write_jsonl(glimmer_dir / "log.jsonl", [])
            write_jsonl(glimmer_dir / "events.jsonl", [
                {
                    "timestamp": "2026-04-03T10:00:00+00:00",
                    "companion": "Glimmer",
                    "text": "*drifts closer* hello",
                    "emote_verb": "drifts",
                    "source": "auto",
                    "session_id": "s1",
                },
                {
                    "timestamp": "2026-04-03T10:01:00+00:00",
                    "companion": "Glimmer",
                    "text": "*flickers* hmm",
                    "emote_verb": "flickers",
                    "source": "auto",
                    "session_id": "s1",
                },
            ])
            index = m.build_index(glimmer_dir)
            session = index["sessions"][0]
            self.assertIn("emote_arc", session)
            self.assertEqual(len(session["emote_arc"]), 2)
            self.assertEqual(session["emote_arc"][0]["state"], "observing")
            self.assertEqual(session["emote_arc"][1]["state"], "uncertain")

    def test_session_bubbles_have_state_class(self):
        m = self.module
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            (glimmer_dir / "sessions").mkdir()
            write_jsonl(glimmer_dir / "log.jsonl", [])
            write_jsonl(glimmer_dir / "events.jsonl", [
                {
                    "timestamp": "2026-04-03T10:00:00+00:00",
                    "companion": "Glimmer",
                    "text": "*shimmers* nice",
                    "emote_verb": "shimmers",
                    "source": "auto",
                    "session_id": "s1",
                },
            ])
            index = m.build_index(glimmer_dir)
            bubble = index["sessions"][0]["bubbles"][0]
            self.assertIn("state_class", bubble)
            self.assertEqual(bubble["state_class"], "warm")


if __name__ == "__main__":
    unittest.main()
