# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

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

[1.0.0]: https://github.com/johnban-coder/prompt-counter/releases/tag/v1.0.0
