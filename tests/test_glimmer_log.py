import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GLIMMER_LOG = REPO_ROOT / "glimmer-log"


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


if __name__ == "__main__":
    unittest.main()
