#!/bin/bash
# check-codex.sh - Check if Codex CLI is installed and authenticated
# Place in: ~/.claude/skills/codex-agent/scripts/

set -e

echo "Checking Codex CLI installation..."

# Check if codex is installed
if ! command -v codex &> /dev/null; then
    echo "ERROR: Codex CLI not found"
    echo ""
    echo "Install via npm:"
    echo "  npm install -g @openai/codex"
    echo ""
    echo "Or via Homebrew (macOS):"
    echo "  brew install --cask codex"
    echo ""
    exit 1
fi

VERSION=$(codex --version 2>/dev/null || echo "unknown")
echo "Codex CLI found: $VERSION"
echo "Path: $(which codex)"

# Check authentication by trying a simple read-only command.
echo ""
echo "Checking authentication..."

# Try to run a minimal command
if codex exec -s read-only "echo test" &>/dev/null; then
    echo "Authentication: OK"
else
    echo "WARNING: Authentication may not be configured, or this directory is not accepted by Codex"
    echo ""
    echo "Run 'codex login' to authenticate"
fi

echo ""
echo "Codex CLI is ready to use!"
