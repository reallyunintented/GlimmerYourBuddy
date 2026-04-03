# Contributing

Found a bug? Have a feature idea? Love Glimmer and want to help?

## Ideas for Improvement

- **Export formats** — HTML, JSON, plaintext collections
- **Search** — Find bubbles by keyword or date range
- **Stats** — More detailed analytics on buddy comments
- **Sync** — Optional cloud backup (respecting privacy)
- **Themes** — Custom display styles for `glimmer-log`
- **Integration** — IDE plugins to view bubbles within your editor

## Getting Started

1. Fork the repo
2. Make your changes
3. Test with `glimmer-claude` to ensure bubble detection still works
4. Submit a PR

## Architecture Notes

The runtime is split on purpose:

- `glimmer-claude`
  Starts Claude inside `script`, creates the session id, writes the session manifest, and launches the watcher.
- `glimmer-watcher.py`
  Parses the raw terminal recording, extracts stable speech-bubble text, writes plain entries to `log.jsonl`, and writes richer auto-capture metadata to `events.jsonl`.
- `glimmer-log`
  Reads `log.jsonl` for the all-time plain view and reads `events.jsonl` plus `sessions/` for grouped session output.

Important storage paths:

- `~/.claude/glimmer/log.jsonl`
  Plain compatibility log. Keep this shape stable.
- `~/.claude/glimmer/events.jsonl`
  Auto-capture sidecar metadata. Session ids and trigger tags belong here.
- `~/.claude/glimmer/sessions/`
  One manifest per run.
- `~/.claude/glimmer/raw/`
  Raw `script` recordings used for parser debugging.
- `~/.claude/glimmer/watcher.log`
  Watcher debug output. The watcher should stay quiet on the Claude UI unless explicitly requested.

## How Capture Works

This is the internal flow:

1. `glimmer-claude` creates a session id.
2. It starts `script` and writes raw terminal output to `~/.claude/glimmer/raw/`.
3. It writes a session manifest to `~/.claude/glimmer/sessions/`.
4. It starts `glimmer-watcher.py` in the background.
5. The watcher tails the raw file, strips ANSI control sequences, and preserves cursor-based spacing used by Claude's UI.
6. The watcher looks for rounded speech-bubble boxes and extracts their visible text.
7. The watcher requires the same bubble text to survive more than one scan before it logs it.
8. The plain bubble is appended to `log.jsonl`.
9. The richer auto-capture event is appended to `events.jsonl`.
10. When the session exits, `glimmer-claude` fills in `ended_at` in the manifest and stops the watcher.

Why the split exists:

- `log.jsonl` must stay stable and simple for compatibility.
- `events.jsonl` can evolve to hold session ids, trigger metadata, and future sidecar fields.
- watcher debug output belongs in `watcher.log`, not on the shared fullscreen Claude terminal.

## Trigger Attribution

Auto-captured events can include:

- `buddy_pet`
  Exact when `/buddy pet` is visible before the bubble.
- `post_prompt`
  Best-effort when a bubble appears after prompt completion.
- `unknown`
  Used when the watcher cannot honestly attribute the bubble.

These tags belong in `events.jsonl`, not in `log.jsonl`.

## Code Style

- Shell scripts: keep it simple and portable (bash 4+)
- Python: follow PEP 8
- Comments: explain *why*, not what

## Testing

The trickiest part is testing the bubble detection. You can manually trigger it:

```bash
# Run a real session:
glimmer-claude

# View the plain all-time log:
glimmer-log

# View session-aware output:
glimmer-log --sessions
glimmer-log --session latest
```

When changing parser behavior, check all of these:

- the live terminal stays readable and the watcher does not print across Claude's fullscreen UI
- `log.jsonl` remains plain and backward compatible
- `events.jsonl` keeps session and trigger metadata
- the latest session manifest gets both `started_at` and `ended_at`
- a large or slowly painted bubble is not saved too early
- the watcher still performs a final scan on shutdown

If you need live watcher output for debugging, use:

```bash
GLIMMER_WATCHER_STDOUT=1 glimmer-claude
```

Otherwise inspect:

```bash
tail -n 50 ~/.claude/glimmer/watcher.log
ls ~/.claude/glimmer/raw/
```

## Questions?

Open an issue. We're all learning here.

---

Thanks for helping make buddy memories last forever.
