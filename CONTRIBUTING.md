# Contributing

Found a bug? Have a feature idea? Love Glimmer and want to help?

## Ideas for Improvement

- **Export formats** — HTML, JSON, plaintext collections
- **Stats** — More detailed analytics on buddy comments
- **Sync** — Optional cloud backup (respecting privacy)
- **Themes** — Alternative visual treatments for `glimmer-ui`
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
- `glimmer-session.py`
  Detects exact repo context for the session manifest and finalizes manifests on exit.
- `glimmer-watcher.py`
  Parses the raw terminal recording, extracts stable speech-bubble text, writes plain entries to `log.jsonl`, and writes richer auto-capture metadata to `events.jsonl`.
- `glimmer-log`
  Reads `log.jsonl` for the all-time plain view and reads `events.jsonl` plus `sessions/` for grouped session output.
- `glimmer-ui`
  Runs the local archive app over localhost, merges mattered marks, and serves the frontend from `ui/`.

Important storage paths:

- `~/.claude/glimmer/log.jsonl`
  Plain compatibility log. Keep this shape stable.
- `~/.claude/glimmer/events.jsonl`
  Auto-capture sidecar metadata. Session ids, exact repo context, and trigger tags belong here.
- `~/.claude/glimmer/sessions/`
  One manifest per run.
- `~/.claude/glimmer/raw/`
  Raw `script` recordings used for parser debugging.
- `~/.claude/glimmer/watcher.log`
  Watcher debug output. The watcher should stay quiet on the Claude UI unless explicitly requested.
- `~/.claude/glimmer/mattered.json`
  Explicit mattered marks and optional notes created in the local archive UI.

## How Capture Works

This is the internal flow:

1. `glimmer-claude` creates a session id.
2. It starts `script` and writes raw terminal output to `~/.claude/glimmer/raw/`.
3. It detects exact repo context from the launch cwd and writes a session manifest to `~/.claude/glimmer/sessions/`.
4. It starts `glimmer-watcher.py` in the background.
5. The watcher tails the raw file, strips ANSI control sequences, and preserves cursor-based spacing used by Claude's UI.
6. The watcher looks for rounded speech-bubble boxes and extracts their visible text.
7. The watcher requires the same bubble text to survive more than one scan before it logs it.
8. The plain bubble is appended to `log.jsonl`.
9. The richer auto-capture event is appended to `events.jsonl`.
10. `glimmer-ui` can layer mattered marks and notes on top of captured bubbles via `mattered.json`.
11. When the session exits, `glimmer-claude` fills in `ended_at` in the manifest and stops the watcher.

Why the split exists:

- `log.jsonl` must stay stable and simple for compatibility.
- `events.jsonl` can evolve to hold session ids, exact repo context, trigger metadata, and future sidecar fields.
- `mattered.json` is user-authored signal and should stay separate from passive capture data.
- watcher debug output belongs in `watcher.log`, not on the shared fullscreen Claude terminal.

## Manifest Schema

Each session manifest stores:

- `session_id`
- `started_at`
- `ended_at`
- `companion`
- `raw_path`
- `argv`
- `cwd`
- `project_root`
- `project_name`
- `git_branch`
- `is_repo_root`

`events.jsonl` copies the same session context fields into each auto-captured event. `log.jsonl` must not grow these fields.

## Repo Context Rules

Repo context is exact and intentionally limited:

- `cwd`
  The launch directory from shell `pwd`.
- `project_root`
  `git rev-parse --show-toplevel` when inside a repo, else `null`.
- `project_name`
  `basename(project_root)` when inside a repo, else `basename(cwd)`.
- `git_branch`
  `git rev-parse --abbrev-ref HEAD` when inside a repo. Detached HEAD is reported as `HEAD`.
- `is_repo_root`
  Exact string comparison: `cwd == project_root`.

Do not add inferred categories like "random question", "personal vs work", or "unrelated to project". Those require prompt capture or guesswork, which Glimmer avoids.

## Trigger Attribution

Auto-captured events can include:

- `buddy_pet`
  Exact when `/buddy pet` is visible before the bubble.
- `post_prompt`
  Best-effort when a bubble appears after prompt completion.
- `unknown`
  Used when the watcher cannot honestly attribute the bubble.

These tags belong in `events.jsonl`, not in `log.jsonl`.

Trigger attribution is separate from project context. Do not collapse them into a single reason field.

## Code Style

- Shell scripts: keep it simple and portable (bash 4+)
- Python: follow PEP 8
- Comments: explain *why*, not what

## Testing

Automated coverage lives under `tests/` and should cover:

- manifest context detection inside a repo root
- manifest context detection inside a repo subdirectory
- manifest context detection outside any repo
- detached HEAD reporting
- watcher event shape, including exact session context copy-through
- `glimmer-log --sessions`
- `glimmer-log --session latest`
- `glimmer-log --project`
- `glimmer-log --branch`
- `glimmer-log --cwd`
- `glimmer-log --grep`
- `glimmer-log --cleanup-raw`
- `glimmer-ui` index aggregation
- mattered mark and note merging

Run the automated suite with:

```bash
python3 -m unittest discover -s tests -v
```

Manual QA still matters for the parser and fullscreen UI. You can trigger it with:

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
- `events.jsonl` keeps session, exact repo context, and trigger metadata
- mattered marks remain local-only and do not mutate capture logs
- the latest session manifest gets both `started_at` and `ended_at` plus correct repo context
- a large or slowly painted bubble is not saved too early
- the watcher still performs a final scan on shutdown
- session headers and `glimmer-log` filters match the real cwd, repo root, project name, and branch

Recommended manual flows:

- launch from a repo root
- launch from a nested repo subdirectory
- launch from a home directory outside a repo
- trigger `/buddy pet`
- ask a normal coding question
- verify `glimmer-log --sessions`, `glimmer-log --session latest`, and context filters against what actually happened

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
