# Contributing

Thanks for helping. Prompt Counter is intentionally small: one stdlib-only Python script, one `SKILL.md`, two installers.

## Ground rules

- **Privacy first.** Never commit a real transcript, a real report or anything that came out of `~/.cursor`, `~/.claude` or `~/.codex`. Tests use synthetic fixtures built in `tests/test_count.py`.
- **Standard library only.** No dependencies, so the skill runs anywhere Python 3.10+ runs.
- **Keep it one file.** New transcript formats go in `scripts/count.py` as a new `parse_<tool>()` + `<tool>_conversations()` pair.

## Development

```bash
python -m unittest discover -s tests -v
python scripts/count.py --all --format table
```

## Adding a new tool

1. Find where the tool stores its transcripts and how it marks user messages, assistant tool calls and timestamps.
2. Add a parser that feeds a `RowBuilder` (`prompt(text, dt)` for each user prompt, `tools(n)` for agent tool calls).
3. Add the source to `SOURCES`, `scan_workspace()` and `scan_all()`.
4. Add a synthetic fixture test.
5. Document the location in `README.md` → *Where the data comes from*.

## Pull requests

Small, focused PRs with a short description of what changed and why. CI must be green on the three OSes.
