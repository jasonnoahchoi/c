#!/bin/bash
# setup-statusline.sh — Install the statusline sidecar wrapper for enriched session metadata.
#
# This wraps your existing statusLine.command to also write a sidecar JSON file
# that save-session.py reads for cost, context window, worktree, and version data.
#
# Usage: bash setup-statusline.sh [--uninstall]
#
# What it does:
#   1. Backs up your current statusLine.command
#   2. Creates ~/.claude/hooks/statusline-wrapper.sh
#   3. Updates settings.json statusLine.command to use the wrapper
#
# This is OPTIONAL. Without it, sessions still save with basic metadata
# (session ID, timestamp, model, git branch, working directory).

set -uo pipefail

WRAPPER_PATH="$HOME/.claude/hooks/statusline-wrapper.sh"
SETTINGS_PATH="$HOME/.claude/settings.json"
SIDECAR_PATH="$HOME/.claude/.session-context.json"
BACKUP_PATH="$HOME/.claude/.statusline-backup"

# --- Uninstall mode ---
if [[ "${1:-}" == "--uninstall" ]]; then
    echo "Removing statusline wrapper..."

    if [[ -f "$SETTINGS_PATH" ]]; then
        # Restore original statusline command from backup
        SETTINGS_PATH="$SETTINGS_PATH" BACKUP_PATH="$BACKUP_PATH" python3 -c "
import json, os
p = os.environ['SETTINGS_PATH']
bp = os.environ['BACKUP_PATH']
try:
    with open(p) as f: s = json.load(f)
except (json.JSONDecodeError, OSError) as e:
    print(f'Warning: could not read settings.json: {e}')
    raise SystemExit(1)
cmd = s.get('statusLine', {}).get('command', '')
if 'statusline-wrapper' not in cmd:
    print('statusline command not using wrapper, skipping')
    raise SystemExit(0)
# Restore from backup if available, otherwise use default
original = None
try:
    with open(bp) as f: original = f.read().strip()
except OSError:
    pass
restore_cmd = original or 'bunx -y ccstatusline@latest'
s['statusLine']['command'] = restore_cmd
with open(p, 'w') as f: json.dump(s, f, indent=2)
print(f'Restored statusline command: {restore_cmd}')
" || echo "Warning: failed to update settings.json, continuing cleanup..." >&2
    fi

    [[ -f "$WRAPPER_PATH" ]] && rm "$WRAPPER_PATH" && echo "Removed $WRAPPER_PATH"
    [[ -f "$SIDECAR_PATH" ]] && rm "$SIDECAR_PATH" && echo "Removed sidecar file"
    [[ -f "$BACKUP_PATH" ]] && rm "$BACKUP_PATH" && echo "Removed backup file"
    echo "Done. Restart Claude Code for changes to take effect."
    exit 0
fi

# --- Install mode ---
echo "Installing statusline sidecar wrapper..."

# Ensure hooks directory exists
mkdir -p "$(dirname "$WRAPPER_PATH")"

# Back up current statusline command before overwriting
if [[ -f "$SETTINGS_PATH" ]]; then
    SETTINGS_PATH="$SETTINGS_PATH" BACKUP_PATH="$BACKUP_PATH" python3 -c "
import json, os
p = os.environ['SETTINGS_PATH']
bp = os.environ['BACKUP_PATH']
try:
    with open(p) as f: s = json.load(f)
    cmd = s.get('statusLine', {}).get('command', '')
    if cmd and 'statusline-wrapper' not in cmd:
        with open(bp, 'w') as f: f.write(cmd)
        print(f'Backed up original statusline command: {cmd}')
except (json.JSONDecodeError, OSError) as e:
    print(f'Warning: could not back up statusline command: {e}')
" || true
fi

# Write the wrapper script
cat > "$WRAPPER_PATH" << 'WRAPPER'
#!/bin/bash
# Wraps the statusline command to save session context as a sidecar file.
# The save-session.py hook reads this file for rich frontmatter metadata.

INPUT=$(cat)
SIDECAR="$HOME/.claude/.session-context.json"

# Write sidecar (atomic via temp file to avoid partial reads)
if TMPFILE=$(mktemp "${SIDECAR}.XXXXXX" 2>/dev/null); then
    echo "$INPUT" > "$TMPFILE"
    mv -f "$TMPFILE" "$SIDECAR"
fi

# Pipe to the real statusline (skip if bunx not available)
if command -v bunx >/dev/null 2>&1; then
    echo "$INPUT" | bunx -y ccstatusline@latest
fi
WRAPPER

chmod +x "$WRAPPER_PATH"
echo "Created $WRAPPER_PATH"

# Update settings.json
if [[ -f "$SETTINGS_PATH" ]]; then
    if WRAPPER_PATH="$WRAPPER_PATH" SETTINGS_PATH="$SETTINGS_PATH" python3 -c "
import json, os
p = os.environ['SETTINGS_PATH']
with open(p) as f: s = json.load(f)
s.setdefault('statusLine', {})['command'] = os.environ['WRAPPER_PATH']
with open(p, 'w') as f: json.dump(s, f, indent=2)
print('Updated statusLine.command in settings.json')
"; then
        :
    else
        echo "Error: failed to update settings.json" >&2
        echo "You may need to set statusLine.command manually to: $WRAPPER_PATH" >&2
        exit 1
    fi
else
    echo "Warning: $SETTINGS_PATH not found. You may need to set statusLine.command manually."
    echo "Set it to: $WRAPPER_PATH"
fi

echo ""
echo "Done! Restart Claude Code for changes to take effect."
echo ""
echo "Your sessions will now include enriched metadata:"
echo "  - Cost (USD, duration, lines added/removed)"
echo "  - Context window usage"
echo "  - Worktree info"
echo "  - Claude Code version"
echo ""
echo "To uninstall: bash $0 --uninstall"
