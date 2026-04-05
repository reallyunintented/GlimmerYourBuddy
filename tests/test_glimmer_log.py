import json
import os
import stat
import subprocess
import tempfile
import time
import unittest
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GLIMMER_LOG = REPO_ROOT / "glimmer-log"
GLIMMER_UI = REPO_ROOT / "glimmer-ui"


def load_glimmer_ui_module():
    loader = SourceFileLoader("glimmer_ui_for_log_tests", str(GLIMMER_UI))
    spec = importlib.util.spec_from_loader("glimmer_ui_for_log_tests", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class GlimmerLogSessionFilterTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        home = Path(self.tempdir.name)
        self.home = home
        self.glimmer_dir = home / ".claude" / "glimmer"
        self.sessions_dir = self.glimmer_dir / "sessions"
        self.sessions_dir.mkdir(parents=True)
        self.eventsfile = self.glimmer_dir / "events.jsonl"
        self._write_fixtures()

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_fixtures(self):
        manifests = [
            {
                "session_id": "sess-root",
                "started_at": "2026-04-03T10:00:00+00:00",
                "ended_at": "2026-04-03T10:30:00+00:00",
                "companion": "Glimmer",
                "raw_path": "/tmp/sess-root.raw",
                "cwd": "/work/alpha",
                "project_root": "/work/alpha",
                "project_name": "alpha",
                "git_branch": "main",
                "is_repo_root": True,
            },
            {
                "session_id": "sess-subdir",
                "started_at": "2026-04-03T11:00:00+00:00",
                "ended_at": None,
                "companion": "Glimmer",
                "raw_path": "/tmp/sess-subdir.raw",
                "cwd": "/work/alpha/src/tools",
                "project_root": "/work/alpha",
                "project_name": "alpha",
                "git_branch": "feature/session-context",
                "is_repo_root": False,
            },
            {
                "session_id": "sess-home",
                "started_at": "2026-04-03T12:00:00+00:00",
                "ended_at": "2026-04-03T12:05:00+00:00",
                "companion": "Glimmer",
                "raw_path": "/tmp/sess-home.raw",
                "cwd": "/home/notprinted",
                "project_root": None,
                "project_name": "notprinted",
                "git_branch": None,
                "is_repo_root": False,
            },
        ]
        for manifest in manifests:
            (self.sessions_dir / f'{manifest["session_id"]}.json').write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        write_jsonl(
            self.eventsfile,
            [
                {
                    "timestamp": "2026-04-03T10:01:00+00:00",
                    "companion": "Glimmer",
                    "text": "repo root bubble",
                    "source": "auto",
                    "bubble_seq": 1,
                    "session_id": "sess-root",
                    "cwd": "/work/alpha",
                    "project_root": "/work/alpha",
                    "project_name": "alpha",
                    "git_branch": "main",
                    "is_repo_root": True,
                    "trigger_type": "unknown",
                    "trigger_confidence": "none",
                },
                {
                    "timestamp": "2026-04-03T11:02:00+00:00",
                    "companion": "Glimmer",
                    "text": "nested bubble",
                    "source": "auto",
                    "bubble_seq": 1,
                    "session_id": "sess-subdir",
                    "cwd": "/work/alpha/src/tools",
                    "project_root": "/work/alpha",
                    "project_name": "alpha",
                    "git_branch": "feature/session-context",
                    "is_repo_root": False,
                    "trigger_type": "post_prompt",
                    "trigger_confidence": "heuristic",
                },
                {
                    "timestamp": "2026-04-03T12:01:00+00:00",
                    "companion": "Glimmer",
                    "text": "home bubble",
                    "source": "auto",
                    "bubble_seq": 1,
                    "session_id": "sess-home",
                    "cwd": "/home/notprinted",
                    "project_root": None,
                    "project_name": "notprinted",
                    "git_branch": None,
                    "is_repo_root": False,
                    "trigger_type": "buddy_pet",
                    "trigger_confidence": "exact",
                    "trigger_text": "/buddy pet",
                },
            ],
        )

    def run_glimmer_log(self, *args: str) -> str:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        completed = subprocess.run(
            ["bash", str(GLIMMER_LOG), *args],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout

    def test_sessions_list_shows_project_branch_and_cwd_summary(self):
        output = self.run_glimmer_log("--sessions")

        self.assertIn("sess-home  latest", output)
        self.assertIn("project=alpha  branch=main  cwd=.", output)
        self.assertIn(
            "project=alpha  branch=feature/session-context  cwd=src/tools",
            output,
        )
        self.assertIn("project=notprinted  branch=-  cwd=/home/notprinted", output)

    def test_session_latest_header_includes_project_context(self):
        output = self.run_glimmer_log("--session", "latest", "--project", "alpha")

        self.assertIn("Session: sess-subdir", output)
        self.assertIn("Project: alpha", output)
        self.assertIn("Branch: feature/session-context", output)
        self.assertIn("CWD: /work/alpha/src/tools", output)
        self.assertIn("Repo root: /work/alpha", output)
        self.assertIn("At repo root: no", output)

    def test_project_filter_lists_only_matching_sessions(self):
        output = self.run_glimmer_log("--project", "alpha")

        self.assertIn("sess-root", output)
        self.assertIn("sess-subdir", output)
        self.assertNotIn("sess-home", output)

    def test_branch_filter_lists_only_matching_sessions(self):
        output = self.run_glimmer_log("--branch", "main")

        self.assertIn("sess-root", output)
        self.assertNotIn("sess-subdir", output)
        self.assertNotIn("sess-home", output)

    def test_cwd_filter_lists_only_exact_match(self):
        output = self.run_glimmer_log("--cwd", "/work/alpha/src/tools")

        self.assertIn("sess-subdir", output)
        self.assertNotIn("sess-root", output)
        self.assertNotIn("sess-home", output)

    def test_repo_root_only_filters_out_nested_and_non_repo_sessions(self):
        output = self.run_glimmer_log("--sessions", "--repo-root-only")

        self.assertIn("sess-root", output)
        self.assertNotIn("sess-subdir", output)
        self.assertNotIn("sess-home", output)


class GlimmerLogLegacyCommandTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.home = Path(self.tempdir.name)
        self.glimmer_dir = self.home / ".claude" / "glimmer"
        self.glimmer_dir.mkdir(parents=True)
        self.logfile = self.glimmer_dir / "log.jsonl"
        self.raw_dir = self.glimmer_dir / "raw"
        self.raw_dir.mkdir()
        self.claude_config = self.home / ".claude.json"
        self._write_log_fixture()

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_log_fixture(self):
        write_jsonl(
            self.logfile,
            [
                {
                    "timestamp": "2026-04-03T10:01:00+00:00",
                    "companion": "Glimmer",
                    "text": "First debugging whisper",
                },
                {
                    "timestamp": "2026-04-03T10:02:00+00:00",
                    "companion": "Glimmer",
                    "text": "Second patient bubble",
                },
            ],
        )

    def run_glimmer_log(self, *args: str) -> str:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        completed = subprocess.run(
            ["bash", str(GLIMMER_LOG), *args],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout

    def test_add_uses_configured_companion_name(self):
        self.claude_config.write_text(
            json.dumps({"companion": {"name": "Vy"}}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        self.run_glimmer_log("--add", "Manual note")

        entries = [
            json.loads(line)
            for line in self.logfile.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(entries[-1]["companion"], "Vy")
        self.assertEqual(entries[-1]["text"], "Manual note")

    def test_add_keeps_log_private(self):
        self.run_glimmer_log("--add", "Manual note")

        logfile_mode = stat.S_IMODE(self.logfile.stat().st_mode)
        glimmer_dir_mode = stat.S_IMODE(self.glimmer_dir.stat().st_mode)

        self.assertEqual(logfile_mode, 0o600)
        self.assertEqual(glimmer_dir_mode, 0o700)

    def test_grep_filters_legacy_output_case_insensitively(self):
        output = self.run_glimmer_log("--grep", "patient")

        self.assertIn("Second patient bubble", output)
        self.assertNotIn("First debugging whisper", output)

    def test_cleanup_raw_removes_only_old_files(self):
        old_raw = self.raw_dir / "session-old.raw"
        fresh_raw = self.raw_dir / "session-fresh.raw"
        old_raw.write_text("old\n", encoding="utf-8")
        fresh_raw.write_text("fresh\n", encoding="utf-8")
        now = time.time()
        os.utime(old_raw, (now - 20 * 86400, now - 20 * 86400))
        os.utime(fresh_raw, (now, now))

        output = self.run_glimmer_log("--cleanup-raw", "14")

        self.assertIn("Removed 1 raw capture file(s) older than 14 days.", output)
        self.assertFalse(old_raw.exists())
        self.assertTrue(fresh_raw.exists())


class GlimmerLogMatterCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glimmer_ui = load_glimmer_ui_module()

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.home = Path(self.tempdir.name)
        self.glimmer_dir = self.home / ".claude" / "glimmer"
        self.sessions_dir = self.glimmer_dir / "sessions"
        self.sessions_dir.mkdir(parents=True)
        self.eventsfile = self.glimmer_dir / "events.jsonl"
        self.logfile = self.glimmer_dir / "log.jsonl"
        self._write_fixtures()

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_fixtures(self):
        events = [
            {
                "timestamp": "2026-04-03T10:01:00+00:00",
                "companion": "Glimmer",
                "text": "Older bubble",
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
                "text": "Latest mattered candidate",
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
        ]
        write_jsonl(self.eventsfile, events)
        write_jsonl(self.logfile, [])
        (self.sessions_dir / "sess-1.json").write_text(
            json.dumps(
                {
                    "session_id": "sess-1",
                    "started_at": "2026-04-03T10:00:00+00:00",
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
        self.latest_bubble_id = self.glimmer_ui.bubble_id(events[-1])

    def run_glimmer_log(self, *args: str) -> str:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        completed = subprocess.run(
            ["bash", str(GLIMMER_LOG), *args],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout

    def load_usage(self) -> dict:
        usage_path = self.glimmer_dir / "usage.json"
        if not usage_path.exists():
            return {}
        return json.loads(usage_path.read_text(encoding="utf-8"))

    def test_mark_latest_creates_mattered_entry(self):
        self.run_glimmer_log("--mark", "latest", "--note", "Keep this one.")

        matters = json.loads(
            (self.glimmer_dir / "mattered.json").read_text(encoding="utf-8")
        )
        self.assertIn(self.latest_bubble_id, matters)
        self.assertEqual(matters[self.latest_bubble_id]["note"], "Keep this one.")
        self.assertEqual(matters[self.latest_bubble_id]["review_state"], "unreviewed")

    def test_mattered_json_lists_marked_bubbles(self):
        self.run_glimmer_log("--mark", "latest", "--note", "Keep this one.")

        output = self.run_glimmer_log("--mattered", "--json")
        payload = json.loads(output)

        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["bubbles"][0]["id"], self.latest_bubble_id)
        self.assertEqual(payload["bubbles"][0]["matter_note"], "Keep this one.")

    def test_review_state_updates_and_review_filter_outputs_group(self):
        self.run_glimmer_log("--mark", "latest", "--note", "Keep this one.")
        self.run_glimmer_log("--review-state", "latest", "used")

        matters = json.loads(
            (self.glimmer_dir / "mattered.json").read_text(encoding="utf-8")
        )
        self.assertEqual(matters[self.latest_bubble_id]["review_state"], "resolved")
        self.assertIsNotNone(matters[self.latest_bubble_id]["reviewed_at"])

        output = self.run_glimmer_log("--review", "used", "--json")
        payload = json.loads(output)
        self.assertEqual(len(payload["groups"]["resolved"]), 1)
        self.assertEqual(payload["groups"]["resolved"][0]["id"], self.latest_bubble_id)

    def test_mark_and_review_state_record_usage(self):
        self.run_glimmer_log("--mark", "latest", "--note", "Keep this one.")

        usage = self.load_usage()
        self.assertEqual(usage[self.latest_bubble_id]["use_count"], 1)
        self.assertEqual(
            usage[self.latest_bubble_id]["use_sources"],
            ["cli.matter_toggle"],
        )

        self.run_glimmer_log("--review-state", "latest", "used")

        usage = self.load_usage()
        self.assertEqual(usage[self.latest_bubble_id]["use_count"], 2)
        self.assertEqual(
            usage[self.latest_bubble_id]["use_sources"],
            ["cli.matter_toggle", "cli.review_state"],
        )

    def test_mattered_and_review_views_record_usage(self):
        self.run_glimmer_log("--mark", "latest", "--note", "Keep this one.")
        self.run_glimmer_log("--mattered", "--json")
        self.run_glimmer_log("--review", "unreviewed", "--json")

        usage = self.load_usage()
        self.assertEqual(usage[self.latest_bubble_id]["use_count"], 3)
        self.assertEqual(
            usage[self.latest_bubble_id]["use_sources"],
            ["cli.matter_toggle", "cli.mattered", "cli.review"],
        )


class GlimmerLogBriefCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glimmer_ui = load_glimmer_ui_module()

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.home = Path(self.tempdir.name)
        self.glimmer_dir = self.home / ".claude" / "glimmer"
        self.sessions_dir = self.glimmer_dir / "sessions"
        self.sessions_dir.mkdir(parents=True)
        self.eventsfile = self.glimmer_dir / "events.jsonl"
        self.logfile = self.glimmer_dir / "log.jsonl"
        self._write_fixtures()

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_fixtures(self):
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
        write_jsonl(self.eventsfile, events)
        write_jsonl(self.logfile, [])

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
            (self.sessions_dir / f'{manifest["session_id"]}.json').write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        self.ids = {
            "focus": self.glimmer_ui.bubble_id(events[1]),
            "after": self.glimmer_ui.bubble_id(events[2]),
            "beta": self.glimmer_ui.bubble_id(events[3]),
        }
        (self.glimmer_dir / "mattered.json").write_text(
            json.dumps(
                {
                    self.ids["focus"]: {
                        "note": "Need review on direction signal",
                        "marked_at": "2026-04-03T10:06:00+00:00",
                        "updated_at": "2026-04-03T10:06:00+00:00",
                        "review_state": "unreviewed",
                        "reviewed_at": None,
                    },
                    self.ids["after"]: {
                        "note": "Direction signal remains open in alpha",
                        "marked_at": "2026-04-03T10:07:00+00:00",
                        "updated_at": "2026-04-03T10:08:00+00:00",
                        "review_state": "open",
                        "reviewed_at": "2026-04-03T10:08:00+00:00",
                    },
                    self.ids["beta"]: {
                        "note": "Direction signal recurring concern in beta",
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

    def run_glimmer_log(self, *args: str) -> str:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        completed = subprocess.run(
            ["bash", str(GLIMMER_LOG), *args],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout

    def load_usage(self) -> dict:
        usage_path = self.glimmer_dir / "usage.json"
        if not usage_path.exists():
            return {}
        return json.loads(usage_path.read_text(encoding="utf-8"))

    def test_brief_json_returns_project_summary(self):
        output = self.run_glimmer_log("--brief", "--project", "alpha", "--json")
        payload = json.loads(output)

        self.assertEqual(payload["scope"]["project_key"], "alpha")
        self.assertEqual(payload["summary"]["mattered_count"], 2)
        self.assertEqual(payload["summary"]["active_count"], 1)
        self.assertEqual(payload["top_mattered"][0]["id"], self.ids["after"])
        self.assertEqual(payload["recurring_signals"][0]["bubble"]["id"], self.ids["after"])

    def test_brief_markdown_formats_for_agent_handoff(self):
        output = self.run_glimmer_log("--brief", "--project", "alpha", "--markdown")

        self.assertIn("# Glimmer Brief: alpha", output)
        self.assertIn("## Top Mattered", output)
        self.assertIn(self.ids["after"], output)

    def test_brief_can_infer_project_from_cwd_argument(self):
        output = self.run_glimmer_log("--brief", "--cwd", "/work/alpha/src")

        self.assertIn("Brief: alpha", output)
        self.assertIn("Active items", output)

    def test_brief_records_usage_once_per_returned_bubble(self):
        self.run_glimmer_log("--brief", "--project", "alpha", "--json")

        usage = self.load_usage()
        self.assertEqual(usage[self.ids["focus"]]["use_count"], 1)
        self.assertEqual(usage[self.ids["focus"]]["use_sources"], ["cli.brief"])
        self.assertEqual(usage[self.ids["after"]]["use_count"], 1)
        self.assertEqual(usage[self.ids["after"]]["use_sources"], ["cli.brief"])
        self.assertNotIn(self.ids["beta"], usage)


if __name__ == "__main__":
    unittest.main()
