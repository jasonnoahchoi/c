#!/usr/bin/env python3
"""
Unified Conversation Export Hook (/c command)

A UserPromptSubmit hook that intercepts /c commands, parses the transcript
JSONL directly, and delivers results to clipboard or file.

Usage:
    /c                  → copy last assistant response to clipboard
    /c 2                → copy 2nd most recent response
    /c -3               → copy last 3 assistant responses
    /c -p 3             → copy last 3 rounds (user + assistant pairs)
    /c --all            → copy full conversation
    /c list [N]         → list recent N responses (default 10)
    /c find "term"      → search responses

Flags:
    -t, --think         → include thinking blocks in output
    -s <filepath>       → save to file instead of clipboard
    -f md|txt|json      → output format (default: txt for clipboard, md for -s)
"""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Round:
    user_text: Optional[str]
    assistant_text: str
    timestamp: str = ""


@dataclass
class Args:
    mode: str = "copy"          # copy | list | find | all
    count: int = 1              # positive = Nth response, negative = last N
    include_prompts: bool = False  # -p flag
    include_thinking: bool = False  # -t flag
    format: Optional[str] = None   # md | txt | json (None = auto)
    save_path: Optional[str] = None  # -s filepath
    search_term: str = ""        # find "term"
    list_count: int = 10         # list N


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(prompt: str) -> Optional[Args]:
    """Parse /c command arguments. Returns None if prompt doesn't match."""
    prompt = prompt.strip()

    # Match /c, /copy, /copy-response (with optional arguments)
    match = re.match(r"^/(c|copy|copy-response)(?:\s+(.*))?$", prompt)
    if not match:
        return None

    args = Args()
    rest = (match.group(2) or "").strip()

    if not rest:
        return args  # /c → copy last response

    if rest in ("--help", "-h", "help"):
        args.mode = "help"
        return args

    # Tokenize respecting quoted strings
    tokens = []
    for m in re.finditer(r'"([^"]*)"|([\S]+)', rest):
        tokens.append(m.group(1) if m.group(1) is not None else m.group(2))

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok == "list":
            args.mode = "list"
            if i + 1 < len(tokens) and tokens[i + 1].isdigit():
                i += 1
                args.list_count = int(tokens[i])
        elif tok == "find":
            args.mode = "find"
            if i + 1 < len(tokens):
                i += 1
                args.search_term = tokens[i]
        elif tok in ("--all", "-a"):
            args.mode = "all"
        elif tok in ("-t", "--think"):
            args.include_thinking = True
        elif tok == "-p":
            args.include_prompts = True
            if i + 1 < len(tokens) and tokens[i + 1].lstrip("-").isdigit():
                i += 1
                args.count = -abs(int(tokens[i]))
        elif tok == "-s":
            if i + 1 < len(tokens):
                i += 1
                args.save_path = tokens[i]
        elif tok == "-f":
            if i + 1 < len(tokens):
                i += 1
                args.format = tokens[i]
        elif re.match(r"^-\d+$", tok):
            # -3 → last 3 responses
            args.count = int(tok)  # negative
        elif tok.isdigit():
            # 2 → 2nd most recent
            args.count = int(tok)
        i += 1

    return args


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

SKIP_TYPES = {"progress", "file-history-snapshot"}

# Patterns that indicate a user message is system-injected noise, not human input
_NOISE_PREFIXES = (
    "Base directory for this skill:",
    "<task-notification>",
    "<command-message>",
    "<system-reminder>",
)


def _is_noise(text: str) -> bool:
    """Check if text is system-injected noise rather than human input."""
    stripped = text.strip()
    return any(stripped.startswith(p) for p in _NOISE_PREFIXES)


def extract_user_text(message: dict) -> Optional[str]:
    """Extract text from a user message. Returns None for tool_result or noise messages."""
    content = message.get("content", "")
    if isinstance(content, str):
        if not content.strip() or _is_noise(content):
            return None
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if block.get("type") == "text":
                text = block.get("text", "")
                if _is_noise(text):
                    return None
                texts.append(text)
            elif block.get("type") == "tool_result":
                return None  # Skip tool result messages
        return "\n".join(texts) if texts else None
    return None


def extract_assistant_text(content, include_thinking: bool = False) -> str:
    """Extract text blocks from assistant message content array."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if block.get("type") == "thinking" and include_thinking:
                thinking = block.get("thinking", "")
                if thinking.strip():
                    parts.append(f"<thinking>\n{thinking}\n</thinking>")
            elif block.get("type") == "text":
                text = block.get("text", "")
                if text.strip():
                    parts.append(text)
        return "\n".join(parts)
    return ""


def parse_transcript(path: str, include_thinking: bool = False) -> List[Round]:
    """Parse a JSONL transcript into a list of Rounds."""
    rounds: List[Round] = []
    current_user_text: Optional[str] = None
    current_assistant_texts: List[str] = []
    current_timestamp = ""
    last_request_id = None

    def flush_round():
        nonlocal current_user_text, current_assistant_texts, current_timestamp
        assistant_combined = "\n".join(current_assistant_texts).strip()
        if assistant_combined:
            rounds.append(Round(
                user_text=current_user_text,
                assistant_text=assistant_combined,
                timestamp=current_timestamp,
            ))
        current_user_text = None
        current_assistant_texts = []
        current_timestamp = ""

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type", "")

            # Skip noise
            if entry_type in SKIP_TYPES:
                continue

            # Skip compaction summaries (originals preserved)
            if entry.get("isCompactSummary"):
                continue

            # Turn boundary markers
            if entry_type == "system":
                subtype = entry.get("subtype", "")
                if subtype in ("turn_duration", "stop_hook_summary"):
                    flush_round()
                    last_request_id = None
                continue

            message = entry.get("message", {})
            role = message.get("role", "")

            if role == "user":
                user_text = extract_user_text(message)
                if user_text is not None:
                    # If we have pending assistant text, flush the round
                    if current_assistant_texts:
                        flush_round()
                    current_user_text = user_text
                    current_timestamp = entry.get("timestamp", "")

            elif role == "assistant":
                request_id = entry.get("requestId", "")
                text = extract_assistant_text(message.get("content", []), include_thinking)
                if text.strip():
                    current_assistant_texts.append(text)
                    if not current_timestamp:
                        current_timestamp = entry.get("timestamp", "")

    # Flush any remaining round
    flush_round()

    return rounds


# ---------------------------------------------------------------------------
# Content selection
# ---------------------------------------------------------------------------

def select_content(rounds: List[Round], args: Args) -> List[Round]:
    """Select rounds based on args."""
    if not rounds:
        return []

    if args.mode == "all":
        return rounds

    if args.mode in ("list", "find"):
        return rounds  # Caller handles display

    if args.include_prompts:
        # -p N → last N rounds (user + assistant pairs)
        n = abs(args.count) if args.count < 0 else args.count
        return rounds[-n:]

    if args.count < 0:
        # -3 → last 3 assistant responses
        n = abs(args.count)
        return rounds[-n:]
    else:
        # Positive number → Nth from end (1 = most recent)
        idx = len(rounds) - args.count
        if 0 <= idx < len(rounds):
            return [rounds[idx]]
        return []


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_txt(rounds: List[Round], include_prompts: bool) -> str:
    """Plain text format."""
    parts = []
    for r in rounds:
        if include_prompts and r.user_text:
            parts.append(r.user_text)
        parts.append(r.assistant_text)
    return "\n\n---\n\n".join(parts)


def format_md(rounds: List[Round], include_prompts: bool, session_id: str = "") -> str:
    """Markdown format."""
    lines = ["# Conversation Export"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    meta = f"**Date**: {now}"
    if session_id:
        meta += f"  |  **Session**: {session_id[:8]}"
    lines.append(meta)
    lines.append("")

    for r in rounds:
        lines.append("---")
        lines.append("")
        if include_prompts and r.user_text:
            lines.append("## User")
            lines.append(r.user_text)
            lines.append("")
        lines.append("## Assistant")
        lines.append(r.assistant_text)
        lines.append("")

    return "\n".join(lines)


def format_json_output(rounds: List[Round], include_prompts: bool) -> str:
    """JSON format."""
    entries = []
    for r in rounds:
        if include_prompts and r.user_text:
            entries.append({
                "role": "user",
                "content": r.user_text,
                "timestamp": r.timestamp,
            })
        entries.append({
            "role": "assistant",
            "content": r.assistant_text,
            "timestamp": r.timestamp,
        })
    return json.dumps(entries, indent=2, ensure_ascii=False)


def format_output(rounds: List[Round], args: Args, session_id: str = "") -> str:
    """Format selected content based on args."""
    fmt = args.format
    if fmt is None:
        fmt = "md" if args.save_path else "txt"

    include_prompts = args.include_prompts or args.mode == "all"

    if fmt == "json":
        return format_json_output(rounds, include_prompts)
    elif fmt == "md":
        return format_md(rounds, include_prompts, session_id)
    else:
        return format_txt(rounds, include_prompts)


# ---------------------------------------------------------------------------
# Clipboard / file output
# ---------------------------------------------------------------------------

def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    if sys.platform == "darwin":
        cmd = ["pbcopy"]
    elif os.path.exists("/usr/bin/xclip"):
        cmd = ["xclip", "-selection", "clipboard"]
    elif os.path.exists("/mnt/c/Windows"):
        cmd = ["clip.exe"]
    else:
        # Try xclip anyway
        cmd = ["xclip", "-selection", "clipboard"]

    try:
        proc = subprocess.run(cmd, input=text.encode("utf-8"),
                              capture_output=True, timeout=5)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def save_to_file(text: str, path: str, fmt: str) -> bool:
    """Save text to file. Auto-appends extension if missing. Returns True on success."""
    try:
        filepath = Path(path).expanduser().resolve()
        # Auto-append extension if the path has no suffix
        if not filepath.suffix:
            ext_map = {"md": ".md", "txt": ".txt", "json": ".json"}
            filepath = filepath.with_suffix(ext_map.get(fmt, ".md"))
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(text, encoding="utf-8")
        return True
    except (OSError, PermissionError):
        return False


# ---------------------------------------------------------------------------
# Display helpers (for list/find modes)
# ---------------------------------------------------------------------------

def generate_preview(text: str, max_len: int = 60) -> str:
    """Generate a preview of text content."""
    for line in text.split("\n"):
        line = line.strip()
        if line:
            if len(line) > max_len:
                return line[:max_len] + "..."
            return line
    return "<empty response>"


def format_time_ago(timestamp: str) -> str:
    """Format a timestamp as relative time."""
    if not timestamp:
        return ""
    try:
        # Handle ISO format with various suffixes
        ts = timestamp.replace("Z", "+00:00")
        if "." in ts:
            # Truncate microseconds for simpler parsing
            base, frac_and_tz = ts.split(".", 1)
            # Find where the timezone starts (+ or - after the decimal)
            tz_match = re.search(r"[+-]\d{2}:\d{2}$", frac_and_tz)
            if tz_match:
                ts = base + tz_match.group(0)
            else:
                ts = base

        dt = datetime.fromisoformat(ts)
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = (now - dt).total_seconds()

        if diff < 0:
            diff = 0
        if diff < 60:
            return f"[{diff:.0f}s ago]"
        elif diff < 3600:
            return f"[{diff/60:.1f}m ago]"
        else:
            return f"[{diff/3600:.1f}h ago]"
    except (ValueError, TypeError):
        return ""


def display_help():
    """Display usage help to stderr."""
    print("""Usage: /c [options]

Copy & export Claude responses from the current session.

  /c                  Copy last response to clipboard
  /c 2                Copy 2nd most recent response
  /c -3               Copy last 3 responses
  /c -p 3             Copy last 3 rounds (prompts + responses)
  /c --all            Copy full conversation
  /c list [N]         List recent N responses (default 10)
  /c find "term"      Search responses
  -t, --think         Include thinking blocks
  -s <path>           Save to file (auto-appends .md/.txt/.json if no extension)
  -f md|txt|json      Output format (default: txt for clipboard, md for file)
  --help              Show this help""", file=sys.stderr)


def display_list(rounds: List[Round], count: int):
    """Display numbered list of recent responses to stderr."""
    total = len(rounds)
    show = min(count, total)
    print(f"Available responses (1-{total}):", file=sys.stderr)

    # Show most recent first, but only `show` entries
    start = max(0, total - show)
    for i in range(total - 1, start - 1, -1):
        r = rounds[i]
        num = total - i  # 1 = most recent
        preview = generate_preview(r.assistant_text)
        time_ago = format_time_ago(r.timestamp)
        print(f"  {num:3d} {time_ago:>12s}: {preview}", file=sys.stderr)


def display_find(rounds: List[Round], term: str):
    """Search and display matching responses to stderr."""
    total = len(rounds)
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    found = 0

    print(f'Searching for "{term}":', file=sys.stderr)
    for i in range(total - 1, -1, -1):
        r = rounds[i]
        if pattern.search(r.assistant_text):
            found += 1
            num = total - i
            preview = generate_preview(r.assistant_text)
            time_ago = format_time_ago(r.timestamp)
            print(f"  {num:3d} {time_ago:>12s}: {preview}", file=sys.stderr)

    if found == 0:
        print(f'No responses found matching "{term}"', file=sys.stderr)
    else:
        print(f"Found {found} matching response(s)", file=sys.stderr)


# ---------------------------------------------------------------------------
# Hook response helpers
# ---------------------------------------------------------------------------

def block_with_reason(reason: str):
    """Block the prompt and show reason to user."""
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def block_with_stderr():
    """Block the prompt, show stderr to user (already printed)."""
    sys.exit(2)


def pass_through():
    """Let the prompt pass through to Claude."""
    sys.exit(0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        pass_through()

    prompt = input_data.get("prompt", "")
    transcript_path = input_data.get("transcript_path", "")
    session_id = input_data.get("session_id", "")

    # Parse command
    args = parse_args(prompt)
    if args is None:
        pass_through()

    # Handle help (no transcript needed)
    if args.mode == "help":
        display_help()
        block_with_stderr()

    # Validate transcript
    if not transcript_path or not os.path.isfile(transcript_path):
        print("No valid transcript path found", file=sys.stderr)
        block_with_stderr()

    # Parse transcript
    rounds = parse_transcript(transcript_path, include_thinking=args.include_thinking)
    if not rounds:
        print("No assistant responses found in transcript", file=sys.stderr)
        block_with_stderr()

    # Handle list mode
    if args.mode == "list":
        display_list(rounds, args.list_count)
        block_with_stderr()

    # Handle find mode
    if args.mode == "find":
        if not args.search_term:
            print("Usage: /c find \"search term\"", file=sys.stderr)
            block_with_stderr()
        display_find(rounds, args.search_term)
        block_with_stderr()

    # Select content
    selected = select_content(rounds, args)
    if not selected:
        total = len(rounds)
        if args.count > 0 and args.count > total:
            print(f"Response #{args.count} not found. Available: 1-{total}", file=sys.stderr)
        else:
            print("No matching content found", file=sys.stderr)
        block_with_stderr()

    # Format output
    output = format_output(selected, args, session_id)

    # Determine effective format
    effective_fmt = args.format if args.format else ("md" if args.save_path else "txt")

    # Deliver
    if args.save_path:
        if save_to_file(output, args.save_path, effective_fmt):
            # Show the actual path (with auto-appended extension)
            display_path = args.save_path
            if not Path(args.save_path).suffix:
                ext_map = {"md": ".md", "txt": ".txt", "json": ".json"}
                display_path += ext_map.get(effective_fmt, ".md")
            block_with_reason(f"✅ Saved to {display_path}")
        else:
            print(f"Failed to save to {args.save_path}", file=sys.stderr)
            block_with_stderr()
    else:
        if copy_to_clipboard(output):
            # Build descriptive message
            if args.mode == "all":
                msg = f"✅ Full conversation copied ({len(selected)} rounds)"
            elif args.count < 0:
                msg = f"✅ Last {abs(args.count)} responses copied"
            elif args.count == 1:
                msg = "✅ Latest response copied!"
            else:
                msg = f"✅ Response #{args.count} copied"

            if args.include_prompts:
                msg += " (with prompts)"

            block_with_reason(msg)
        else:
            print("Failed to copy to clipboard. No clipboard utility found.", file=sys.stderr)
            block_with_stderr()


if __name__ == "__main__":
    main()
