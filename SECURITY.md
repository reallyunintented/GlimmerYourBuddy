# Security Policy

## Scope

Glimmer is a local-first tool. Its intended trust boundary is:

- local files in the current user's home directory
- loopback-only HTTP access from the same machine
- reviewed installs from a local clone or a pinned commit

Anything outside that boundary should be treated as a deliberate expansion of risk.

## Supported Hardening Baseline

The current baseline is:

- archive files and directories are written with private permissions where possible
- `glimmer-ui` binds to `127.0.0.1` by default
- non-loopback binds require `--allow-remote`
- browser POST requests are restricted to same-origin requests
- mutable archive files use atomic replace-on-write updates

## What To Report

Please report issues that can lead to:

- remote code execution
- archive exfiltration
- unintended network exposure
- cross-origin request abuse against the local UI
- privilege or permission boundary failures
- install-chain or update-chain compromise

## What Not To Assume

The following are not security guarantees:

- keeping raw terminal transcripts forever
- exposing `glimmer-ui` on `0.0.0.0` without another auth boundary
- installing from a mutable branch with `curl | bash`

## Operational Guidance

- Prefer `git clone` plus local review before install.
- If you use remote install, pin `GLIMMER_REF` to a commit.
- Use `GLIMMER_KEEP_RAW=0` if you do not want raw `script` transcripts retained.
- If you expose `glimmer-ui` remotely, put it behind your own authentication and network controls.

## Reporting

Open a private channel if you have one available. If not, file a GitHub issue with only high-level impact details and avoid publishing exploit steps until a fix exists.
