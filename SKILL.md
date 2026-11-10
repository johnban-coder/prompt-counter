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
- `--all` — every project found on this machine (also when the user types `/prompt-count --all`). See "With --all" below.
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

## With `--all`

The script prints a **Summary** first, then one block per project. Always give the user the summary; never stop at the list of projects.

1. Lead with the machine-wide total, in bold: **N unique prompts · total active time (≈ H h) · P projects · C conversations** (`totals.unique_prompts`, `totals.duration`, `totals.duration_hours`, `totals.projects`).
2. Show the per-project table from the Summary (Project | Source | Conversations | Prompts | Active time, Total row). Projects are already sorted by active time, most active first.
3. If several tools are involved, add the one-line breakdown by tool (`totals.by_source`, `totals.duration_by_source`).
4. Only then, the per-project details — keep them short or offer them on request if there are many projects.
5. Finish by repeating the total line (the output is long; the user must see the total without scrolling back).

## Rules

- Use the script totals. Never recompute durations by hand.
- Never merge another project's transcripts into this project's report.
- Answer in the user's language.
- This `/prompt-count` turn is itself excluded from the count.
