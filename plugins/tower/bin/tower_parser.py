"""
Tower Parser - Shared JSONL transcript parser and renderer.

Provides structured parsing of Claude Code JSONL transcripts into Message
dataclasses, plus rendering functions for both basic stdout mode (ANSI) and
TUI mode (rich markup).
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
SKIP_TYPES = {"progress", "file-history-snapshot"}
NOISE_PREFIXES = (
    "Base directory for this skill:",
    "<task-notification>",
    "<command-message>",
    "<system-reminder>",
)

# ANSI colors (basic mode)
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
RED = "\033[31m"
MAGENTA = "\033[35m"
YELLOW = "\033[33m"
RESET = "\033[0m"
RULE = f"{DIM}{'─' * 72}{RESET}"


@dataclass
class ToolCall:
    name: str
    input: dict
    summary: str
    full_detail: str
    full_detail_rich: str = ""


@dataclass
class ToolResult:
    is_error: bool
    content: str


@dataclass
class Message:
    type: str  # "user" | "assistant" | "tool_result"
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


def is_noise(text: str) -> bool:
    stripped = text.strip()
    return any(stripped.startswith(p) for p in NOISE_PREFIXES)


# --- Transcript discovery ---

def find_latest_transcript() -> str | None:
    all_jsonl = list(PROJECTS_DIR.rglob("*.jsonl"))
    if not all_jsonl:
        return None
    return str(max(all_jsonl, key=lambda p: p.stat().st_mtime))


def find_transcript_by_id(session_id: str) -> str | None:
    for p in PROJECTS_DIR.rglob("*.jsonl"):
        if session_id in p.stem:
            return str(p)
    return None


def get_sorted_transcripts() -> list[Path]:
    all_jsonl = list(PROJECTS_DIR.rglob("*.jsonl"))
    all_jsonl.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return all_jsonl


def list_sessions(count: int = 10):
    all_jsonl = get_sorted_transcripts()
    for i, p in enumerate(all_jsonl[:count]):
        size_kb = p.stat().st_size // 1024
        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime))
        preview = ""
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if entry.get("type") == "user":
                        content = entry.get("message", {}).get("content", "")
                        if isinstance(content, str) and content.strip():
                            preview = content[:60]
                            break
        except Exception:
            pass
        sid = p.stem[:8]
        print(f"  {i+1:2d}) {sid}...  {mtime}  {size_kb:>4d}KB  {DIM}{preview}{RESET}")


# --- Tool rendering (ANSI basic mode) ---

def render_diff(old: str, new: str, max_lines: int = 15) -> str:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    result = []
    for line in old_lines[:max_lines]:
        result.append(f"  {RED}- {line}{RESET}")
    if len(old_lines) > max_lines:
        result.append(f"  {DIM}  ... ({len(old_lines) - max_lines} more lines){RESET}")
    for line in new_lines[:max_lines]:
        result.append(f"  {GREEN}+ {line}{RESET}")
    if len(new_lines) > max_lines:
        result.append(f"  {DIM}  ... ({len(new_lines) - max_lines} more lines){RESET}")
    return "\n".join(result)


def render_file_preview(content: str, max_lines: int = 10) -> str:
    lines = content.splitlines()
    result = []
    for line in lines[:max_lines]:
        result.append(f"  {DIM}  {line}{RESET}")
    if len(lines) > max_lines:
        result.append(f"  {DIM}  ... ({len(lines) - max_lines} more lines){RESET}")
    return "\n".join(result)


def _tool_summary(name: str, inp: dict) -> str:
    """One-line summary for a tool call (used in both modes)."""
    if name in ("Edit", "MultiEdit"):
        return f"> Edit {inp.get('file_path', '')}"
    elif name == "Write":
        content = inp.get("content", "")
        lc = len(content.splitlines()) if content else 0
        return f"> Write {inp.get('file_path', '')} ({lc} lines)"
    elif name == "Read":
        return f"> Read {inp.get('file_path', '')}"
    elif name == "Bash":
        cmd = inp.get("command", "")
        first_line = cmd.splitlines()[0][:60] if cmd else ""
        return f"> Bash $ {first_line}"
    elif name == "Grep":
        return f"> Grep `{inp.get('pattern', '')}`"
    elif name == "Glob":
        return f"> Glob `{inp.get('pattern', '')}`"
    elif name == "Agent":
        return f"> Agent {inp.get('description', '')}"
    elif name == "Skill":
        return f"> Skill /{inp.get('skill', '')}"
    else:
        return f"> {name}"


def render_tool_use_basic(block: dict) -> str:
    """Render a tool_use block with ANSI colors for basic stdout mode."""
    name = block.get("name", "")
    inp = block.get("input", {})
    lines = []

    if name in ("Edit", "MultiEdit"):
        fp = inp.get("file_path", "")
        lines.append(f"{MAGENTA}> Edit{RESET} {DIM}{fp}{RESET}")
        old = inp.get("old_string", "")
        new = inp.get("new_string", "")
        if old or new:
            lines.append(render_diff(old, new))

    elif name == "Write":
        fp = inp.get("file_path", "")
        content = inp.get("content", "")
        line_count = len(content.splitlines()) if content else 0
        lines.append(f"{MAGENTA}> Write{RESET} {DIM}{fp}{RESET} {DIM}({line_count} lines){RESET}")
        if content:
            lines.append(render_file_preview(content))

    elif name == "Read":
        fp = inp.get("file_path", "")
        offset = inp.get("offset", "")
        limit = inp.get("limit", "")
        range_info = ""
        if offset or limit:
            range_info = f" {DIM}(lines {offset or 1}-{(offset or 0) + (limit or 2000)}){RESET}"
        lines.append(f"{MAGENTA}> Read{RESET} {DIM}{fp}{RESET}{range_info}")

    elif name == "Bash":
        cmd = inp.get("command", "")
        lines.append(f"{MAGENTA}> Bash{RESET}")
        if cmd:
            for cmd_line in cmd.splitlines()[:5]:
                lines.append(f"  {DIM}$ {cmd_line}{RESET}")
            if len(cmd.splitlines()) > 5:
                lines.append(f"  {DIM}  ... ({len(cmd.splitlines()) - 5} more lines){RESET}")

    elif name == "Grep":
        pattern = inp.get("pattern", "")
        path = inp.get("path", "")
        glob_filter = inp.get("glob", "")
        detail = f" {DIM}in {path}{RESET}" if path else ""
        detail += f" {DIM}({glob_filter}){RESET}" if glob_filter else ""
        lines.append(f"{MAGENTA}> Grep{RESET} {DIM}`{pattern}`{RESET}{detail}")

    elif name == "Glob":
        pattern = inp.get("pattern", "")
        path = inp.get("path", "")
        detail = f" {DIM}in {path}{RESET}" if path else ""
        lines.append(f"{MAGENTA}> Glob{RESET} {DIM}`{pattern}`{RESET}{detail}")

    elif name == "Agent":
        desc = inp.get("description", "")
        agent_type = inp.get("subagent_type", "")
        bg = " (background)" if inp.get("run_in_background") else ""
        type_info = f" [{agent_type}]" if agent_type else ""
        lines.append(f"{MAGENTA}> Agent{RESET}{type_info} {desc}{bg}")

    elif name == "Skill":
        skill = inp.get("skill", "")
        args = inp.get("args", "")
        lines.append(f"{MAGENTA}> Skill{RESET} /{skill}" + (f" {DIM}{args}{RESET}" if args else ""))

    else:
        lines.append(f"{MAGENTA}> {name}{RESET}")
        for k, v in list(inp.items())[:3]:
            v_str = str(v)[:80]
            lines.append(f"  {DIM}{k}: {v_str}{RESET}")

    return "\n".join(lines)


# --- Tool rendering (rich markup for TUI mode) ---

def _escape_rich(text: str) -> str:
    """Escape brackets so rich/textual doesn't interpret them as markup tags."""
    return text.replace("[", "\\[")


def format_tool_detail_rich(name: str, inp: dict) -> str:
    """Render tool detail with rich markup for textual TUI."""
    lines = []

    if name in ("Edit", "MultiEdit"):
        old = _escape_rich(inp.get("old_string", ""))
        new = _escape_rich(inp.get("new_string", ""))
        for line in old.splitlines()[:15]:
            lines.append(f"[red]- {line}[/red]")
        if len(old.splitlines()) > 15:
            lines.append(f"[dim]  ... ({len(old.splitlines()) - 15} more)[/dim]")
        for line in new.splitlines()[:15]:
            lines.append(f"[green]+ {line}[/green]")
        if len(new.splitlines()) > 15:
            lines.append(f"[dim]  ... ({len(new.splitlines()) - 15} more)[/dim]")

    elif name == "Write":
        content = _escape_rich(inp.get("content", ""))
        for line in content.splitlines()[:15]:
            lines.append(f"[dim]  {line}[/dim]")
        if len(content.splitlines()) > 15:
            lines.append(f"[dim]  ... ({len(content.splitlines()) - 15} more)[/dim]")

    elif name == "Bash":
        cmd = _escape_rich(inp.get("command", ""))
        for line in cmd.splitlines()[:10]:
            lines.append(f"[dim]$ {line}[/dim]")
        if len(cmd.splitlines()) > 10:
            lines.append(f"[dim]  ... ({len(cmd.splitlines()) - 10} more)[/dim]")

    elif name == "Read":
        fp = _escape_rich(inp.get("file_path", ""))
        offset = inp.get("offset", "")
        limit = inp.get("limit", "")
        if offset or limit:
            lines.append(f"[dim]lines {offset or 1}-{(offset or 0) + (limit or 2000)}[/dim]")

    else:
        for k, v in list(inp.items())[:5]:
            v_str = _escape_rich(str(v)[:120])
            lines.append(f"[dim]{k}: {v_str}[/dim]")

    return "\n".join(lines)


# --- Structured parsing ---

def parse_entry(entry: dict) -> Message | None:
    """Parse a JSONL entry into a structured Message, or None if noise/skip."""
    entry_type = entry.get("type", "")

    if entry_type in SKIP_TYPES:
        return None
    if entry.get("isCompactSummary"):
        return None

    message = entry.get("message", {})
    role = message.get("role", "")
    content = message.get("content", "")

    if entry_type == "user" or role == "user":
        if isinstance(content, str):
            if not content.strip() or is_noise(content):
                return None
            return Message(type="user", text=content, raw=entry)
        elif isinstance(content, list):
            user_texts = []
            tool_results = []
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if is_noise(text):
                        return None
                    if text.strip():
                        user_texts.append(text)
                elif block.get("type") == "tool_result":
                    is_err = block.get("is_error", False)
                    tc = block.get("content", "")
                    if isinstance(tc, list):
                        tc = " ".join(b.get("text", "") for b in tc if b.get("type") == "text")
                    elif isinstance(tc, str):
                        pass
                    tool_results.append(ToolResult(is_error=is_err, content=tc))
            if user_texts:
                return Message(type="user", text="\n".join(user_texts), raw=entry)
            if tool_results:
                return Message(type="tool_result", tool_results=tool_results, raw=entry)
        return None

    elif entry_type == "assistant" or role == "assistant":
        text_parts = []
        tool_calls = []
        if isinstance(content, str):
            if content.strip():
                text_parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text.strip():
                        text_parts.append(text)
                elif block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = block.get("input", {})
                    tool_calls.append(ToolCall(
                        name=name,
                        input=inp,
                        summary=_tool_summary(name, inp),
                        full_detail=render_tool_use_basic(block),
                        full_detail_rich=format_tool_detail_rich(name, inp),
                    ))
        if text_parts or tool_calls:
            return Message(
                type="assistant",
                text="\n".join(text_parts),
                tool_calls=tool_calls,
                raw=entry,
            )
        return None

    return None


# --- Basic mode rendering ---

def render_entry_basic(entry: dict) -> str | None:
    """Render a JSONL entry as ANSI-colored text for stdout mode."""
    msg = parse_entry(entry)
    if msg is None:
        return None

    if msg.type == "user":
        return f"\n{RULE}\n{BOLD}{CYAN}## User{RESET}\n\n{msg.text}\n"

    elif msg.type == "tool_result":
        parts = []
        for tr in msg.tool_results:
            label = f"{YELLOW}ERROR{RESET}" if tr.is_error else f"{DIM}ok{RESET}"
            parts.append(f"{DIM}  ({label})\n  {tr.content}{RESET}")
        return f"\n{DIM}## Tools{RESET}\n" + "\n".join(parts) + "\n"

    elif msg.type == "assistant":
        parts = []
        if msg.text:
            parts.append(msg.text)
        for tc in msg.tool_calls:
            parts.append(tc.full_detail)
        if parts:
            return f"\n{BOLD}{GREEN}## Assistant{RESET}\n" + "\n".join(parts) + "\n"

    return None
