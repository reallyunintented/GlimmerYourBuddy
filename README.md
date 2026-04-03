# ✨ Glimmer — Your Buddy's Wisdom, Forever

Ever loved something your Claude Code buddy said, but the comment disappeared after 10 seconds? **Glimmer** captures those precious speech bubbles so you can keep them forever.

No screenshots. No copying. Just memories.

---

## 🎯 What It Does

When you use Claude Code with Glimmer enabled, it:
- **Watches** your Claude Code terminal in real-time
- **Detects** speech bubbles from your buddy companion
- **Logs** them instantly with timestamps
- **Keeps the terminal clean** by writing watcher debug output to a separate file
- **Groups** auto-captured bubbles by Claude session
- **Tags** exact `/buddy pet` reactions and best-effort post-prompt bubbles
- **Lets you view** them anytime with a simple command

It's like having a journal of your buddy's wisest, funniest, and most helpful comments.

---

## 🚀 Install

### Quick Start (One Command)
```bash
curl -sSL https://raw.githubusercontent.com/reallyunintented/GlimmerYourBuddy/main/install.sh | bash
```

The installer downloads the Glimmer scripts into `~/.local/bin`. Then make sure `~/.local/bin` is in your `$PATH`. If you see a warning, add this to `~/.bashrc` or `~/.zshrc`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Manual Install
```bash
git clone https://github.com/reallyunintented/GlimmerYourBuddy.git
cd GlimmerYourBuddy
./install.sh
```

---

## 📖 Usage

### Start Claude Code with Capturing
Instead of `claude`, run:
```bash
glimmer-claude
```

It starts your normal Claude Code session **and** captures every speech bubble your buddy makes.

### View Your Captured Bubbles
```bash
# See all bubbles you've captured
glimmer-log

# See the last 10
glimmer-log -n 10

# List session-aware runs
glimmer-log --sessions

# Open the newest session
glimmer-log --session latest

# Get stats
glimmer-log --stats

# Raw JSON (for processing)
glimmer-log --json
```

### Watcher Debug Output
By default, Glimmer keeps the watcher quiet so it does not scribble across Claude's fullscreen UI.

If you want to see watcher debug lines live anyway, run:
```bash
GLIMMER_WATCHER_STDOUT=1 glimmer-claude
```

### Manually Add a Bubble
Heard something great and want to log it manually?
```bash
glimmer-log --add "This is something brilliant my buddy said"
```

---

## 💾 Where It's Stored

Glimmer writes a few local files on purpose. They have different jobs.

### `~/.claude/glimmer/log.jsonl`
This is the compatibility log. It is the main "plain bubble history" file.

Each line is a simple JSON object:
```json
{
  "timestamp": "2026-04-03T14:22:15+00:00",
  "companion": "Glimmer",
  "text": "Your buddy said something witty here"
}
```

This file is meant to stay simple and stable. It is what `glimmer-log`, `glimmer-log -n`, `glimmer-log --json`, and `glimmer-log --stats` use for the all-time view.

### `~/.claude/glimmer/events.jsonl`
This is the richer sidecar event log for auto-captured bubbles.

It stores session metadata and trigger tagging without polluting `log.jsonl`:
```json
{
  "timestamp": "2026-04-03T14:22:15+00:00",
  "companion": "Glimmer",
  "text": "Your buddy said something witty here",
  "source": "auto",
  "session_id": "20260403-142215-12345",
  "bubble_seq": 4,
  "trigger_type": "buddy_pet",
  "trigger_confidence": "exact",
  "trigger_text": "/buddy pet"
}
```

This file is what `glimmer-log --sessions` and `glimmer-log --session ...` use.

### `~/.claude/glimmer/sessions/`
This directory holds one manifest per Claude run:
```json
{
  "session_id": "20260403-142215-12345",
  "started_at": "2026-04-03T14:22:15+00:00",
  "ended_at": "2026-04-03T14:30:02+00:00",
  "companion": "Glimmer",
  "raw_path": "/home/user/.claude/glimmer/raw/session-20260403-142215-12345.raw",
  "argv": ["claude"]
}
```

These manifests let Glimmer list sessions even if a run had zero captured bubbles.

### `~/.claude/glimmer/raw/`
This directory holds the raw terminal capture from `script`.

Glimmer does not show these files in normal use, but they are the source material the watcher parses.

### `~/.claude/glimmer/watcher.log`
This is the watcher's own debug log.

The watcher writes its internal status here instead of printing into Claude's fullscreen UI by default.

### Summary
All bubbles are still saved locally. The split is:
```
log.jsonl      plain bubble history
events.jsonl   richer auto-capture metadata
sessions/      one manifest per Claude run
raw/           raw terminal recordings
watcher.log    watcher debug output
```

**Your data stays on your machine.** Glimmer never uploads anything.

---

## 🔧 How It Works

### The Short Version
- **`glimmer-claude`** starts Claude inside `script`, creates a session id, writes a session manifest, and launches the watcher.
- **`glimmer-watcher.py`** tails the raw terminal capture, strips ANSI control sequences, finds speech bubbles, waits for stable text, and writes logs.
- **`glimmer-log`** reads either the simple history or the richer sidecar metadata depending on the command you ask for.

### Trigger Tagging
For auto-captured entries, Glimmer also stores trigger metadata in `events.jsonl`:

- `buddy_pet`
  Exact when the watcher can see `/buddy pet` before the bubble.
- `post_prompt`
  Best-effort when a bubble appears after prompt completion.
- `unknown`
  Used when the watcher cannot honestly attribute the bubble.

The plain `log.jsonl` file does not include these extra fields on purpose.

---

## 📚 Examples

### Start capturing your buddy's wisdom
```bash
$ glimmer-claude
Starting Claude Code with Glimmer logging...
  Companion: Glimmer
  Session:   20260403-142215-12345
  Log file:  ~/.claude/glimmer/log.jsonl
```

### Later, relive the memories
```bash
$ glimmer-log --session latest

Session: 20260403-142215-12345
Companion: Glimmer
Started: 2026-04-03 14:22
Ended: 2026-04-03 14:30
Bubbles: 3

  2026-04-03 14:22  Glimmer  #1
  "You're overthinking this. Just ship it."

  2026-04-03 14:25  Glimmer  #2
  "That's a clever approach to the race condition."

  2026-04-03 14:30  Glimmer  #3
  "Remember to test the edge case where the user has no permissions."
```

### See all known sessions
```bash
$ glimmer-log --sessions
2026-04-03 14:22  20260403-142215-12345  latest
  Glimmer  3 bubbles  ended 2026-04-03 14:30

Legacy entries without session metadata: 42
```

### Get stats on what your buddy says
```bash
$ glimmer-log --stats
Total bubbles captured: 47
First: 2026-04-01 09:15
Last:  2026-04-03 14:30
Average bubble length: 63 chars
Longest: "This is a really detailed explanation of why your approach..."
```

---

## ✨ Features

✅ **Real-time capture** — Bubbles logged as they appear  
✅ **Deduplication** — Won't log the same bubble twice  
✅ **Session-aware** — New runs get their own session IDs and manifests  
✅ **Trigger tagging** — Exact `/buddy pet` and best-effort post-prompt attribution  
✅ **Cleaner terminal UI** — Watcher debug output is separate by default  
✅ **More stable capture** — Bubble text must survive more than one scan before logging  
✅ **Lightweight** — ~300 lines of Python, minimal dependencies  
✅ **Privacy-first** — All data stays local  
✅ **Simple** — Just 3 scripts, no bloat  
✅ **Portable** — Works on any system with Python 3.7+ and Claude Code  

---

## 🧰 Troubleshooting

### `glimmer-log --sessions` shows nothing
Only newer runs have session metadata. Older bubbles still remain visible in the plain all-time log.

Start one fresh run with:
```bash
glimmer-claude
```

### Want more technical detail?
See [CONTRIBUTING.md](CONTRIBUTING.md) for implementation notes, storage details, and debugging workflow.

---

## 🛠️ Requirements

- **Python 3.7+**
- **Claude Code** (the CLI)
- **A terminal** that supports ANSI escape sequences (most modern terminals do)
- **`~/.local/bin` in your PATH** (usually there by default)

---

## 📝 Contributing

Have an idea? Found a bug? Want to add a feature?

Check out [CONTRIBUTING.md](CONTRIBUTING.md) for ideas and guidelines.

Some ideas:
- Export to HTML, Markdown, or other formats
- Search and filter bubbles by keyword or date
- IDE integration (VS Code, JetBrains, etc.)
- Buddy quote analytics

---

## 📄 License

MIT — Use it, modify it, share it. Your buddy would approve.

---

<div align="center">

**Made for anyone who cherishes their buddy's comments.**

[Issues](https://github.com/reallyunintented/GlimmerYourBuddy/issues) · [Discussions](https://github.com/reallyunintented/GlimmerYourBuddy/discussions)

</div>
