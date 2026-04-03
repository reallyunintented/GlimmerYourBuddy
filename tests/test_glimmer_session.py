import importlib.util
import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "glimmer-session.py"


def load_module():
    spec = importlib.util.spec_from_file_location("glimmer_session", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def init_repo(root: Path) -> None:
    run(["git", "init", "-b", "main"], cwd=root)
    run(["git", "config", "user.name", "Glimmer Tests"], cwd=root)
    run(["git", "config", "user.email", "glimmer@example.com"], cwd=root)
    (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    run(["git", "add", "tracked.txt"], cwd=root)
    run(["git", "commit", "-m", "init"], cwd=root)


class DetectRepoContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_detects_repo_root_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_repo(repo)

            context = self.module.detect_repo_context(str(repo))

            self.assertEqual(context["cwd"], str(repo))
            self.assertEqual(context["project_root"], str(repo))
            self.assertEqual(context["project_name"], repo.name)
            self.assertEqual(context["git_branch"], "main")
            self.assertTrue(context["is_repo_root"])

    def test_detects_repo_subdirectory_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_repo(repo)
            nested = repo / "nested" / "deeper"
            nested.mkdir(parents=True)

            context = self.module.detect_repo_context(str(nested))

            self.assertEqual(context["cwd"], str(nested))
            self.assertEqual(context["project_root"], str(repo))
            self.assertEqual(context["project_name"], repo.name)
            self.assertEqual(context["git_branch"], "main")
            self.assertFalse(context["is_repo_root"])

    def test_detects_non_repo_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            context = self.module.detect_repo_context(str(cwd))

            self.assertEqual(context["cwd"], str(cwd))
            self.assertIsNone(context["project_root"])
            self.assertEqual(context["project_name"], cwd.name)
            self.assertIsNone(context["git_branch"])
            self.assertFalse(context["is_repo_root"])

    def test_detached_head_reports_head_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            init_repo(repo)
            head = (
                subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                .stdout.strip()
            )
            run(["git", "checkout", "--detach", head], cwd=repo)

            context = self.module.detect_repo_context(str(repo))

            self.assertEqual(context["project_root"], str(repo))
            self.assertEqual(context["git_branch"], "HEAD")
            self.assertTrue(context["is_repo_root"])

    def test_manifest_writes_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "sessions" / "sess-1.json"

            self.module.write_manifest(
                str(manifest_path),
                "sess-1",
                "2026-04-04T00:00:00+00:00",
                "Glimmer",
                "/tmp/session.raw",
                tmp,
                ["--model", "test"],
            )

            mode = stat.S_IMODE(manifest_path.stat().st_mode)
            self.assertEqual(mode, self.module.PRIVATE_FILE_MODE)

    def test_finalize_preserves_existing_manifest_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "sessions" / "sess-1.json"

            self.module.write_manifest(
                str(manifest_path),
                "sess-1",
                "2026-04-04T00:00:00+00:00",
                "Glimmer",
                "/tmp/session.raw",
                tmp,
                ["--model", "test"],
            )

            self.module.finalize_manifest(
                str(manifest_path),
                "sess-1",
                "2026-04-04T00:10:00+00:00",
            )

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["session_id"], "sess-1")
            self.assertEqual(manifest["ended_at"], "2026-04-04T00:10:00+00:00")
            self.assertEqual(manifest["raw_path"], "/tmp/session.raw")
            mode = stat.S_IMODE(manifest_path.stat().st_mode)
            self.assertEqual(mode, self.module.PRIVATE_FILE_MODE)


if __name__ == "__main__":
    unittest.main()
