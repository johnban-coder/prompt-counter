# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [1.2.0] — 2026-11-12

### Added
- `/prompt-count help` — short explanation of the skill, commands and active-time model (`python scripts/count.py help`).
- `/prompt-count update` — checks GitHub `main`, downloads the zip and refreshes every installed `…/skills/prompt-count` folder.
- Optional update notice on count reports when `PROMPT_COUNTER_CHECK_UPDATE=1` (off by default; counting stays offline).
- skills.sh badge and `npx skills add johnban-coder/prompt-counter -g` as the recommended install path.

## [1.1.0] — 2026-11-10

### Added
- `--all` now opens with a **Summary** block: machine-wide total of unique prompts and active time (also in decimal hours), a per-project table sorted by active time, and a breakdown by tool. The total line is repeated at the end of the output.
- `totals.duration_hours` and `totals.duration_by_source` in the JSON report.
- `SKILL.md` section "With --all" so agents always report the grand total instead of only listing projects.

## [1.0.0] — 2026-11-06

First public release.

### Added
- Count unique prompts per conversation and per project, with duplicate / automatic / skill-call exclusion.
- **Active time** model: idle gaps (nights, breaks) are dropped; long agent runs are credited up to 45 min.
- Readers for **Cursor** (`~/.cursor/projects`), **Claude Code** (`~/.claude/projects`) and **OpenAI Codex** (`~/.codex/sessions`).
- `--all` to scan every project on the machine, `--source` to pick tools, `--format table|json`.
- `SKILL.md` following the Agent Skills convention, installable in Cursor, Claude Code, Codex and any `~/.agents/skills` reader.
- One-line installers for PowerShell and POSIX shells.
- Unit tests on synthetic fixtures for the three formats; CI on Linux and Windows.

[1.2.0]: https://github.com/johnban-coder/prompt-counter/releases/tag/v1.2.0
[1.1.0]: https://github.com/johnban-coder/prompt-counter/releases/tag/v1.1.0
[1.0.0]: https://github.com/johnban-coder/prompt-counter/releases/tag/v1.0.0
