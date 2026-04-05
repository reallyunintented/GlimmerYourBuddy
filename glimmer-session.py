#!/usr/bin/env python3
"""
Shared session metadata helpers for Glimmer.

Usage:
  glimmer-session.py context <cwd>
  glimmer-session.py manifest <manifest-path> <session-id> <started-at> <companion> <raw-path> <cwd> [claude-args...]
  glimmer-session.py finalize <manifest-path> <session-id> <ended-at>
"""

from __future__ import annotations

from contextlib import contextmanager
import errno
try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


def _set_permissions(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except (FileNotFoundError, PermissionError):
        pass


def _ensure_private_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _set_permissions(path.parent, PRIVATE_DIR_MODE)


def _lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


@contextmanager
def _advisory_lock(path: Path):
    _ensure_private_parent(path)
    with open(path, "a+", encoding="utf-8") as handle:
        _set_permissions(path, PRIVATE_FILE_MODE)
        if fcntl is not None:
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                    break
                except OSError as exc:  # pragma: no cover - signal interruption
                    if exc.errno == errno.EINTR:
                        continue
                    raise
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic_write_text(path: Path, content: str) -> None:
    _ensure_private_parent(path)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _set_permissions(tmp_path, PRIVATE_FILE_MODE)
        os.replace(tmp_path, path)
        _set_permissions(path, PRIVATE_FILE_MODE)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _write_private_json(path: Path, payload: dict) -> None:
    with _advisory_lock(_lock_path(path)):
        _atomic_write_text(
            path,
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        )


def _load_private_json_unlocked(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _mutate_private_json(path: Path, callback):
    with _advisory_lock(_lock_path(path)):
        payload = _load_private_json_unlocked(path)
        result = callback(payload)
        _atomic_write_text(
            path,
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        )
        return result


def _run_git(cwd: str, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    value = completed.stdout.strip()
    return value or None


def detect_repo_context(cwd: str) -> dict:
    project_root = _run_git(cwd, "rev-parse", "--show-toplevel")
    project_name = Path(project_root).name if project_root else Path(cwd).name
    git_branch = None
    if project_root:
        git_branch = _run_git(cwd, "rev-parse", "--abbrev-ref", "HEAD")

    return {
        "cwd": cwd,
        "project_root": project_root,
        "project_name": project_name,
        "git_branch": git_branch,
        "is_repo_root": bool(project_root and cwd == project_root),
    }


def write_manifest(
    manifest_path: str,
    session_id: str,
    started_at: str,
    companion: str,
    raw_path: str,
    cwd: str,
    claude_args: list[str],
    *,
    session_profile: str | None = None,
) -> None:
    _profile = (session_profile or "").strip().lower() or None
    manifest = {
        "session_id": session_id,
        "started_at": started_at,
        "ended_at": None,
        "companion": companion,
        "raw_path": raw_path,
        "argv": ["claude", *claude_args],
        "session_profile": _profile,
        **detect_repo_context(cwd),
    }
    _write_private_json(Path(manifest_path), manifest)


def finalize_manifest(manifest_path: str, session_id: str, ended_at: str) -> None:
    path = Path(manifest_path)
    def apply_finalize(manifest: dict) -> None:
        manifest["session_id"] = manifest.get("session_id", session_id)
        manifest["ended_at"] = ended_at

    _mutate_private_json(path, apply_finalize)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__.strip(), file=sys.stderr)
        return 1

    command = sys.argv[1]
    if command == "context":
        if len(sys.argv) != 3:
            print("Usage: glimmer-session.py context <cwd>", file=sys.stderr)
            return 1
        print(json.dumps(detect_repo_context(sys.argv[2]), ensure_ascii=False))
        return 0

    if command == "manifest":
        if len(sys.argv) < 8:
            print(
                "Usage: glimmer-session.py manifest <manifest-path> <session-id> <started-at> <companion> <raw-path> <cwd> [claude-args...]",
                file=sys.stderr,
            )
            return 1
        write_manifest(
            manifest_path=sys.argv[2],
            session_id=sys.argv[3],
            started_at=sys.argv[4],
            companion=sys.argv[5],
            raw_path=sys.argv[6],
            cwd=sys.argv[7],
            claude_args=sys.argv[8:],
            session_profile=os.environ.get("GLIMMER_SESSION_PROFILE", "") or None,
        )
        return 0

    if command == "finalize":
        if len(sys.argv) != 5:
            print(
                "Usage: glimmer-session.py finalize <manifest-path> <session-id> <ended-at>",
                file=sys.stderr,
            )
            return 1
        finalize_manifest(sys.argv[2], sys.argv[3], sys.argv[4])
        return 0

    print(f"Unknown command: {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
