#!/usr/bin/env python3
"""
Glimmer speech bubble watcher.

Tails a `script` typescript file, strips ANSI escape sequences,
detects rounded-box speech bubbles, and logs unique ones to JSONL.

Usage: glimmer-watcher.py <typescript-file> [companion-name]
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOGFILE = Path.home() / ".claude" / "glimmer" / "log.jsonl"
# How often to scan the buffer (seconds)
SCAN_INTERVAL = 1.5
# Minimum box width to consider (Glimmer's box is 34 chars)
MIN_BOX_WIDTH = 20
MAX_BOX_WIDTH = 50

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

# Rounded box characters
TOP_RE = re.compile(r"╭(─+)╮")
BOT_RE = re.compile(r"╰(─+)╯")
MID_RE = re.compile(r"│(.+?)│")


def strip_ansi(text: str) -> str:
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


def extract_bubbles(text: str) -> list[str]:
    """Find speech bubble content in cleaned terminal text."""
    lines = normalize_lines(text)
    bubbles = []
    i = 0
    while i < len(lines):
        top = TOP_RE.search(lines[i])
        if top:
            width = len(top.group(1)) + 2  # +2 for corners
            if MIN_BOX_WIDTH <= width <= MAX_BOX_WIDTH:
                content_lines = []
                j = i + 1
                while j < len(lines):
                    if BOT_RE.search(lines[j]):
                        break
                    mid = MID_RE.search(lines[j])
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
                        bubbles.append(bubble_text)
                i = j + 1
                continue
        i += 1
    return bubbles


def load_seen() -> set[str]:
    """Load previously logged bubble texts to avoid duplicates."""
    seen = set()
    if LOGFILE.exists():
        for line in LOGFILE.read_text().splitlines():
            try:
                entry = json.loads(line)
                seen.add(entry.get("text", ""))
            except json.JSONDecodeError:
                pass
    return seen


def log_bubble(text: str, companion: str):
    """Append a bubble to the log file."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "companion": companion,
        "text": text,
    }
    with open(LOGFILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def tail_and_watch(filepath: str, companion: str):
    """Tail the typescript file and scan for bubbles."""
    seen = load_seen()
    # Track what we've already scanned in this session to avoid re-processing
    session_seen: set[str] = set()
    file_pos = 0
    buf = ""

    print(f"[glimmer-watcher] Watching for {companion}'s speech bubbles...")
    print(f"[glimmer-watcher] Logging to {LOGFILE}")

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
            cleaned = strip_ansi(buf)
            bubbles = extract_bubbles(cleaned)
            for b in bubbles:
                if b not in seen and b not in session_seen:
                    seen.add(b)
                    session_seen.add(b)
                    log_bubble(b, companion)
                    print(f"[glimmer-watcher] Caught: \"{b[:60]}{'...' if len(b) > 60 else ''}\"")

        time.sleep(SCAN_INTERVAL)


def main():
    if len(sys.argv) < 2:
        print("Usage: glimmer-watcher.py <typescript-file> [companion-name]")
        sys.exit(1)

    filepath = sys.argv[1]
    companion = sys.argv[2] if len(sys.argv) > 2 else "Glimmer"

    LOGFILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        tail_and_watch(filepath, companion)
    except KeyboardInterrupt:
        print("\n[glimmer-watcher] Stopped.")


if __name__ == "__main__":
    main()
