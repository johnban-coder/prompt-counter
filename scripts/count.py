#!/usr/bin/env python3
"""Prompt Counter — count your unique prompts and active time per AI conversation.

Reads the local transcripts written by Cursor, Claude Code and OpenAI Codex,
and reports, per conversation and per workspace:

* unique user prompts (deduplicated, minus automatic/system prompts),
* active interaction time (idle gaps such as nights or lunch breaks are dropped).

Standard library only. Nothing leaves your machine. Output is JSON by default
so an AI agent can read it, or a Markdown table with ``--format table``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

__version__ = "1.1.0"

# --- Active time model --------------------------------------------------------
# A gap longer than IDLE_GAP_S between two of your prompts is idle time, unless
# the agent was busy (>= TOOL_BUSY tool calls) — long builds, OCR, test runs.
IDLE_GAP_S = 15 * 60
AI_WORK_CAP_S = 45 * 60
TAIL_S = 5 * 60
TOOL_BUSY = 5

# Prompts that the tool itself injects (not your work).
AUTO_MARKERS = (
    "briefly inform the user about the task result",
)

# The skill's own slash command and aliases are not project work.
SKILL_START = re.compile(
    r"^(?:"
    r"/(?:prompt-count|counter-prompt|prompt-counter)\b"
    r"|combien de prompts?\b"
    r"|nombre de prompts?\b"
    r"|prompt[\s-]?count(?:er)?\b"
    r"|how many prompts?\b"
    r")",
    re.I,
)

# Cursor wraps the real prompt in <user_query> and adds a <timestamp> tag.
QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S)
TS_RE = re.compile(r"<timestamp>(.*?)</timestamp>")
TS_PARSE = re.compile(
    r"^[A-Za-z]+,\s+(\w{3})\s+(\d{1,2}),\s+(\d{4}),\s+"
    r"(\d{1,2}):(\d{2})\s+(AM|PM)\s+\(UTC([+-]\d{1,2})\)$"
)
MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

SOURCES = ("cursor", "claude", "codex")


# --- Small helpers ------------------------------------------------------------
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _is_auto(query: str) -> bool:
    n = _norm(query)
    return any(marker in n for marker in AUTO_MARKERS)


def _is_skill_call(query: str) -> bool:
    return bool(SKILL_START.match(_norm(query)))


def _excerpt(query: str, limit: int = 72) -> str:
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in query.strip().splitlines()]
    lines = [ln for ln in lines if ln]
    line = next((ln for ln in lines if len(ln) >= 12), lines[0] if lines else "")
    return line[:limit] + ("…" if len(line) > limit else "")


def parse_cursor_ts(raw: str) -> datetime | None:
    """'Friday, Nov 6, 2026, 3:58 PM (UTC+1)' -> aware datetime."""
    if not raw:
        return None
    match = TS_PARSE.match(raw.strip())
    if not match:
        return None
    mon, day, year, hour, minute, ampm, offset = match.groups()
    month = MONTHS.get(mon)
    if month is None:
        return None
    hour_i = int(hour) % 12
    if ampm.upper() == "PM":
        hour_i += 12
    tz = timezone(timedelta(hours=int(offset)))
    return datetime(int(year), month, int(day), hour_i, int(minute), tzinfo=tz)


def parse_iso_ts(raw: str | None) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    total_min = int(round(seconds / 60.0))
    if total_min < 1:
        return "< 1 min"
    if total_min < 60:
        return f"{total_min} min"
    days, rem = divmod(total_min, 1440)
    hours, minutes = divmod(rem, 60)
    if days:
        return f"{days} d {hours} h" if hours else f"{days} d"
    if minutes:
        return f"{hours} h {minutes:02d} min"
    return f"{hours} h"


def format_dt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def _iter_jsonl(path: Path) -> Iterable[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


def _content_text(content, text_types=("text", "input_text")) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in text_types:
                parts.append(item.get("text") or "")
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def _content_tool_calls(content) -> int:
    if not isinstance(content, list):
        return 0
    return sum(
        1
        for item in content
        if isinstance(item, dict)
        and (item.get("type") in ("tool_use", "tool_call", "function_call") or item.get("name"))
    )


def _credit_gap(gap_s: float, tools: int) -> float:
    """Credit only active interaction; overnight / idle PC is dropped."""
    if gap_s <= 0:
        return 0.0
    if gap_s <= IDLE_GAP_S:
        return gap_s
    if tools >= TOOL_BUSY:
        return min(gap_s, float(AI_WORK_CAP_S))
    return min(gap_s, float(TAIL_S))


# --- Rows ---------------------------------------------------------------------
@dataclass
class Row:
    dt: datetime | None
    query: str
    auto: bool = False
    skill_call: bool = False
    duplicate: bool = False
    tools_after: int = 0

    @property
    def unique(self) -> bool:
        return not (self.auto or self.skill_call or self.duplicate)


@dataclass
class Conversation:
    source: str
    id: str
    path: Path
    rows: list[Row] = field(default_factory=list)
    end: datetime | None = None


class RowBuilder:
    """Accumulates prompts + the tool calls the agent made between them."""

    def __init__(self) -> None:
        self.rows: list[Row] = []
        self._prev_norm = ""
        self._pending_tools = 0

    def tools(self, n: int) -> None:
        self._pending_tools += max(0, n)

    def prompt(self, query: str, dt: datetime | None) -> None:
        query = (query or "").strip()
        if not query:
            return
        if self.rows:
            self.rows[-1].tools_after = self._pending_tools
        self._pending_tools = 0
        n = _norm(query)
        dup = bool(n) and n == self._prev_norm
        if n:
            self._prev_norm = n
        self.rows.append(
            Row(
                dt=dt,
                query=query,
                auto=_is_auto(query),
                skill_call=_is_skill_call(query),
                duplicate=dup,
            )
        )

    def finish(self) -> list[Row]:
        if self.rows:
            self.rows[-1].tools_after = self._pending_tools
        return self.rows


def active_seconds(rows: list[Row], end: datetime | None) -> float | None:
    timed = [r for r in rows if r.dt is not None]
    if not timed:
        return None
    total = 0.0
    for i, row in enumerate(timed[:-1]):
        gap = (timed[i + 1].dt - row.dt).total_seconds()  # type: ignore[operator]
        total += _credit_gap(gap, row.tools_after)
    last = timed[-1]
    if end is not None:
        tail = (end.astimezone(timezone.utc) - last.dt.astimezone(timezone.utc)).total_seconds()  # type: ignore[union-attr]
        total += _credit_gap(tail, last.tools_after)
    return max(0.0, total)


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


# --- Source: Cursor -----------------------------------------------------------
# ~/.cursor/projects/<slug>/agent-transcripts/<chat-id>/<chat-id>.jsonl
def cursor_root() -> Path:
    return Path.home() / ".cursor" / "projects"


def cursor_slug(workspace: Path) -> str:
    raw = str(workspace.resolve()).replace(":", "")
    return raw.replace("\\", "-").replace("/", "-")


def cursor_project_dir(workspace: Path) -> Path | None:
    root = cursor_root()
    if not root.is_dir():
        return None
    want = cursor_slug(workspace).casefold()
    for child in root.iterdir():
        if child.is_dir() and child.name.casefold() == want and (child / "agent-transcripts").is_dir():
            return child
    name = workspace.resolve().name.casefold()
    hits = [
        c for c in root.iterdir()
        if c.is_dir() and (c / "agent-transcripts").is_dir() and c.name.casefold().endswith("-" + name)
    ]
    return hits[0] if len(hits) == 1 else None


def _cursor_parent_jsonl(chat_dir: Path) -> Path | None:
    parent = chat_dir / f"{chat_dir.name}.jsonl"
    if parent.is_file():
        return parent
    jsonls = [p for p in chat_dir.glob("*.jsonl") if "subagents" not in p.parts]
    return jsonls[0] if len(jsonls) == 1 else None


def parse_cursor(path: Path) -> list[Row]:
    rb = RowBuilder()
    for obj in _iter_jsonl(path):
        role = obj.get("role")
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else obj
        if role == "assistant":
            rb.tools(_content_tool_calls(msg.get("content")) or 1)
            continue
        if role != "user":
            continue
        text = _content_text(msg.get("content"))
        match = QUERY_RE.search(text)
        if not match:
            continue
        ts = TS_RE.search(text)
        rb.prompt(match.group(1), parse_cursor_ts(ts.group(1) if ts else ""))
    return rb.finish()


def cursor_conversations(project_dir: Path) -> list[Conversation]:
    out: list[Conversation] = []
    transcripts = project_dir / "agent-transcripts"
    if not transcripts.is_dir():
        return out
    for child in sorted(transcripts.iterdir()):
        if not child.is_dir() or child.name == "subagents":
            continue
        path = _cursor_parent_jsonl(child)
        if path is None:
            continue
        out.append(Conversation("cursor", child.name, path, parse_cursor(path), _mtime(path)))
    return out


def cursor_all() -> list[tuple[str, list[Conversation]]]:
    root = cursor_root()
    if not root.is_dir():
        return []
    return [
        (child.name, cursor_conversations(child))
        for child in sorted(root.iterdir())
        if (child / "agent-transcripts").is_dir()
    ]


# --- Source: Claude Code ------------------------------------------------------
# ~/.claude/projects/<slug>/<session-id>.jsonl   (slug = cwd with [^A-Za-z0-9] -> '-')
def claude_root() -> Path:
    return Path.home() / ".claude" / "projects"


def claude_slug(workspace: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(workspace.resolve()))


def claude_project_dirs(workspace: Path) -> list[Path]:
    root = claude_root()
    if not root.is_dir():
        return []
    want = claude_slug(workspace).casefold()
    return [c for c in root.iterdir() if c.is_dir() and c.name.casefold() == want]


def parse_claude(path: Path) -> list[Row]:
    rb = RowBuilder()
    for obj in _iter_jsonl(path):
        kind = obj.get("type")
        if obj.get("isSidechain"):
            continue  # sub-agent traffic
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        if kind == "assistant":
            rb.tools(_content_tool_calls(msg.get("content")) or 1)
            continue
        if kind != "user" or obj.get("isMeta"):
            continue
        content = msg.get("content")
        if isinstance(content, list) and any(
            isinstance(i, dict) and i.get("type") == "tool_result" for i in content
        ):
            continue  # tool results come back under role=user
        text = _content_text(content).strip()
        if not text or text.startswith(("<command-", "<local-command", "<system-reminder")):
            continue  # slash-command plumbing
        rb.prompt(text, parse_iso_ts(obj.get("timestamp")))
    return rb.finish()


def claude_conversations(project_dir: Path) -> list[Conversation]:
    out: list[Conversation] = []
    for path in sorted(project_dir.glob("*.jsonl")):
        out.append(Conversation("claude", path.stem, path, parse_claude(path), _mtime(path)))
    return out


def claude_all() -> list[tuple[str, list[Conversation]]]:
    root = claude_root()
    if not root.is_dir():
        return []
    return [(c.name, claude_conversations(c)) for c in sorted(root.iterdir()) if c.is_dir()]


# --- Source: OpenAI Codex -----------------------------------------------------
# ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl  (first line: session_meta with cwd)
def codex_root() -> Path:
    return Path.home() / ".codex" / "sessions"


def _codex_cwd(path: Path) -> str | None:
    for obj in _iter_jsonl(path):
        if obj.get("type") == "session_meta":
            payload = obj.get("payload") or {}
            return payload.get("cwd")
        break
    return None


def parse_codex(path: Path) -> list[Row]:
    rb = RowBuilder()
    saw_event_prompts = False
    for obj in _iter_jsonl(path):
        kind = obj.get("type")
        payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
        ptype = payload.get("type")
        dt = parse_iso_ts(obj.get("timestamp"))
        if kind == "event_msg" and ptype == "user_message":
            saw_event_prompts = True
            rb.prompt(str(payload.get("message") or ""), dt)
        elif kind == "response_item":
            if ptype in ("function_call", "custom_tool_call", "local_shell_call", "web_search_call"):
                rb.tools(1)
            elif ptype == "message" and payload.get("role") == "user" and not saw_event_prompts:
                text = _content_text(payload.get("content")).strip()
                if text and not text.startswith("<"):  # skip injected <environment_context> etc.
                    rb.prompt(text, dt)
    return rb.finish()


def codex_all_files() -> list[Path]:
    root = codex_root()
    if not root.is_dir():
        return []
    return sorted(root.rglob("rollout-*.jsonl"))


def _same_path(a: str | None, b: Path) -> bool:
    if not a:
        return False
    try:
        return Path(a).resolve().as_posix().casefold() == b.resolve().as_posix().casefold()
    except OSError:
        return False


def codex_conversations(workspace: Path | None) -> list[Conversation]:
    out: list[Conversation] = []
    for path in codex_all_files():
        cwd = _codex_cwd(path)
        if workspace is not None and not _same_path(cwd, workspace):
            continue
        out.append(Conversation("codex", path.stem, path, parse_codex(path), _mtime(path)))
    return out


def codex_all() -> list[tuple[str, list[Conversation]]]:
    groups: dict[str, list[Conversation]] = {}
    for path in codex_all_files():
        cwd = _codex_cwd(path) or "(unknown cwd)"
        groups.setdefault(cwd, []).append(
            Conversation("codex", path.stem, path, parse_codex(path), _mtime(path))
        )
    return sorted(groups.items())


# --- Reporting ----------------------------------------------------------------
def summarize(conv: Conversation) -> dict | None:
    unique = [r for r in conv.rows if r.unique]
    if not unique:
        return None
    duration_s = active_seconds(conv.rows, conv.end)
    return {
        "source": conv.source,
        "id": conv.id,
        "title": _excerpt(unique[0].query) or conv.id,
        "first": format_dt(unique[0].dt),
        "last_prompt": format_dt(unique[-1].dt),
        "last_ai": format_dt(conv.end),
        "duration_seconds": duration_s,
        "duration": format_duration(duration_s),
        "unique_prompts": len(unique),
        "skill_calls": sum(1 for r in conv.rows if r.skill_call and not r.duplicate),
        "auto_prompts": sum(1 for r in conv.rows if r.auto),
        "duplicates": sum(1 for r in conv.rows if r.duplicate and not r.auto and not r.skill_call),
        "raw_prompts": len(conv.rows),
    }


def _totals(chats: list[dict]) -> dict:
    vals = [c["duration_seconds"] for c in chats if c.get("duration_seconds") is not None]
    total_dur = float(sum(vals)) if vals else None
    return {
        "unique_prompts": sum(c["unique_prompts"] for c in chats),
        "skill_calls": sum(c["skill_calls"] for c in chats),
        "auto_prompts": sum(c["auto_prompts"] for c in chats),
        "duplicates": sum(c["duplicates"] for c in chats),
        "raw_prompts": sum(c["raw_prompts"] for c in chats),
        "conversations": len(chats),
        "by_source": {
            s: sum(c["unique_prompts"] for c in chats if c["source"] == s)
            for s in SOURCES
            if any(c["source"] == s for c in chats)
        },
        "duration_seconds": total_dur,
        "duration": format_duration(total_dur),
        "duration_hours": round(total_dur / 3600.0, 2) if total_dur is not None else None,
    }


def build_report(convs: list[Conversation], sources_scanned: list[dict]) -> dict:
    chats = [s for s in (summarize(c) for c in convs) if s]
    chats.sort(key=lambda c: c.get("first") or "")
    return {
        "version": __version__,
        "duration_mode": "active",
        "idle_gap_minutes": IDLE_GAP_S // 60,
        "ai_work_cap_minutes": AI_WORK_CAP_S // 60,
        "sources": sources_scanned,
        "conversations": chats,
        "totals": _totals(chats),
    }


def scan_workspace(workspace: Path, wanted: set[str]) -> dict:
    convs: list[Conversation] = []
    scanned: list[dict] = []
    if "cursor" in wanted:
        pdir = cursor_project_dir(workspace)
        scanned.append({"source": "cursor", "path": str(pdir) if pdir else None})
        if pdir:
            convs += cursor_conversations(pdir)
    if "claude" in wanted:
        dirs = claude_project_dirs(workspace)
        scanned.append({"source": "claude", "path": str(dirs[0]) if dirs else None})
        for d in dirs:
            convs += claude_conversations(d)
    if "codex" in wanted:
        root = codex_root()
        scanned.append({"source": "codex", "path": str(root) if root.is_dir() else None})
        if root.is_dir():
            convs += codex_conversations(workspace)
    report = build_report(convs, scanned)
    report["workspace"] = str(workspace)
    if not report["conversations"]:
        report["error"] = "no transcripts found for this workspace"
        report["hint"] = (
            "Open this project in Cursor, Claude Code or Codex and send at least one prompt. "
            "Use --all to list every project that has transcripts."
        )
    return report


def scan_all(wanted: set[str]) -> dict:
    projects: list[dict] = []
    groups: list[tuple[str, str, list[Conversation]]] = []
    if "cursor" in wanted:
        groups += [("cursor", name, convs) for name, convs in cursor_all()]
    if "claude" in wanted:
        groups += [("claude", name, convs) for name, convs in claude_all()]
    if "codex" in wanted:
        groups += [("codex", name, convs) for name, convs in codex_all()]
    for source, name, convs in groups:
        report = build_report(convs, [{"source": source, "path": name}])
        if report["totals"]["raw_prompts"]:
            report["workspace"] = name
            report["source"] = source
            projects.append(report)
    return build_all_report(projects)


def build_all_report(projects: list[dict]) -> dict:
    """Wrap per-project reports with machine-wide totals (most active project first)."""
    projects = sorted(
        projects,
        key=lambda p: (p["totals"]["duration_seconds"] or 0.0, p["totals"]["unique_prompts"]),
        reverse=True,
    )
    all_chats = [c for p in projects for c in p["conversations"]]
    totals = _totals(all_chats)
    totals["projects"] = len(projects)
    totals["duration_by_source"] = {
        s: format_duration(sum(c["duration_seconds"] or 0.0 for c in all_chats if c["source"] == s))
        for s in SOURCES
        if any(c["source"] == s for c in all_chats)
    }
    return {"version": __version__, "mode": "all", "projects": projects, "totals": totals}


def _hours(t: dict) -> str:
    h = t.get("duration_hours")
    return f" (≈ {h:.1f} h)" if h is not None and h >= 1 else ""


def render_table(report: dict) -> str:
    def block(rep: dict, heading: str | None) -> list[str]:
        lines: list[str] = []
        if heading:
            lines.append(f"### {heading}")
            lines.append("")
        chats = rep.get("conversations") or []
        t = rep.get("totals") or {}
        lines.append(
            f"**{t.get('unique_prompts', 0)} unique prompts** · "
            f"**{t.get('duration', '—')} active** · {t.get('conversations', 0)} conversation(s)"
        )
        lines.append("")
        lines.append("| Conversation | Source | Period | Prompts | Active time |")
        lines.append("|---|---|---|---:|---:|")
        for c in chats:
            period = f"{c['first']} → {c['last_ai']}" if c.get("first") else ""
            lines.append(
                f"| {c['title']} | {c['source']} | {period} | {c['unique_prompts']} | {c['duration']} |"
            )
        lines.append(
            f"| **Total** | | | **{t.get('unique_prompts', 0)}** | **{t.get('duration', '—')}** |"
        )
        lines.append("")
        lines.append(
            f"_excluded: {t.get('skill_calls', 0)} skill call(s), "
            f"{t.get('auto_prompts', 0)} automatic prompt(s), {t.get('duplicates', 0)} duplicate(s)_"
        )
        lines.append("")
        return lines

    out: list[str] = []
    if report.get("mode") == "all":
        t = report["totals"]
        headline = (
            f"**{t['unique_prompts']} unique prompts** · **{t['duration']} active{_hours(t)}** · "
            f"{t['projects']} project(s) · {t['conversations']} conversation(s)"
        )
        out.append("## Summary — all projects")
        out.append("")
        out.append(headline)
        out.append("")
        out.append("| Project | Source | Conversations | Prompts | Active time |")
        out.append("|---|---|---:|---:|---:|")
        for p in report["projects"]:
            pt = p["totals"]
            out.append(
                f"| {p['workspace']} | {p['source']} | {pt['conversations']} | "
                f"{pt['unique_prompts']} | {pt['duration']} |"
            )
        out.append(
            f"| **Total** | | **{t['conversations']}** | **{t['unique_prompts']}** | **{t['duration']}** |"
        )
        by_src = t.get("by_source") or {}
        if len(by_src) > 1:
            out.append("")
            out.append(
                "_by tool: "
                + ", ".join(
                    f"{s} {n} prompts / {t.get('duration_by_source', {}).get(s, '—')}" for s, n in by_src.items()
                )
                + "_"
            )
        out.append("")
        out.append(
            f"_excluded: {t.get('skill_calls', 0)} skill call(s), "
            f"{t.get('auto_prompts', 0)} automatic prompt(s), {t.get('duplicates', 0)} duplicate(s)_"
        )
        out.append("")
        out.append("## Details per project")
        out.append("")
        for p in report["projects"]:
            out += block(p, f"{p['workspace']} ({p['source']})")
        out.append(
            f"**Total, all projects: {t['unique_prompts']} unique prompts · "
            f"{t['duration']} active{_hours(t)} · {t['projects']} project(s)**"
        )
    else:
        if report.get("error"):
            out.append(f"_{report['error']}_ — {report.get('hint', '')}")
        else:
            out += block(report, None)
    return "\n".join(out).rstrip() + "\n"


# --- CLI ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prompt-counter",
        description="Count unique prompts and active time per AI conversation (Cursor, Claude Code, Codex).",
    )
    parser.add_argument("--workspace", default=".", help="Project root (default: cwd). Ignored with --all.")
    parser.add_argument("--all", action="store_true", help="Scan every project that has transcripts.")
    parser.add_argument(
        "--source",
        default="auto",
        help="Comma list of sources to read: cursor,claude,codex (default: auto = all three).",
    )
    parser.add_argument("--format", choices=("json", "table"), default="json", help="Output format.")
    parser.add_argument("--version", action="version", version=f"prompt-counter {__version__}")
    args = parser.parse_args(argv)

    wanted = set(SOURCES) if args.source == "auto" else {s.strip() for s in args.source.split(",")}
    unknown = wanted - set(SOURCES)
    if unknown:
        parser.error(f"unknown source(s): {', '.join(sorted(unknown))}")

    report = scan_all(wanted) if args.all else scan_workspace(Path(args.workspace).resolve(), wanted)

    if args.format == "table":
        sys.stdout.write(render_table(report))
    else:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return 2 if report.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
