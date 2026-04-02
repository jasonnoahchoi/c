# c - Claude Code Conversation Tools

A marketplace plugin collection for working with Claude Code conversations. Three tools, one obsession: **never lose a conversation again.**

## The Origin Story

`c` started on March 5, 2026, at 3:01 PM, born from the most universal Claude Code frustration: you're deep in a 2-hour session, you hit `/clear`, and your entire conversation vanishes. Not from the transcript files - Claude Code always saves those - but from your terminal. Your scrollback. The thing you instinctively scroll up to re-read.

The first commit was a single Python script called `/c` that could copy the last assistant response to your clipboard. That's it. One command, one annoyance solved.

Then it grew. `/c:c` became `/c:this` (because naming things is hard). The save plugin appeared four days later when Jason realized the clipboard trick didn't help if the session crashed - you needed auto-saves too. The hooks evolved: `PreCompact` to catch compaction events, `SessionEnd` to catch exits and `/clear`.

The naming went through its own journey. The plugins started as `c-copy` and `c-save`, got refactored into a marketplace structure, then the commands got renamed again when Claude Code's plugin system matured. Every name change has a commit message that reads like a small sigh of relief.

Then came March 31. A deep dive into the Claude Code source revealed **why** scrollback disappears - `CSI 3J` (`\x1b[3J`), an ANSI escape sequence that tells your terminal to erase its scrollback buffer. It fires not just on `/clear`, but during normal rendering when the frame overflows the viewport. The terminal isn't just clearing the screen - it's destroying the buffer.

The solution wasn't to fight the escape sequence. It was to watch from somewhere it can't reach. **Tower** was born: a Python script that tails the raw JSONL transcript in a separate terminal pane, rendering the conversation in real-time with ANSI colors. Claude Code can clear its own terminal all day long. Tower runs in a different pane. It doesn't care.

The name "tower" came from air traffic control - a place where someone watches everything happening, undisturbed by the chaos on the ground.

Together, the three plugins cover the full lifecycle:

- **save** - the flight recorder (always on, always writing)
- **copy** - the radio (grab what you need, when you need it)
- **tower** - the control tower (see everything, in real-time)

## Plugins

### tower

Live conversation mirror. Run in a split terminal pane to see your full session in real-time - including after `/clear` or `/compact` wipes your scrollback.

<video src="assets/tower-demo.mp4" autoplay loop muted playsinline width="100%"></video>

**Setup:**

```bash
# From the tower plugin directory:
bash plugins/tower/scripts/setup.sh
source ~/.zshrc
```

The setup script installs `tower` to `~/bin/` and auto-configures split-pane shortcuts for your terminal:

| Terminal | What it does | Shortcut |
|----------|-------------|----------|
| **Ghostty** | Adds keybind to split right | `Cmd+Shift+T`, then type `tw` |
| **tmux** | Split + run tower in one keybind | `prefix+T` |
| **Kitty** | Split + run tower in one keybind | `Cmd+Shift+T` |
| **iTerm2** | Installs a Python script | Scripts menu > tower-split |
| **WezTerm** | Adds config comment with keybind | Manual: add to `keys` table |
| **Warp** | Creates a Launch Configuration | Sessions > Claude + Tower |
| **Zellij** | Prints the split command | `zellij action new-pane -d right -- tower` |
| **Windows Terminal** | Prints the settings.json snippet | `Ctrl+Shift+T` |

**Usage from Claude Code (recommended):**

```
/tower:watch        # Auto-detect terminal, open split pane, start mirroring
/tower:setup        # First-time install: binary, alias, terminal shortcuts
```

`/tower:watch` detects your terminal and programmatically opens a split pane with tower running. No manual window management needed.

**Usage from the terminal directly:**

```bash
tower              # Watch most recent session (basic streaming mode)
tower --tui        # Interactive TUI with collapsible tool calls
tower -i           # Alias for --tui
tower --list       # List recent sessions with previews
tower 1            # Watch most recent from list
tower 3            # Third most recent
tower 69f6ac9a     # Partial session ID match
tw                 # Alias
```

**TUI keybindings:**

| Key | Action |
|-----|--------|
| `j`/`k` | Scroll down/up |
| `g`/`G` | Jump to top/bottom |
| `/` | Search messages |
| `t` | Toggle tool calls |
| `d` | Toggle diff details |
| `Enter` | Expand/collapse tool call |
| `Esc` | Clear search |
| `q` | Quit |

**Workflow:**

```
+---------------------------+---------------------------+
|                           |                           |
|   Claude Code             |   Tower                   |
|                           |                           |
|   > fix the auth bug      |   ## User                 |
|                           |   fix the auth bug        |
|   [editing files...]      |                           |
|                           |   ## Assistant             |
|   Done! Fixed the null    |   > Grep `auth` in src/   |
|   check in auth.ts        |   > Edit src/auth.ts      |
|                           |   Done! Fixed the null    |
|   > /clear                |   check in auth.ts        |
|                           |                           |
|   (scrollback gone)       |   (still here)            |
|                           |                           |
+---------------------------+---------------------------+
```

### copy

Copy & export conversation responses to clipboard or file.

| Usage | Description |
|-------|-------------|
| `/copy:this` | Copy last response to clipboard |
| `/copy:this N` | Copy Nth most recent response |
| `/copy:this -N` | Copy last N responses |
| `/copy:this --all` | Copy full conversation |
| `/copy:this -p N` | Copy last N rounds (prompt + response pairs) |
| `/copy:this list [N]` | List recent N responses with previews |
| `/copy:this find "term"` | Search responses |
| `-t` | Include thinking blocks |
| `-s <path>` | Save to file instead of clipboard |
| `-f md\|txt\|json` | Output format |

### save

Auto-save readable session transcripts to `~/.claude/sessions/` before compact/clear wipes terminal scrollback. Fires on `PreCompact` and `SessionEnd` events.

Each saved session is a markdown file with YAML frontmatter:

```yaml
---
sessionId: abc12345
timestamp: 2026-03-09T14:30:00
trigger: precompact
cwd: /Users/you/project
model: claude-opus-4-6
gitBranch: feature/cool-thing
cost:
  usd: 3.42
  durationSeconds: 1847
contextWindow:
  usedPercent: 45
---
```

**Basic mode** (zero config): Saves session ID, timestamp, model, git branch, cwd.

**Enriched mode** (optional): Run `/save:setup` to also capture cost, context window, worktree, and version data via a statusline sidecar wrapper.

## Install

```bash
claude plugin add jasonnoahchoi/c
```

Or from local:

```bash
claude plugin add /path/to/c
```

## Structure

```
c/
├── .claude-plugin/
│   └── marketplace.json     # Plugin registry
├── plugins/
│   ├── copy/                # copy: clipboard export
│   │   ├── .claude-plugin/plugin.json
│   │   ├── hooks/hooks.json
│   │   ├── scripts/claude-export.py
│   │   └── commands/this.md
│   ├── save/                # save: session preservation
│   │   ├── .claude-plugin/plugin.json
│   │   ├── hooks/hooks.json
│   │   ├── scripts/save-session.py
│   │   ├── scripts/setup-statusline.sh
│   │   └── commands/setup.md
│   └── tower/               # tower: live session mirror
│       ├── .claude-plugin/plugin.json
│       ├── bin/
│       │   ├── tower              # CLI entry point
│       │   ├── tower_parser.py    # Shared JSONL parser
│       │   ├── tower_tui.py       # Interactive TUI (textual)
│       │   └── tower_tui.css      # TUI styling
│       ├── skills/watch/SKILL.md
│       ├── commands/setup.md
│       ├── requirements.txt
│       └── scripts/
│           ├── setup.sh
│           ├── detect-terminal.sh
│           └── launch-pane.sh
└── README.md
```

## Requirements

- Python 3.10+
- Claude Code with plugin support
- Clipboard utility: `pbcopy` (macOS), `xclip` (Linux), or `clip.exe` (WSL)

## License

MIT
