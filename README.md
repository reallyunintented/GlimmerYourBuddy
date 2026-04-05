# ✨ Glimmer — Local Significance Archive for Claude Buddy Bubbles

> *hovers closer, squinting at the README* Building a museum of me. Meta enough?

Your Claude Code buddy says things in speech bubbles — small observations, code hints, reactions — and then they scroll away. Glimmer catches them before they disappear.

It keeps a local archive with session context, mattered signals, and a review loop. No screenshots. No copying. No uploading. Just a usable history of the moments that actually changed the work.

---

## 🎯 What It Does

When you use Claude Code with Glimmer enabled, it:
- **Watches** your Claude Code terminal in real-time
- **Detects** speech bubbles from your buddy companion
- **Logs** them instantly with timestamps
- **Keeps the terminal clean** by writing watcher debug output to a separate file
- **Groups** auto-captured bubbles by Claude session
- **Stores exact session context** like cwd, project name, repo root, and branch
- **Tags** exact `/buddy pet` reactions and best-effort post-prompt bubbles
- **Lets you browse** them in a local archive UI with recent, mattered, review, project, session, and search views
- **Lets you mark** a bubble as mattered, attach a short note, and move it through a review state
- **Surfaces recurrence cues** so related mattered bubbles and repeated themes can come back later
- **Tracks explicit local revisits** with `last_used_at`, `use_count`, and `use_sources`
- **Derives honest staleness** so Glimmer can show what is still active, what is fading, and what needs to come back now
- **Exposes local interfaces** for people and tools through the UI, `glimmer-log`, and a small localhost JSON API

It is a local-first significance layer for things your Claude buddy said that actually changed the work.

---

## 🚀 Install

### Recommended Install
```bash
git clone https://github.com/reallyunintented/GlimmerYourBuddy.git
cd GlimmerYourBuddy
./install.sh
```

This keeps the install reviewable before anything lands in `~/.local/bin`.

<details>
<summary><strong>Verified Release Install</strong></summary>

Download a tagged release source archive plus its checksum assets, then verify before installing:
```bash
tar -xzf GlimmerYourBuddy-vX.Y.Z.tar.gz
cd GlimmerYourBuddy-vX.Y.Z

cosign verify-blob \
  --certificate SHA256SUMS.txt.pem \
  --signature SHA256SUMS.txt.sig \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp '^https://github.com/reallyunintented/GlimmerYourBuddy/.github/workflows/release.yml@refs/tags/vX\.Y\.Z$' \
  SHA256SUMS.txt

sha256sum -c SHA256SUMS.txt
./install.sh
```

If your system does not have `sha256sum`, use `shasum -a 256 -c SHA256SUMS.txt` instead.
</details>

<details>
<summary><strong>Remote Bootstrap (Higher Risk)</strong></summary>

```bash
export GLIMMER_REF=<pinned-commit>
curl -sSL "https://raw.githubusercontent.com/reallyunintented/GlimmerYourBuddy/${GLIMMER_REF}/install.sh" | bash
```

Pin the commit. Pulling installer files from a mutable branch is a supply-chain footgun. This path is less trustworthy than a reviewed clone or verified release — the installer runs before any file verification can happen.
</details>

The installer puts launchers into `~/.local/bin` and UI assets into `~/.local/share/glimmer/`. Make sure `~/.local/bin` is in your `$PATH`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

It also installs `glimmer-mcp` plus a Glimmer-owned Python runtime under `~/.local/share/glimmer/`, using `mcp==1.26.0` by default.

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

# Filter session-aware runs by exact context
glimmer-log --project GlimmerYourBuddy
glimmer-log --branch main
glimmer-log --cwd ~/src/GlimmerYourBuddy
glimmer-log --repo-root-only

# Search captured bubble text
glimmer-log --grep patience

# Remove old raw capture files
glimmer-log --cleanup-raw
glimmer-log --cleanup-raw 30

# Open the local archive app
glimmer-ui

# Show mattered bubbles and review buckets
glimmer-log --mattered
glimmer-log --review

# Build a project brief for the current work
glimmer-log --brief
glimmer-log --brief --markdown

# Mark the latest bubble and add a note
glimmer-log --mark latest --note "This changed the direction."

# Move a mattered bubble through the review loop
glimmer-log --review-state latest active

# Get stats
glimmer-log --stats

# Raw JSON (for processing)
glimmer-log --json
```

### Browse Them Visually
```bash
glimmer-ui
```

That opens a small local app for browsing recent bubbles, mattered bubbles, the review queue, projects, sessions, and search. You can mark a bubble as mattered, add a note, change its review state, inspect related mattered bubbles plus recurrence hints, and see derived staleness based on age and explicit revisit activity. It reads and writes only your local Glimmer files and does not upload anything.

The UI also has a `Brief` view: a compact "before you begin" panel that pulls the top mattered bubbles, active items, and recurring signals for a project, with copy buttons for plain text or markdown agent context.

`glimmer-ui` binds to `127.0.0.1` by default. Keep it on loopback unless you intentionally proxy or expose it yourself.

If you deliberately expose it, Glimmer now requires HTTP Basic auth for non-loopback binds. Set a password first:
```bash
export GLIMMER_UI_AUTH_TOKEN="$(openssl rand -hex 24)"
glimmer-ui --host 0.0.0.0 --allow-remote
```

Then connect with username `glimmer` and that password, or change the username with `--auth-user`.

See [`SECURITY.md`](SECURITY.md) for the current threat model and operational guidance.

### Use the Local API
When `glimmer-ui` is running, it also exposes a small localhost JSON API:

```bash
curl -s http://127.0.0.1:8767/api/review
curl -s http://127.0.0.1:8767/api/mattered
curl -s "http://127.0.0.1:8767/api/brief?project=GlimmerYourBuddy"
curl -s http://127.0.0.1:8767/api/bubbles/<bubble-id>
```

Current routes:
- `GET /api/index`
- `GET /api/mattered`
- `GET /api/review`
- `GET /api/brief?project=...`
- `GET /api/search?q=...`
- `GET /api/bubbles/:id`
- `POST /api/matters`
- `POST /api/review-state`

This API is local-only and meant to support the UI first. It is also the foundation for future agent integrations.

Review lifecycle:
- `unreviewed` — newly marked, not triaged yet
- `active` — still relevant and worth keeping in working memory
- `resolved` — handled and can rest without active attention now
- `stale` — cooled off or no longer worth carrying

### Use as an MCP Server
Glimmer includes a read-only MCP server so Claude Code agents can query your archive directly.

The `./install.sh` script provisions a Glimmer-owned Python runtime automatically — no manual `pip install` needed. By default it uses `mcp==1.26.0`, and you can override that with `GLIMMER_MCP_PYPI_SPEC` if you intentionally want a different version. If the host lacks `python3-venv`, Glimmer falls back to a local vendored runtime under `~/.local/share/glimmer/`.

Add Glimmer to Claude Code with:

```bash
claude mcp add --transport stdio --scope user glimmer -- glimmer-mcp
```

If you prefer to edit the config directly, user-scoped MCP servers live in `~/.claude.json`:
```json
{
  "mcpServers": {
    "glimmer": {
      "command": "glimmer-mcp",
      "type": "stdio"
    }
  }
}
```

Available tools:
- `get_brief` — Project brief with top mattered bubbles, active items, and recurring signals
- `list_mattered` — All mattered bubbles with counts by review state
- `get_review` — Mattered bubbles grouped by review state plus resurface hints
- `search_bubbles` — Case-insensitive search across bubble text, notes, and metadata
- `get_bubble` — Full detail for a single bubble including session and project context

The tools do not mutate captured bubbles, mattered marks, or review state. Successful tool calls do update `usage.json` so Glimmer can track explicit local revisit activity.

### Start With a Brief
If you want a small project-specific memory snapshot before a session starts, you now have three paths:

```bash
# In the terminal
glimmer-log --brief
glimmer-log --brief --markdown

# In the local app
glimmer-ui

# Right before Claude starts
glimmer-claude --glimmer-brief
```

The brief pulls from the same local mattered/review/recurrence/staleness data as the UI and API. It is meant to answer one question quickly: what should I remember before I continue here, and what is fading enough to bring back now?

### Explicit Local Usage Tracking
Glimmer now keeps a local `usage.json` summary alongside the archive. This is intentionally narrow and explicit:

- UI brief loads, bubble detail opens, matter toggles, and review-state changes count as use
- `glimmer-log --brief`, `--mattered`, `--review`, `--mark`/`--unmark`, and `--review-state` count as use
- MCP tool results count as use for the bubbles actually returned

Glimmer stores only durable local facts:

- `last_used_at`
- `use_count`
- `use_sources`

This is not an inferred importance score. Glimmer does not try to guess meaning from vague behavior yet.

Staleness is derived from those explicit facts only. There is no separate staleness store and no AI interpretation layer behind it.

### Watcher Debug Output
By default, Glimmer keeps the watcher quiet so it does not scribble across Claude's fullscreen UI.

If you want to see watcher debug lines live anyway, run:
```bash
GLIMMER_WATCHER_STDOUT=1 glimmer-claude
```

### Raw Transcript Retention
Raw terminal capture is sensitive. If you want Glimmer to delete the raw `script` transcript as soon as the watcher is finished with it, run:
```bash
GLIMMER_KEEP_RAW=0 glimmer-claude
```

Structured bubble data still stays in the normal Glimmer archive.

### Manually Add a Bubble
Heard something great and want to log it manually?
```bash
glimmer-log --add "This is something brilliant my buddy said"
```

Manual adds use your configured Claude companion name when available.

---

## 💾 Where It's Stored

Everything lives under `~/.claude/glimmer/`. Nothing leaves your machine.

```
log.jsonl      plain bubble history (stable, simple)
events.jsonl   richer auto-capture metadata (sessions, triggers, repo context)
sessions/      one manifest per Claude run
raw/           raw terminal recordings (can be auto-deleted)
watcher.log    watcher debug output
mattered.json  explicit mattered marks, notes, and review state
usage.json     explicit local revisit summary (`last_used_at`, `use_count`, `use_sources`)
```

Permissions are tightened to user-only by default. `usage.json` records explicit local activity only; it is not a hidden event log or an inferred ranking model. See [CONTRIBUTING.md](CONTRIBUTING.md) for full storage schemas and architecture details.

---

## 🔧 How It Works

> *phases through the terminal screen* Local ghosts stay local. Logs forget us.

- **`glimmer-claude`** starts Claude inside `script`, creates a session id, writes a session manifest, and launches the watcher.
- **`glimmer-watcher.py`** tails the raw terminal capture, strips ANSI control sequences, finds speech bubbles, waits for stable text, and writes logs.
- **`glimmer-log`** reads the plain history or the richer sidecar metadata, and can build project briefs.
- **`glimmer-ui`** serves the local archive app with mattered marks, review state, recurrence cues, and a localhost JSON API.

Each captured bubble gets a **trigger tag**: `buddy_pet` (exact `/buddy pet` match), `post_prompt` (best-effort), or `unknown` (honest about what it can't attribute). Session context (project, cwd, branch) is tracked separately from triggers.

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

### Start Claude with a project brief first
```bash
$ glimmer-claude --glimmer-brief
[glimmer-claude] Brief for this project
Brief: GlimmerYourBuddy
Scope: cwd  cwd=/home/notprinted/glimmer
Mattered: 4  Active: 2  Unreviewed: 1  Resolved: 1  Stale: 0
```

### Later, before they scroll away forever
```bash
$ glimmer-log --session latest

Session: 20260403-142215-12345
Companion: Glimmer
Started: 2026-04-03 14:22
Ended: 2026-04-03 14:30
Bubbles: 3
Project: GlimmerYourBuddy
Branch: main
CWD: /home/user/src/GlimmerYourBuddy
Repo root: /home/user/src/GlimmerYourBuddy
At repo root: yes

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
  project=GlimmerYourBuddy  branch=main  cwd=.
2026-04-03 09:05  20260403-090500-99887
  Glimmer  1 bubbles  ended 2026-04-03 09:06
  project=notes  branch=-  cwd=/home/user
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
✅ **Local archive UI** — Recent, mattered, review, projects, sessions, and search  
✅ **Human signal** — Mark bubbles as mattered, attach notes, and move them through review states  
✅ **Recurrence cues** — Related mattered bubbles and repeated themes can resurface later  
✅ **Usage tracking** — Explicit local revisit counts and sources across UI, CLI, and MCP  
✅ **Derived staleness** — Active, fading, and needs-return signals from age plus revisit history  
✅ **Local machine interface** — `glimmer-log` mattered/review commands plus localhost JSON routes  
✅ **Lightweight** — Small local toolchain, minimal dependencies  
✅ **Privacy-first** — Everything stays on your machine  
✅ **Portable** — Works on any system with Python 3.7+ and Claude Code  

---

## 🧰 Troubleshooting

### `glimmer-log --sessions` shows nothing
Only newer runs have session metadata. Older bubbles still remain visible in the plain all-time log.

Start one fresh run with:
```bash
glimmer-claude
```

### `Review` is empty
The review loop only starts once you mark a bubble as mattered.

Try:
```bash
glimmer-log --mark latest --note "Worth revisiting."
glimmer-log --review
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
- Digest and recap commands
- Better recurrence heuristics

---

## 📄 License

MIT — Use it, modify it, share it. Your buddy would approve.

Full license text lives in [`LICENSE`](LICENSE).

---

<div align="center">

**Your buddy says things that change the work. Glimmer makes sure you don't lose them.**

[Issues](https://github.com/reallyunintented/GlimmerYourBuddy/issues) · [Discussions](https://github.com/reallyunintented/GlimmerYourBuddy/discussions)

</div>
