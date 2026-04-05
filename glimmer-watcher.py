#!/usr/bin/env python3
"""
Glimmer speech bubble watcher.

Tails a `script` typescript file, strips ANSI escape sequences,
detects rounded-box speech bubbles, and logs unique ones to JSONL.

Usage: glimmer-watcher.py <typescript-file> [companion-name] [session-id] [manifest-path]
"""

import json
import os
import re
import signal
import sys
import time
from contextlib import contextmanager
import errno
try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_GLIMMER_DIR = Path(
    os.environ.get("GLIMMER_DATA_DIR", Path.home() / ".claude" / "glimmer")
)
LOGFILE = DEFAULT_GLIMMER_DIR / "log.jsonl"
EVENTSFILE = DEFAULT_GLIMMER_DIR / "events.jsonl"
WATCHERLOG = DEFAULT_GLIMMER_DIR / "watcher.log"
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
# How often to scan the buffer (seconds)
SCAN_INTERVAL = 1.5
# Require the same bubble text to appear in two scans before logging it.
STABLE_SCAN_COUNT = 2
# Minimum box width to consider (Glimmer's box is 34 chars)
MIN_BOX_WIDTH = 20
MAX_BOX_WIDTH = 50
VERBOSE_STDOUT = os.environ.get("GLIMMER_WATCHER_STDOUT") == "1"

# ANSI escape sequence pattern — covers CSI, OSC, and simple escapes
ANSI_RE = re.compile(
    r"""
    \x1b       # ESC
    (?:
        \[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]  # CSI sequences
      | \].*?(?:\x07|\x1b\\)                     # OSC sequences
      | [\x20-\x2f]*[\x30-\x7e]                  # 2-char sequences
    )
    | [\x00-\x08\x0e-\x1f]  # other control chars (except \t \n \r)
    """,
    re.VERBOSE,
)
CURSOR_RIGHT_RE = re.compile(r"\x1b\[(\d*)C")
PROMPT_LINE_RE = re.compile(r"^\s*❯\s*(.*?)\s*$")
PROMPT_MARKER_RE = re.compile(r"^\s*❯(?:\s.*)?$")

# Rounded box characters
TOP_RE = re.compile(r"╭(─+)╮")
BOT_RE = re.compile(r"╰(─+)╯")
MID_RE = re.compile(r"│(.+?)│")
STOP_REQUESTED = False
BUBBLE_CONTEXT_BEFORE = 4000
BUBBLE_CONTEXT_AFTER = 1500
SESSION_CONTEXT_KEYS = (
    "session_id",
    "raw_path",
    "companion",
    "started_at",
    "ended_at",
    "cwd",
    "project_root",
    "project_name",
    "git_branch",
    "is_repo_root",
    "session_profile",
)


def set_permissions(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except (FileNotFoundError, PermissionError):
        pass


def ensure_private_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    set_permissions(path.parent, PRIVATE_DIR_MODE)


def lock_path_for(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


@contextmanager
def advisory_lock(path: Path):
    ensure_private_parent(path)
    with open(path, "a+", encoding="utf-8") as handle:
        set_permissions(path, PRIVATE_FILE_MODE)
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


def debug(message: str) -> None:
    ensure_private_parent(WATCHERLOG)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with advisory_lock(lock_path_for(WATCHERLOG)):
        with open(WATCHERLOG, "a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}\n")
    set_permissions(WATCHERLOG, PRIVATE_FILE_MODE)
    if VERBOSE_STDOUT:
        print(message, flush=True)


def strip_ansi(text: str) -> str:
    def preserve_cursor_spacing(match: re.Match[str]) -> str:
        width = int(match.group(1) or "1")
        return " " * width

    # Claude's full-screen UI sometimes encodes visible word spacing as
    # horizontal cursor movement. Preserve that before dropping ANSI codes.
    text = CURSOR_RIGHT_RE.sub(preserve_cursor_spacing, text)
    return ANSI_RE.sub("", text)


def normalize_lines(text: str) -> list[str]:
    """Split on both \\n and \\r — Ink's full-screen renderer uses \\r for
    cursor positioning, so box parts end up on a single \\n-line separated
    by \\r characters."""
    return re.split(r"[\r\n]+", text)


# UI boxes to ignore (Claude Code welcome screen, etc.)
IGNORE_PREFIXES = (
    "ClaudeCode",
    "Recent",
    "Welcome",
    "What's",
    "/resume",
    "/release",
)


def line_spans(text: str) -> list[dict]:
    """Return non-empty terminal lines with source offsets."""
    spans = []
    for match in re.finditer(r"[^\r\n]+", text):
        spans.append(
            {
                "text": match.group(0),
                "start": match.start(),
                "end": match.end(),
            }
        )
    return spans


def find_related_pending_text(
    pending_bubbles: dict[str, dict],
    bubble_text: str,
) -> str | None:
    """Find a pending bubble that looks like an earlier/later version of the
    same text.

    Claude often paints bubble text incrementally. If a later scan produces a
    longer version with the earlier text as a prefix, treat it as the same
    bubble and prefer the longer variant.
    """
    related = [
        pending_text
        for pending_text in pending_bubbles
        if bubble_text.startswith(pending_text) or pending_text.startswith(bubble_text)
    ]
    if not related:
        return None
    return max(related, key=len)


def extract_bubble_candidates(text: str) -> list[dict]:
    """Find speech bubbles and keep source offsets for trigger attribution."""
    lines = line_spans(text)
    bubbles = []
    i = 0
    while i < len(lines):
        top = TOP_RE.search(lines[i]["text"])
        if top:
            width = len(top.group(1)) + 2  # +2 for corners
            if MIN_BOX_WIDTH <= width <= MAX_BOX_WIDTH:
                content_lines = []
                bubble_start = lines[i]["start"]
                bubble_end = lines[i]["end"]
                j = i + 1
                while j < len(lines):
                    current_line = lines[j]["text"]
                    bubble_end = lines[j]["end"]
                    if BOT_RE.search(current_line):
                        break
                    mid = MID_RE.search(current_line)
                    if mid:
                        content_lines.append(mid.group(1).strip())
                    j += 1
                    if j - i > 15:  # sanity: don't scan forever
                        break
                if content_lines:
                    bubble_text = " ".join(
                        l for l in content_lines if l
                    )
                    # Filter: must have real text, skip UI chrome
                    if (
                        len(bubble_text) > 5
                        and not any(
                            bubble_text.startswith(p) for p in IGNORE_PREFIXES
                        )
                    ):
                        bubbles.append(
                            {
                                "text": bubble_text,
                                "start": bubble_start,
                                "end": bubble_end,
                            }
                        )
                i = j + 1
                continue
        i += 1
    return bubbles


def find_last_prompt_line(text: str) -> str | None:
    """Return the most recent visible prompt line in the given text window."""
    last_prompt = None
    for line in normalize_lines(text):
        match = PROMPT_LINE_RE.match(line)
        if match:
            prompt_text = match.group(1).strip()
            if prompt_text:
                last_prompt = prompt_text
    return last_prompt


def has_prompt_marker(text: str) -> bool:
    """Whether the visible terminal content contains a ready prompt marker."""
    return any(PROMPT_MARKER_RE.match(line) for line in normalize_lines(text))


def classify_trigger(cleaned_text: str, bubble: dict) -> dict:
    """Best-effort trigger attribution for a newly seen bubble."""
    start = bubble["start"]
    end = bubble["end"]
    before = cleaned_text[max(0, start - BUBBLE_CONTEXT_BEFORE):start]
    after = cleaned_text[end:min(len(cleaned_text), end + BUBBLE_CONTEXT_AFTER)]
    prompt_text = find_last_prompt_line(before)

    if prompt_text == "/buddy pet":
        return {
            "trigger_type": "buddy_pet",
            "trigger_confidence": "exact",
            "trigger_text": "/buddy pet",
        }

    if has_prompt_marker(after):
        trigger = {
            "trigger_type": "post_prompt",
            "trigger_confidence": "heuristic",
        }
        if prompt_text and not prompt_text.startswith("/"):
            trigger["trigger_text"] = prompt_text
        return trigger

    return {
        "trigger_type": "unknown",
        "trigger_confidence": "none",
    }


EMOTE_VERB_RE = re.compile(r"^\*(\w+)")


def extract_emote_verb(text: str) -> str | None:
    """Return the first word of an italicised emote action, or None."""
    match = EMOTE_VERB_RE.match(text)
    return match.group(1).lower() if match else None


def load_session_state(session_id: str | None) -> tuple[set[str], int]:
    """Load bubbles already logged for this session."""
    seen = set()
    bubble_seq = 0
    if EVENTSFILE.exists():
        for line in EVENTSFILE.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
                if entry.get("session_id") != session_id:
                    continue
                seen.add(entry.get("text", ""))
                bubble_seq = max(bubble_seq, int(entry.get("bubble_seq", 0) or 0))
            except json.JSONDecodeError:
                pass
            except (TypeError, ValueError):
                pass
    return seen, bubble_seq


def load_session_context(
    filepath: str, companion: str, session_id: str | None, manifest_path: str | None
) -> dict:
    """Load session metadata written by glimmer-claude."""
    context = {
        "session_id": session_id,
        "raw_path": filepath,
        "companion": companion,
        "manifest_path": manifest_path,
    }
    if not manifest_path:
        return context

    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return context

    if not isinstance(manifest, dict):
        return context

    for key in SESSION_CONTEXT_KEYS:
        if key in manifest:
            context[key] = manifest.get(key)
    return context


def request_stop(_signum, _frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True


def build_entry(
    text: str,
    companion: str,
    session_ctx: dict,
    bubble_seq: int,
    trigger_ctx: dict,
    timestamp: str,
) -> dict:
    entry = {
        "timestamp": timestamp,
        "companion": companion,
        "text": text,
        "source": "auto",
        "bubble_seq": bubble_seq,
        "session_id": session_ctx.get("session_id"),
        "cwd": session_ctx.get("cwd"),
        "project_root": session_ctx.get("project_root"),
        "project_name": session_ctx.get("project_name"),
        "git_branch": session_ctx.get("git_branch"),
        "is_repo_root": session_ctx.get("is_repo_root"),
        "session_profile": session_ctx.get("session_profile"),
        "trigger_type": trigger_ctx.get("trigger_type", "unknown"),
        "trigger_confidence": trigger_ctx.get("trigger_confidence", "none"),
        "emote_verb": extract_emote_verb(text),
    }
    if "raw_path" in session_ctx:
        entry["raw_path"] = session_ctx.get("raw_path")
    if trigger_ctx.get("trigger_text"):
        entry["trigger_text"] = trigger_ctx["trigger_text"]
    return entry


def build_legacy_entry(text: str, companion: str, timestamp: str) -> dict:
    return {
        "timestamp": timestamp,
        "companion": companion,
        "text": text,
    }


def log_legacy_entry(entry: dict) -> None:
    ensure_private_parent(LOGFILE)
    with advisory_lock(lock_path_for(LOGFILE)):
        with open(LOGFILE, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    set_permissions(LOGFILE, PRIVATE_FILE_MODE)


def log_event_entry(entry: dict) -> None:
    ensure_private_parent(EVENTSFILE)
    with advisory_lock(lock_path_for(EVENTSFILE)):
        with open(EVENTSFILE, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    set_permissions(EVENTSFILE, PRIVATE_FILE_MODE)


def scan_buffer(
    buf: str,
    session_seen: set[str],
    pending_bubbles: dict[str, dict],
    companion: str,
    session_ctx: dict,
    bubble_seq: int,
    final_pass: bool = False,
) -> int:
    """Extract and persist unseen bubbles from the current buffer."""
    cleaned = strip_ansi(buf)
    bubbles = extract_bubble_candidates(cleaned)
    current_candidates = set()
    for bubble in bubbles:
        bubble_text = bubble["text"]
        if bubble_text in session_seen:
            continue

        trigger_ctx = classify_trigger(cleaned, bubble)
        state = pending_bubbles.get(bubble_text)
        if state is None:
            related_text = find_related_pending_text(pending_bubbles, bubble_text)
            if related_text and related_text != bubble_text:
                related_state = pending_bubbles.pop(related_text)
                if bubble_text.startswith(related_text):
                    # The same bubble grew between scans. Prefer the fuller text
                    # and wait for that longer version to stabilize.
                    pending_bubbles[bubble_text] = {
                        "stable_scans": 1,
                        "trigger_ctx": trigger_ctx,
                    }
                    current_candidates.add(bubble_text)
                    if not final_pass:
                        continue
                    state = pending_bubbles[bubble_text]
                else:
                    # A shorter redraw should not displace the longest pending
                    # version we have already seen.
                    pending_bubbles[related_text] = related_state
                    current_candidates.add(related_text)
                    continue

        current_candidates.add(bubble_text)
        if state is None:
            pending_bubbles[bubble_text] = {
                "stable_scans": 1,
                "trigger_ctx": trigger_ctx,
            }
            continue

        state["stable_scans"] += 1
        state["trigger_ctx"] = trigger_ctx
        if state["stable_scans"] < STABLE_SCAN_COUNT and not final_pass:
            continue

        session_seen.add(bubble_text)
        bubble_seq += 1
        timestamp = datetime.now(timezone.utc).isoformat()
        legacy_entry = build_legacy_entry(bubble_text, companion, timestamp)
        event_entry = build_entry(
            bubble_text,
            companion,
            session_ctx,
            bubble_seq,
            state["trigger_ctx"],
            timestamp,
        )
        log_legacy_entry(legacy_entry)
        log_event_entry(event_entry)
        pending_bubbles.pop(bubble_text, None)
        preview = bubble_text[:60]
        suffix = "..." if len(bubble_text) > 60 else ""
        debug(f'[glimmer-watcher] Caught: "{preview}{suffix}"')

    for bubble_text in list(pending_bubbles):
        if bubble_text not in current_candidates:
            pending_bubbles.pop(bubble_text, None)
    return bubble_seq


def tail_and_watch(filepath: str, companion: str, session_ctx: dict):
    """Tail the typescript file and scan for bubbles."""
    # Track what we've already scanned in this session to avoid re-processing
    session_seen, bubble_seq = load_session_state(session_ctx.get("session_id"))
    pending_bubbles: dict[str, dict] = {}
    file_pos = 0
    buf = ""

    debug(f"[glimmer-watcher] Watching for {companion}'s speech bubbles...")
    debug(f"[glimmer-watcher] Logging to {LOGFILE}")
    if session_ctx.get("session_id"):
        debug(f"[glimmer-watcher] Session: {session_ctx['session_id']}")

    while True:
        try:
            with open(filepath, "rb") as f:
                f.seek(file_pos)
                new_data = f.read()
                if new_data:
                    file_pos += len(new_data)
                    # Decode with errors='replace' for safety
                    buf += new_data.decode("utf-8", errors="replace")
                    # Keep buffer manageable — only keep last ~50KB
                    if len(buf) > 50000:
                        buf = buf[-40000:]
        except FileNotFoundError:
            pass

        if buf:
            bubble_seq = scan_buffer(
                buf,
                session_seen,
                pending_bubbles,
                companion,
                session_ctx,
                bubble_seq,
            )

        if STOP_REQUESTED:
            try:
                with open(filepath, "rb") as f:
                    f.seek(file_pos)
                    new_data = f.read()
                    if new_data:
                        file_pos += len(new_data)
                        buf += new_data.decode("utf-8", errors="replace")
            except FileNotFoundError:
                pass

            if buf:
                bubble_seq = scan_buffer(
                    buf,
                    session_seen,
                    pending_bubbles,
                    companion,
                    session_ctx,
                    bubble_seq,
                    final_pass=True,
                )
            break

        time.sleep(SCAN_INTERVAL)


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: glimmer-watcher.py <typescript-file> [companion-name] [session-id] [manifest-path]"
        )
        sys.exit(1)

    filepath = sys.argv[1]
    companion = sys.argv[2] if len(sys.argv) > 2 else "Glimmer"
    session_id = sys.argv[3] if len(sys.argv) > 3 else None
    manifest_path = sys.argv[4] if len(sys.argv) > 4 else None
    session_ctx = load_session_context(filepath, companion, session_id, manifest_path)

    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    EVENTSFILE.parent.mkdir(parents=True, exist_ok=True)
    WATCHERLOG.parent.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    try:
        tail_and_watch(filepath, companion, session_ctx)
    except KeyboardInterrupt:
        debug("[glimmer-watcher] Stopped.")


if __name__ == "__main__":
    main()
