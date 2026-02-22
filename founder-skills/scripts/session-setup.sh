#!/usr/bin/env bash
set -euo pipefail
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  escaped=$(printf '%q' "$CLAUDE_PLUGIN_ROOT")
  new_line="export CLAUDE_PLUGIN_ROOT=${escaped}"
  # Remove any existing export line (exact anchor, not substring)
  if [ -f "$CLAUDE_ENV_FILE" ]; then
    tmp="${CLAUDE_ENV_FILE}.tmp.$$"
    grep -v '^export CLAUDE_PLUGIN_ROOT=' "$CLAUDE_ENV_FILE" > "$tmp" 2>/dev/null || true
    mv "$tmp" "$CLAUDE_ENV_FILE"
  fi
  echo "$new_line" >> "$CLAUDE_ENV_FILE"
fi
exit 0
