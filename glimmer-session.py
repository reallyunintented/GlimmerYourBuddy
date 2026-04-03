#!/usr/bin/env python3
"""
Shared session metadata helpers for Glimmer.

Usage:
  glimmer-session.py context <cwd>
  glimmer-session.py manifest <manifest-path> <session-id> <started-at> <companion> <raw-path> <cwd> [claude-args...]
  glimmer-session.py finalize <manifest-path> <session-id> <ended-at>
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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
) -> None:
    manifest = {
        "session_id": session_id,
        "started_at": started_at,
        "ended_at": None,
        "companion": companion,
        "raw_path": raw_path,
        "argv": ["claude", *claude_args],
        **detect_repo_context(cwd),
    }
    path = Path(manifest_path)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def finalize_manifest(manifest_path: str, session_id: str, ended_at: str) -> None:
    path = Path(manifest_path)
    manifest = {}
    if path.exists():
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}

    manifest["session_id"] = manifest.get("session_id", session_id)
    manifest["ended_at"] = ended_at
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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
