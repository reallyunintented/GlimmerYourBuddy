# ✨ Glimmer — Your Buddy's Wisdom, Forever

Ever loved something your Claude Code buddy said, but the comment disappeared after 10 seconds? **Glimmer** captures those precious speech bubbles so you can keep them forever.

No screenshots. No copying. Just memories.

---

## 🎯 What It Does

When you use Claude Code with Glimmer enabled, it:
- **Watches** your Claude Code terminal in real-time
- **Detects** speech bubbles from your buddy companion
- **Logs** them instantly with timestamps
- **Lets you view** them anytime with a simple command

It's like having a journal of your buddy's wisest, funniest, and most helpful comments.

---

## 🚀 Install

### Quick Start (One Command)
```bash
curl -sSL https://raw.githubusercontent.com/reallyunintented/GlimmerYourBuddy/main/install.sh | bash
```

Then make sure `~/.local/bin` is in your `$PATH`. If you see a warning, add this to `~/.bashrc` or `~/.zshrc`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Manual Install
```bash
git clone https://github.com/reallyunintented/GlimmerYourBuddy.git
cd GlimmerYourBuddy
chmod +x glimmer-* install.sh
cp glimmer-* ~/.local/bin/
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

# Get stats
glimmer-log --stats

# Raw JSON (for processing)
glimmer-log --json
```

### Manually Add a Bubble
Heard something great and want to log it manually?
```bash
glimmer-log --add "This is something brilliant my buddy said"
```

---

## 💾 Where It's Stored

All bubbles are saved locally in:
```
~/.claude/glimmer/log.jsonl
```

Each entry looks like:
```json
{
  "timestamp": "2026-04-03T14:22:15+00:00",
  "companion": "Glimmer",
  "text": "Your buddy said something witty here"
}
```

**Your data stays on your machine.** Glimmer never uploads anything.

---

## 🔧 How It Works

- **`glimmer-claude`** — Wrapper that runs Claude Code and pipes output to the watcher
- **`glimmer-watcher.py`** — Tails your session in real-time, detects rounded-box bubbles, logs unique ones
- **`glimmer-log`** — Reader that displays, searches, and exports your captured bubbles

---

## 📚 Examples

### Start capturing your buddy's wisdom
```bash
$ glimmer-claude
Starting Claude Code with Glimmer logging...
  Companion: Glimmer
  Log file:  ~/.claude/glimmer/log.jsonl
```

### Later, relive the memories
```bash
$ glimmer-log

  2026-04-03 14:22  Glimmer
  "You're overthinking this. Just ship it."

  2026-04-03 14:25  Glimmer
  "That's a clever approach to the race condition."

  2026-04-03 14:30  Glimmer
  "Remember to test the edge case where the user has no permissions."
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
✅ **Lightweight** — ~300 lines of Python, minimal dependencies  
✅ **Privacy-first** — All data stays local  
✅ **Simple** — Just 3 scripts, no bloat  
✅ **Portable** — Works on any system with Python 3.7+ and Claude Code  

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
