#!/usr/bin/env python3
"""glimmer-context — write a profile-aware project brief to a temp file.

Usage:
    python3 glimmer-context.py [--cwd DIR] [--profile NAME]

Reads GLIMMER_DATA_DIR (default ~/.claude/glimmer).
Reads GLIMMER_SESSION_PROFILE if --profile not given.

Exits 0 and prints the temp file path on stdout.
Exits 1 on error (writes reason to stderr).
The caller is responsible for deleting the temp file.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _load_glimmer_ui():
    script_path = Path(__file__).resolve()
    candidates = [
        script_path.parent / "glimmer-ui",
        Path.home() / ".local" / "bin" / "glimmer-ui",
    ]
    for candidate in candidates:
        if candidate.exists():
            loader = SourceFileLoader("glimmer_ui", str(candidate))
            spec = importlib.util.spec_from_loader("glimmer_ui", loader)
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)
            return module
    raise FileNotFoundError(f"glimmer-ui not found; searched: {candidates}")


_ui = _load_glimmer_ui()

DEFAULT_GLIMMER_DIR = Path(
    os.environ.get("GLIMMER_DATA_DIR", Path.home() / ".claude" / "glimmer")
)


def _render_brief(brief: dict, *, profile: str | None) -> str:
    lines = []
    scope = brief.get("scope") or {}
    project_label = scope.get("project_label") or scope.get("project_key") or "this project"
    profile_tag = f" [{profile} profile]" if profile else ""
    lines.append(f"# Glimmer context brief — {project_label}{profile_tag}")
    lines.append("")

    summary = brief.get("summary") or {}
    mattered_count = summary.get("mattered_count", 0)
    if mattered_count:
        lines.append(f"{mattered_count} mattered bubble(s) in archive.")
        lines.append("")

    for section_key, label in [
        ("top_mattered", "Top signals"),
        ("open_items", "Open items"),
        ("resurface_now", "Worth revisiting"),
        ("recurring_signals", "Recurring themes"),
    ]:
        items = brief.get(section_key) or []
        if not items:
            continue
        lines.append(f"## {label}")
        for item in items:
            bubble = item.get("bubble") if "bubble" in item else item
            text = (bubble.get("text") or "").strip()
            if not text:
                continue
            preview = text[:200] + ("..." if len(text) > 200 else "")
            lines.append(f"- {preview}")
        lines.append("")

    return "\n".join(lines)


def generate_context(
    glimmer_dir: Path,
    *,
    profile: str | None,
    cwd: str | None,
) -> str:
    index = _ui.build_index(glimmer_dir)
    brief = _ui.build_brief_view(index, cwd=cwd, profile=profile)
    return _render_brief(brief, profile=profile)


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--profile", default=None)
    args = parser.parse_args(argv)

    cwd = args.cwd or os.getcwd()
    profile = args.profile or os.environ.get("GLIMMER_SESSION_PROFILE", "") or None
    if profile:
        profile = profile.strip().lower() or None

    try:
        index = _ui.build_index(DEFAULT_GLIMMER_DIR)
        brief = _ui.build_brief_view(index, cwd=cwd, profile=profile)
        content = _render_brief(brief, profile=profile)
    except Exception as exc:
        print(f"glimmer-context: {exc}", file=sys.stderr)
        return 1

    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        prefix="glimmer-context-",
        delete=False,
        encoding="utf-8",
    )
    try:
        tmp.write(content)
        tmp.flush()
        tmp.close()
        os.chmod(tmp.name, 0o600)
    except Exception as exc:
        os.unlink(tmp.name)
        print(f"glimmer-context: {exc}", file=sys.stderr)
        return 1

    # Record usage (best-effort — don't fail the whole thing if this errors)
    try:
        ids = _ui.brief_bubble_ids(brief)
        _ui.record_usage_for_index(DEFAULT_GLIMMER_DIR, index, ids, "auto.session_start")
    except Exception:
        pass

    print(tmp.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
