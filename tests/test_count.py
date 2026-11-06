"""Synthetic fixtures for the three supported transcript formats. No real data."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("count", ROOT / "scripts" / "count.py")
count = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["count"] = count
spec.loader.exec_module(count)

T0 = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)


def iso(minutes: float) -> str:
    return (T0 + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def cursor_ts(minutes: float) -> str:
    dt = (T0 + timedelta(minutes=minutes)).astimezone(timezone(timedelta(hours=1)))
    return dt.strftime("%A, %b ") + str(dt.day) + dt.strftime(", %Y, ") + dt.strftime("%I:%M %p").lstrip("0") + " (UTC+1)"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


class ActiveTimeTests(unittest.TestCase):
    def test_short_gap_is_counted(self):
        self.assertEqual(count._credit_gap(10 * 60, 0), 10 * 60)

    def test_idle_gap_is_capped_to_tail(self):
        self.assertEqual(count._credit_gap(8 * 3600, 0), count.TAIL_S)

    def test_busy_agent_gap_is_capped_to_work_cap(self):
        self.assertEqual(count._credit_gap(8 * 3600, 12), count.AI_WORK_CAP_S)

    def test_format_duration(self):
        self.assertEqual(count.format_duration(30), "< 1 min")
        self.assertEqual(count.format_duration(125 * 60), "2 h 05 min")
        self.assertEqual(count.format_duration(None), "—")


class CursorFormatTests(unittest.TestCase):
    def test_parses_user_query_and_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.jsonl"

            def user(text: str, minutes: float) -> dict:
                return {
                    "role": "user",
                    "message": {"content": [{"type": "text", "text": f"<timestamp>{cursor_ts(minutes)}</timestamp>\n<user_query>\n{text}\n</user_query>"}]},
                }

            assistant = {"role": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read"}] * 6}}
            write_jsonl(path, [
                user("Add a dark mode toggle to the settings page", 0),
                assistant,
                user("Add a dark mode toggle to the settings page", 1),  # duplicate
                user("Briefly inform the user about the task result", 2),  # auto
                user("/prompt-count", 3),  # skill call
                user("Now write the unit tests", 70),  # 67 min gap after busy agent
            ])
            rows = count.parse_cursor(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(sum(r.unique for r in rows), 2)
            self.assertTrue(rows[1].duplicate)
            self.assertTrue(rows[2].auto)
            self.assertTrue(rows[3].skill_call)
            self.assertEqual(rows[0].tools_after, 6)
            self.assertTrue(rows[0].dt is not None and rows[0].dt.hour in (9, 10))


class ClaudeFormatTests(unittest.TestCase):
    def test_parses_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            write_jsonl(path, [
                {"type": "user", "timestamp": iso(0), "message": {"role": "user", "content": "Refactor the payment service"}},
                {"type": "assistant", "timestamp": iso(1), "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Edit"}]}},
                {"type": "user", "timestamp": iso(2), "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}},
                {"type": "user", "timestamp": iso(3), "isMeta": True, "message": {"role": "user", "content": "<command-name>/clear</command-name>"}},
                {"type": "user", "timestamp": iso(4), "isSidechain": True, "message": {"role": "user", "content": "sub-agent task"}},
                {"type": "user", "timestamp": iso(5), "message": {"role": "user", "content": [{"type": "text", "text": "Add retries on timeout"}]}},
            ])
            rows = count.parse_claude(path)
            self.assertEqual([r.query for r in rows], ["Refactor the payment service", "Add retries on timeout"])
            self.assertEqual(rows[0].tools_after, 1)
            conv = count.Conversation("claude", "s", path, rows, T0 + timedelta(minutes=6))
            summary = count.summarize(conv)
            self.assertEqual(summary["unique_prompts"], 2)
            self.assertEqual(summary["duration_seconds"], 6 * 60)

    def test_slug(self):
        slug = count.claude_slug(Path("/home/alice/acme-shop"))
        self.assertEqual(slug, "-home-alice-acme-shop") if os.name != "nt" else self.assertTrue(slug.endswith("-home-alice-acme-shop"))


class CodexFormatTests(unittest.TestCase):
    def test_parses_rollout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout-2026.jsonl"
            write_jsonl(path, [
                {"timestamp": iso(0), "type": "session_meta", "payload": {"cwd": "/home/alice/acme-shop"}},
                {"timestamp": iso(0), "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "<environment_context>...</environment_context>"}]}},
                {"timestamp": iso(0), "type": "event_msg", "payload": {"type": "user_message", "message": "Fix the flaky checkout test"}},
                {"timestamp": iso(1), "type": "response_item", "payload": {"type": "function_call", "name": "shell", "arguments": "{}"}},
                {"timestamp": iso(9), "type": "event_msg", "payload": {"type": "user_message", "message": "Great, now open a PR"}},
            ])
            self.assertEqual(count._codex_cwd(path), "/home/alice/acme-shop")
            rows = count.parse_codex(path)
            self.assertEqual([r.query for r in rows], ["Fix the flaky checkout test", "Great, now open a PR"])
            self.assertEqual(rows[0].tools_after, 1)


class ReportTests(unittest.TestCase):
    def test_table_and_totals(self):
        rows = [count.Row(dt=T0, query="Build the landing page"), count.Row(dt=T0 + timedelta(minutes=5), query="Make it responsive")]
        conv = count.Conversation("cursor", "c1", Path("x"), rows, T0 + timedelta(minutes=7))
        report = count.build_report([conv], [{"source": "cursor", "path": "x"}])
        self.assertEqual(report["totals"]["unique_prompts"], 2)
        self.assertEqual(report["totals"]["duration"], "7 min")
        table = count.render_table(report)
        self.assertIn("| Build the landing page | cursor |", table)
        self.assertIn("**2 unique prompts**", table)

    def test_missing_workspace_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = count.scan_workspace(Path(tmp), {"cursor"})
            self.assertIn("error", report)


if __name__ == "__main__":
    sys.exit(unittest.main())
