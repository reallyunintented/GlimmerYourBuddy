import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "glimmer-context.py"


def load_module():
    loader = SourceFileLoader("glimmer_context", str(MODULE_PATH))
    spec = importlib.util.spec_from_loader("glimmer_context", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def make_empty_archive(tmp):
    glimmer_dir = Path(tmp)
    (glimmer_dir / "sessions").mkdir(exist_ok=True)
    write_jsonl(glimmer_dir / "events.jsonl", [])
    write_jsonl(glimmer_dir / "log.jsonl", [])
    return glimmer_dir


class TestGenerateContext(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_generate_context_returns_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = make_empty_archive(tmp)
            result = self.module.generate_context(glimmer_dir, profile=None, cwd=tmp)
            self.assertIsInstance(result, str)

    def test_generate_context_contains_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = make_empty_archive(tmp)
            result = self.module.generate_context(glimmer_dir, profile=None, cwd=tmp)
            self.assertIn("Glimmer", result)

    def test_generate_context_with_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = make_empty_archive(tmp)
            result = self.module.generate_context(glimmer_dir, profile="pet", cwd=tmp)
            self.assertIn("pet", result)

    def test_cli_writes_file_and_prints_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_empty_archive(tmp)
            env = {**os.environ, "GLIMMER_DATA_DIR": tmp}
            result = subprocess.run(
                ["python3", str(MODULE_PATH), "--cwd", tmp],
                env=env, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            path_out = result.stdout.strip()
            self.assertTrue(Path(path_out).exists(), f"file not found: {path_out}")
            content = Path(path_out).read_text()
            self.assertIsInstance(content, str)
            Path(path_out).unlink()

    def test_cli_profile_from_env_var(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_empty_archive(tmp)
            env = {**os.environ, "GLIMMER_DATA_DIR": tmp, "GLIMMER_SESSION_PROFILE": "pet"}
            result = subprocess.run(
                ["python3", str(MODULE_PATH), "--cwd", tmp],
                env=env, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            path_out = result.stdout.strip()
            content = Path(path_out).read_text()
            self.assertIn("pet", content)
            Path(path_out).unlink()
