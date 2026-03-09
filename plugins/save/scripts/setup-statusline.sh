#!/bin/bash
# setup-statusline.sh — Install the statusline sidecar wrapper for enriched session metadata.
#
# This wraps your existing statusLine.command to also write a sidecar JSON file
# that save-session.py reads for cost, context window, worktree, and version data.
#
# Usage: bash setup-statusline.sh [--uninstall]
#
# What it does:
#   1. Creates ~/.claude/hooks/statusline-wrapper.sh
#   2. Updates settings.json statusLine.command to use the wrapper
#
# This is OPTIONAL. Without it, sessions still save with basic metadata
# (session ID, timestamp, model, git branch, working directory).

set -euo pipefail

WRAPPER_PATH="$HOME/.claude/hooks/statusline-wrapper.sh"
SETTINGS_PATH="$HOME/.claude/settings.json"
SIDECAR_PATH="$HOME/.claude/.session-context.json"

# --- Uninstall mode ---
if [[ "${1:-}" == "--uninstall" ]]; then
    echo "Removing statusline wrapper..."

    if [[ -f "$SETTINGS_PATH" ]]; then
        # Restore default statusline command
        python3 -c "
import json, sys
p = '$SETTINGS_PATH'
with open(p) as f: s = json.load(f)
cmd = s.get('statusLine', {}).get('command', '')
if 'statusline-wrapper' in cmd:
    s['statusLine']['command'] = 'bunx -y ccstatusline@latest'
    with open(p, 'w') as f: json.dump(s, f, indent=2)
    print('Restored default statusline command')
else:
    print('statusline command not using wrapper, skipping')
"
    fi

    [[ -f "$WRAPPER_PATH" ]] && rm "$WRAPPER_PATH" && echo "Removed $WRAPPER_PATH"
    [[ -f "$SIDECAR_PATH" ]] && rm "$SIDECAR_PATH" && echo "Removed sidecar file"
    echo "Done. Restart Claude Code for changes to take effect."
    exit 0
fi

# --- Install mode ---
echo "Installing statusline sidecar wrapper..."

# Ensure hooks directory exists
mkdir -p "$(dirname "$WRAPPER_PATH")"

# Write the wrapper script
cat > "$WRAPPER_PATH" << 'WRAPPER'
#!/bin/bash
# Wraps the statusline command to save session context as a sidecar file.
# The save-session.py hook reads this file for rich frontmatter metadata.

INPUT=$(cat)
SIDECAR="$HOME/.claude/.session-context.json"

# Write sidecar (atomic via temp file to avoid partial reads)
TMPFILE=$(mktemp "${SIDECAR}.XXXXXX")
echo "$INPUT" > "$TMPFILE"
mv -f "$TMPFILE" "$SIDECAR"

# Pipe to the real statusline
echo "$INPUT" | bunx -y ccstatusline@latest
WRAPPER

chmod +x "$WRAPPER_PATH"
echo "Created $WRAPPER_PATH"

# Update settings.json
if [[ -f "$SETTINGS_PATH" ]]; then
    python3 -c "
import json
p = '$SETTINGS_PATH'
with open(p) as f: s = json.load(f)
s.setdefault('statusLine', {})['command'] = '$WRAPPER_PATH'
with open(p, 'w') as f: json.dump(s, f, indent=2)
print('Updated statusLine.command in settings.json')
"
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
