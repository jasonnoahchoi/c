# /c

A Claude Code plugin for copying and exporting conversation responses. Zero tokens, instant results.

## Install

```bash
claude plugin install --plugin-dir /path/to/c
```

Or add to your marketplace and install from there.

## Reference

| Usage | Description |
|-------|-------------|
| `/c` | Copy last response to clipboard |
| `/c N` | Copy Nth most recent response (1 = latest, 2 = second latest) |
| `/c -N` | Copy last N responses (e.g., `/c -3` copies last 3) |
| `/c --all` | Copy full conversation (includes user prompts) |
| `/c -p N` | Copy last N rounds (prompt + response pairs) |
| `/c list [N]` | List recent N responses with previews (default: 10) |
| `/c find "term"` | Search responses (case-insensitive) |
| `-t`, `--think` | Include thinking blocks (wrapped in `<thinking>` tags) |
| `-s <path>` | Save to file instead of clipboard. Auto-appends `.md`/`.txt`/`.json` if no extension |
| `-f md\|txt\|json` | Output format (default: `txt` for clipboard, `md` for file) |
| `--help` | Show usage help |

Everything is combinable. `/c`, `/copy`, and `/copy-response` are all equivalent.

### Output formats

| Format | Default for | Behavior |
|--------|-------------|----------|
| `txt` | Clipboard | Responses joined with `---` separators |
| `md` | File (`-s`) | Markdown with `## User` / `## Assistant` headers, date, session ID |
| `json` | `-f json` | Array of `{role, content, timestamp}` objects |

### Examples

```bash
# Basics
/c                              # Copy last response
/c 3                            # Copy 3rd most recent response
/c -5                           # Copy last 5 responses

# Export to file
/c --all -s conv.md             # Full conversation to markdown
/c -p 3 -s last-3.md           # Last 3 rounds with prompts to file
/c -s output.json -f json       # Last response as JSON file

# With thinking
/c -t                           # Last response with thinking blocks
/c --all -t -s debug.md         # Full conversation with thinking

# Search and browse
/c list                         # Show last 10 responses with previews
/c list 20                      # Show last 20
/c find "error"                 # Find responses mentioning "error"

# Combine flags
/c -3 -f json                   # Last 3 responses as JSON to clipboard
/c --all -t -f json -s full.json  # Everything, with thinking, as JSON file
```

## How it works

This plugin uses a `UserPromptSubmit` hook to intercept `/c` commands before they reach Claude. The hook parses the session transcript JSONL directly and delivers results to clipboard or file. No LLM tokens are consumed.

### Content filtering

The export automatically filters out noise from the transcript:

- **Skill injections** -- skill content loaded via the Skill tool (detected by `Base directory for this skill:` prefix)
- **Task notifications** -- background task completion messages (`<task-notification>` blocks)
- **Command wrappers** -- skill invocation metadata (`<command-message>` blocks)
- **System reminders** -- hook-injected context (`<system-reminder>` blocks)
- **Tool use/results** -- only text and (optionally) thinking blocks are exported
- **Compaction summaries** -- entries marked `isCompactSummary` are skipped

### Round detection

Responses are grouped into "rounds" (one user message + one assistant response). The parser uses turn-boundary markers (`turn_duration`, `stop_hook_summary`) from the transcript to detect where one round ends and the next begins. Multiple assistant message fragments with the same `requestId` are concatenated into a single response.

## Plugin structure

```
c/
├── .claude-plugin/
│   └── plugin.json           # Plugin metadata
├── hooks/
│   └── hooks.json            # UserPromptSubmit hook registration
├── commands/
│   └── c.md                  # Slash command registration + fallback
├── scripts/
│   └── claude-export.py      # Export logic (Python 3, stdlib only)
└── README.md
```

## Requirements

- Python 3.7+
- Claude Code with plugin support
- Clipboard utility: `pbcopy` (macOS), `xclip` (Linux), or `clip.exe` (WSL)

## License

MIT
