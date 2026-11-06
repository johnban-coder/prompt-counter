---
name: prompt-count
description: Count the user's unique prompts and active interaction time per AI conversation for the current project (Cursor, Claude Code, Codex), or every project with --all. Use when the user runs /prompt-count, /prompt-counter, /counter-prompt, or asks "how many prompts did I send", "prompt count", "combien de prompts", "nombre de prompts", "temps actif", "temps passé", "durée" on a project.
---

# Prompt Counter

Answers "how many prompts did I really send on this project, and how long was I actively working with the AI?"
Everything runs locally from the transcripts Cursor, Claude Code and Codex already keep on disk. Nothing is sent anywhere.

## When

The user asks how many prompts they sent, how much active time a conversation took, or types `/prompt-count` (aliases: `/prompt-counter`, `/counter-prompt`).

## Run

Execute the bundled script. Do **not** rewrite it. Python 3.10+, standard library only.
`<skill-dir>` is the directory that contains this `SKILL.md` (for example `~/.cursor/skills/prompt-count`, `~/.claude/skills/prompt-count`, `~/.codex/skills/prompt-count`, `~/.agents/skills/prompt-count`, or `.cursor/skills/prompt-count` inside the repo).

```bash
python "<skill-dir>/scripts/count.py" --workspace . --format table
```

```powershell
python "<skill-dir>\scripts\count.py" --workspace . --format table
```

Flags:

- `--workspace .` — this project only (default). Always pass the project root so counts stay independent per workspace.
- `--all` — every project found on this machine, one block per project.
- `--source cursor,claude,codex` — restrict to some tools (default: all three).
- `--format json` — raw JSON if you need the numbers (`totals.unique_prompts`, `totals.duration`, `conversations[]`).

## Report

Lead with **N unique prompts** and **total active time**, then show the table the script printed (or build it from the JSON):

| Conversation | Source | Period | Prompts | Active time |
|---|---|---|---:|---:|
| `title` | `source` | `first` → `last_ai` | `unique_prompts` | `duration` |
| **Total** | | | totals.unique_prompts | totals.duration |

Explain **active time** in one sentence if the user has not seen it before:

- gap ≤ 15 min between two messages → counted (you and the agent are exchanging);
- longer gap while the agent was running many tools → counted, capped at 45 min (builds, OCR, test runs);
- PC left on, night, lunch, nobody typing → **not** counted (only a 5 min wrap-up).

One line under the table with what was excluded: `skill_calls` (this command itself), `auto_prompts` (prompts injected by the tool, e.g. "Briefly inform the user…"), `duplicates` (same message sent twice).

If the JSON has `error`, the project has no transcripts yet; say so and suggest `--all`.

## Rules

- Use the script totals. Never recompute durations by hand.
- Never merge another project's transcripts into this project's report.
- Answer in the user's language.
- This `/prompt-count` turn is itself excluded from the count.
