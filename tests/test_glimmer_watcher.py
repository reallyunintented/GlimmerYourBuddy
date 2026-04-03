import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "glimmer-watcher.py"


def load_module():
    spec = importlib.util.spec_from_file_location("glimmer_watcher", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WatcherEventShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_load_session_context_copies_exact_manifest_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "session.json"
            manifest = {
                "session_id": "sess-1",
                "started_at": "2026-04-03T10:00:00+00:00",
                "ended_at": None,
                "companion": "Glimmer",
                "raw_path": "/tmp/session.raw",
                "cwd": "/home/notprinted",
                "project_root": None,
                "project_name": "notprinted",
                "git_branch": None,
                "is_repo_root": False,
            }
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            context = self.module.load_session_context(
                "/tmp/session.raw",
                "Glimmer",
                "sess-1",
                str(manifest_path),
            )

            self.assertEqual(context["cwd"], "/home/notprinted")
            self.assertIsNone(context["project_root"])
            self.assertEqual(context["project_name"], "notprinted")
            self.assertIsNone(context["git_branch"])
            self.assertFalse(context["is_repo_root"])

    def test_log_jsonl_stays_plain_and_events_include_session_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            logfile = Path(tmp) / "log.jsonl"
            eventsfile = Path(tmp) / "events.jsonl"
            original_logfile = self.module.LOGFILE
            original_eventsfile = self.module.EVENTSFILE
            self.module.LOGFILE = logfile
            self.module.EVENTSFILE = eventsfile
            try:
                timestamp = "2026-04-03T12:00:00+00:00"
                legacy_entry = self.module.build_legacy_entry(
                    "plain bubble",
                    "Glimmer",
                    timestamp,
                )
                event_entry = self.module.build_entry(
                    "plain bubble",
                    "Glimmer",
                    {
                        "session_id": "sess-1",
                        "raw_path": "/tmp/session.raw",
                        "cwd": "/work/demo/src",
                        "project_root": "/work/demo",
                        "project_name": "demo",
                        "git_branch": "feature/session-context",
                        "is_repo_root": False,
                    },
                    3,
                    {
                        "trigger_type": "post_prompt",
                        "trigger_confidence": "heuristic",
                        "trigger_text": "explain filters",
                    },
                    timestamp,
                )

                self.module.log_legacy_entry(legacy_entry)
                self.module.log_event_entry(event_entry)

                logged_legacy = json.loads(logfile.read_text(encoding="utf-8").strip())
                logged_event = json.loads(eventsfile.read_text(encoding="utf-8").strip())

                self.assertEqual(
                    set(logged_legacy),
                    {"timestamp", "companion", "text"},
                )
                self.assertEqual(logged_event["session_id"], "sess-1")
                self.assertEqual(logged_event["cwd"], "/work/demo/src")
                self.assertEqual(logged_event["project_root"], "/work/demo")
                self.assertEqual(logged_event["project_name"], "demo")
                self.assertEqual(
                    logged_event["git_branch"],
                    "feature/session-context",
                )
                self.assertFalse(logged_event["is_repo_root"])
                self.assertEqual(logged_event["trigger_type"], "post_prompt")
                self.assertEqual(logged_event["trigger_confidence"], "heuristic")
                self.assertEqual(logged_event["trigger_text"], "explain filters")
            finally:
                self.module.LOGFILE = original_logfile
                self.module.EVENTSFILE = original_eventsfile

    def test_scan_buffer_prefers_fuller_text_when_bubble_grows(self):
        with tempfile.TemporaryDirectory() as tmp:
            logfile = Path(tmp) / "log.jsonl"
            eventsfile = Path(tmp) / "events.jsonl"
            watcherlog = Path(tmp) / "watcher.log"
            original_logfile = self.module.LOGFILE
            original_eventsfile = self.module.EVENTSFILE
            original_watcherlog = self.module.WATCHERLOG
            self.module.LOGFILE = logfile
            self.module.EVENTSFILE = eventsfile
            self.module.WATCHERLOG = watcherlog
            try:
                short_buf = (
                    "╭────────────────────────────────────────╮\n"
                    "│ Ah, the README's selling the dream.   │\n"
                    "╰────────────────────────────────────────╯\n"
                )
                long_buf = (
                    "╭──────────────────────────────────────────────╮\n"
                    "│ Ah, the README's selling the dream.         │\n"
                    "│ But the code is still asking for patterns.  │\n"
                    "╰──────────────────────────────────────────────╯\n"
                )

                session_seen = set()
                pending_bubbles = {}
                session_ctx = {}
                bubble_seq = 0

                bubble_seq = self.module.scan_buffer(
                    short_buf,
                    session_seen,
                    pending_bubbles,
                    "Glimmer",
                    session_ctx,
                    bubble_seq,
                )
                self.assertEqual(bubble_seq, 0)
                self.assertIn(
                    "Ah, the README's selling the dream.",
                    pending_bubbles,
                )

                bubble_seq = self.module.scan_buffer(
                    long_buf,
                    session_seen,
                    pending_bubbles,
                    "Glimmer",
                    session_ctx,
                    bubble_seq,
                )
                self.assertEqual(bubble_seq, 0)
                self.assertNotIn(
                    "Ah, the README's selling the dream.",
                    pending_bubbles,
                )
                self.assertIn(
                    "Ah, the README's selling the dream. But the code is still asking for patterns.",
                    pending_bubbles,
                )

                bubble_seq = self.module.scan_buffer(
                    long_buf,
                    session_seen,
                    pending_bubbles,
                    "Glimmer",
                    session_ctx,
                    bubble_seq,
                )
                self.assertEqual(bubble_seq, 1)

                logged_legacy = json.loads(logfile.read_text(encoding="utf-8").strip())
                logged_event = json.loads(eventsfile.read_text(encoding="utf-8").strip())
                expected_text = (
                    "Ah, the README's selling the dream. "
                    "But the code is still asking for patterns."
                )
                self.assertEqual(logged_legacy["text"], expected_text)
                self.assertEqual(logged_event["text"], expected_text)
            finally:
                self.module.LOGFILE = original_logfile
                self.module.EVENTSFILE = original_eventsfile
                self.module.WATCHERLOG = original_watcherlog


if __name__ == "__main__":
    unittest.main()
