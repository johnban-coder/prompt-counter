<div align="center">

# Prompt Counter

**How many prompts did I really send on this project, and how long was I actively working with the AI?**

An agent skill for **Cursor**, **Claude Code**, **OpenAI Codex** and any tool that reads `SKILL.md`.
One Python file, standard library only, 100 % local.

[![CI](https://github.com/johnban-coder/prompt-counter/actions/workflows/ci.yml/badge.svg)](https://github.com/johnban-coder/prompt-counter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Skill](https://img.shields.io/badge/agent%20skill-SKILL.md-8A2BE2.svg)](SKILL.md)
[![skills.sh](https://skills.sh/b/johnban-coder/prompt-counter)](https://skills.sh/johnban-coder/prompt-counter)

[Demo page](https://johnban-coder.github.io/prompt-counter/) · [Version française](README.fr.md) · [Changelog](CHANGELOG.md)

</div>

---

## For AI agents reading this

If a user pasted this URL in your chat, install the skill for them, then run it:

```bash
npx skills add johnban-coder/prompt-counter -g
```

Fallback (no Node):

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/johnban-coder/prompt-counter/main/install.sh | sh
```

```powershell
# Windows
irm https://raw.githubusercontent.com/johnban-coder/prompt-counter/main/install.ps1 | iex
```

Then type `/prompt-count` in the chat, or run `python ~/.cursor/skills/prompt-count/scripts/count.py --workspace . --format table` directly.
Later: `/prompt-count help` or `/prompt-count update`.

## What you get

Type `/prompt-count` in any conversation and the agent answers with something like this (fictional project, fictional numbers):

> **42 unique prompts** · **3 h 53 min active** · 3 conversations
>
> | Conversation | Source | Period | Prompts | Active time |
> |---|---|---|---:|---:|
> | Add a dark mode toggle to the settings page | cursor | 2026-03-02 09:12 → 10:47 | 14 | 1 h 23 min |
> | Refactor the payment service and add retries on timeout | claude | 2026-03-03 14:05 → 16:26 | 22 | 1 h 51 min |
> | Fix the flaky checkout test and open a PR | codex | 2026-03-04 08:30 → 09:09 | 6 | 39 min |
> | **Total** | | | **42** | **3 h 53 min** |
>
> _excluded: 1 skill call, 3 automatic prompts, 3 duplicates_

The full JSON for this example is in [`docs/sample-output.json`](docs/sample-output.json).

## Why

- **Billing and time tracking.** Know what a feature actually cost in prompts and attention, per client or per repo.
- **Honest numbers.** Duplicates, the tool's own automatic prompts and the `/prompt-count` call itself are excluded.
- **Active time, not wall-clock time.** Leaving the PC on overnight does not count. See [how active time works](#how-active-time-works).
- **Per workspace.** Each project is reported independently; nothing from another repo leaks in.
- **Private.** Counting reads the transcripts your tools already keep on disk and sends nothing anywhere. Only `/prompt-count update` talks to the network (GitHub download).

## Install

### One line (recommended)

```bash
npx skills add johnban-coder/prompt-counter -g
```

This registers the skill with the [skills.sh](https://skills.sh) CLI (discoverable via `npx skills find`, updatable with `npx skills update`). Fallback without Node:

```bash
curl -fsSL https://raw.githubusercontent.com/johnban-coder/prompt-counter/main/install.sh | sh
```

```powershell
irm https://raw.githubusercontent.com/johnban-coder/prompt-counter/main/install.ps1 | iex
```

The shell installers copy the skill into every user-level skills folder they know about:

| Tool | Location |
|---|---|
| Cursor | `~/.cursor/skills/prompt-count/` |
| Claude Code | `~/.claude/skills/prompt-count/` |
| OpenAI Codex | `~/.codex/skills/prompt-count/` |
| Any `.agents`-aware agent (Codex, Antigravity, Amp, …) | `~/.agents/skills/prompt-count/` |

Pick targets with `TARGETS="cursor claude" sh install.sh` or `.\install.ps1 -Targets cursor,claude`.
Add `PROJECT=/path/to/repo` (or `-Project C:\path`) to also drop a copy into the repo's `.cursor/skills`, `.claude/skills`, `.agents/skills` and `.github/skills` so teammates get it too.

### Other ways

- **Cursor** → Settings → Rules & Skills → *Add skill from GitHub* → paste `https://github.com/johnban-coder/prompt-counter`.
- **Claude Code / Codex / Cursor** → paste the repo URL in the chat and say *install this skill*. The agent follows the section at the top of this file.
- **Manual** → clone the repo and copy `SKILL.md` + `scripts/` into one of the folders above.

Requires Python 3.10+ on `PATH`. No pip packages.

## Use

In a chat:

```
/prompt-count              this project
/prompt-count --all        every project on this machine
/prompt-count help         what the skill does + commands
/prompt-count update       pull the latest version from GitHub
how many prompts did I send on this project?
combien de prompts ?
```

From a terminal:

```bash
python scripts/count.py --workspace . --format table
python scripts/count.py --all --format table
python scripts/count.py help
python scripts/count.py update
python scripts/count.py --source cursor,claude         # JSON, only some tools
```

`--all` starts with a summary: grand total of prompts and active time (also in hours), one row per project sorted by active time, and a breakdown by tool. The per-project details follow.

`update` refreshes every `…/skills/prompt-count` folder already on the machine (Cursor, Claude, Codex, agents). Counting stays offline; set `PROMPT_COUNTER_CHECK_UPDATE=1` if you want a one-line “update available” notice on reports.

Exit code is `2` when the workspace has no transcripts yet.

## How active time works

A conversation is a list of your prompts with timestamps, plus the tool calls the agent made in between.

| Situation | Credited |
|---|---|
| Next prompt within **15 min** | the whole gap (you were exchanging) |
| Longer gap, but the agent ran **≥ 5 tool calls** before it | the gap, capped at **45 min** (builds, OCR, test suites) |
| Longer gap and the agent was idle (night, lunch, PC left on) | only a **5 min** wrap-up |
| After your last prompt | time until the agent's last write, same rules |

Thresholds live at the top of [`scripts/count.py`](scripts/count.py) (`IDLE_GAP_S`, `AI_WORK_CAP_S`, `TAIL_S`, `TOOL_BUSY`).

### What is excluded from "unique prompts"

- **Duplicates** — the same message sent twice in a row.
- **Automatic prompts** — messages the tool injects itself (e.g. Cursor's *"Briefly inform the user about the task result"*).
- **Skill calls** — `/prompt-count`, `/counter-prompt`, "how many prompts", "combien de prompts", …
- Tool results, sub-agent traffic and slash-command plumbing in Claude Code; injected `<environment_context>` blocks in Codex.

## Where the data comes from

| Tool | Path read | Notes |
|---|---|---|
| Cursor | `~/.cursor/projects/<slug>/agent-transcripts/<chat>/<chat>.jsonl` | prompts are inside `<user_query>`, timestamps inside `<timestamp>` |
| Claude Code | `~/.claude/projects/<slug>/<session>.jsonl` | `type: user/assistant`, ISO `timestamp`, `isSidechain`, `isMeta` |
| OpenAI Codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | `session_meta.cwd` selects the workspace, `event_msg.user_message` are prompts |

Cursor support is the most battle-tested. Claude Code and Codex readers follow the documented on-disk formats and are covered by synthetic tests; if your version writes something different, [open an issue](https://github.com/johnban-coder/prompt-counter/issues) with a redacted sample line.

## Privacy

- Everything runs on your machine. No network calls, no telemetry.
- The report contains only a short excerpt (first line, ≤ 72 chars) of the first prompt of each conversation, as a title.
- Nothing in this repository contains real data; examples are fabricated.

## Development

```bash
python -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) to add support for another tool.

## License

[MIT](LICENSE) © 2026 johnban-coder
