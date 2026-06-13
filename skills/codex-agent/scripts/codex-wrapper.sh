#!/bin/bash
# codex-wrapper.sh - Wrapper script for calling Codex with common defaults
# Place in: ~/.claude/skills/codex-agent/scripts/

set -e

# Defaults
SANDBOX="${CODEX_SANDBOX:-read-only}"
OUTPUT_FORMAT=""
OUTPUT_FILE=""
SESSION=""
WORKDIR="${PWD}"
CONFIG_OVERRIDES=()

usage() {
    cat << EOF
Usage: codex-wrapper.sh [options] "<task>"

Options:
  -d, --dir <path>       Working directory (default: current)
  -s, --sandbox <mode>   Sandbox mode: read-only, workspace-write, danger-full-access
  -j, --json             Output as JSON
  -c, --config <key=val> Pass a Codex config override (repeatable)
  -o, --output <file>    Save output to file
  -S, --session <id>     Use session ID for follow-up
  -h, --help             Show this help

Examples:
  codex-wrapper.sh -d /path/to/project "Analyze the code"
  codex-wrapper.sh -j -s workspace-write "Fix the bug in main.ts"
  codex-wrapper.sh -s workspace-write -c 'sandbox_workspace_write.network_access=true' "Install dependencies"
  codex-wrapper.sh -S abc123 "Continue from where we left off"
EOF
    exit 0
}

# Parse arguments
POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dir)
            [[ $# -ge 2 ]] || { echo "Error: --dir requires a path" >&2; exit 2; }
            WORKDIR="$2"
            shift 2
            ;;
        -s|--sandbox)
            [[ $# -ge 2 ]] || { echo "Error: --sandbox requires a mode" >&2; exit 2; }
            SANDBOX="$2"
            shift 2
            ;;
        -j|--json)
            OUTPUT_FORMAT="--json"
            shift
            ;;
        -c|--config)
            [[ $# -ge 2 ]] || { echo "Error: --config requires key=value" >&2; exit 2; }
            CONFIG_OVERRIDES+=(-c "$2")
            shift 2
            ;;
        -o|--output)
            [[ $# -ge 2 ]] || { echo "Error: --output requires a file" >&2; exit 2; }
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -S|--session)
            [[ $# -ge 2 ]] || { echo "Error: --session requires an id" >&2; exit 2; }
            SESSION="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        -*)
            echo "Error: unsupported option: $1" >&2
            exit 2
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

set -- "${POSITIONAL_ARGS[@]}"

if [[ $# -eq 0 ]]; then
    echo "Error: Task description required"
    usage
fi

TASK="$*"

# Validate high-impact options before building the command.
case "$SANDBOX" in
    read-only|workspace-write|danger-full-access) ;;
    *)
        echo "Error: unsupported sandbox mode: $SANDBOX" >&2
        exit 2
        ;;
esac

if [[ "$SANDBOX" == "danger-full-access" && "${CODEX_ALLOW_DANGER_FULL_ACCESS:-}" != "1" ]]; then
    echo "Error: danger-full-access requires CODEX_ALLOW_DANGER_FULL_ACCESS=1" >&2
    exit 2
fi

if [[ -n "$SESSION" && ${#CONFIG_OVERRIDES[@]} -gt 0 ]]; then
    echo "Error: --config is only supported for new codex exec tasks, not session resume" >&2
    exit 2
fi

if [[ -n "$SESSION" ]]; then
    # Build command as an argv array. Do not use eval with user-controlled text.
    CMD=(codex exec -C "$WORKDIR" resume)
else
    # Build command as an argv array. Do not use eval with user-controlled text.
    CMD=(codex exec -C "$WORKDIR" -s "$SANDBOX")
    CMD+=("${CONFIG_OVERRIDES[@]}")
fi

if [[ -n "$OUTPUT_FORMAT" ]]; then
    CMD+=("$OUTPUT_FORMAT")
fi

if [[ -n "$OUTPUT_FILE" ]]; then
    CMD+=(-o "$OUTPUT_FILE")
fi

if [[ -n "$SESSION" ]]; then
    CMD+=("$SESSION")
fi

CMD+=("$TASK")

# Execute
"${CMD[@]}"
