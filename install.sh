#!/bin/bash

# Spellbook Installer
# https://github.com/majiayu000/spellbook

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
REPO_URL="${SPELLBOOK_REPO_URL:-https://github.com/majiayu000/spellbook.git}"
LEGACY_REPO_URL="https://github.com/majiayu000/claude-arsenal.git"
CLAUDE_DIR="$HOME/.claude"
CLAUDE_SKILLS_DIR="$CLAUDE_DIR/skills"
CLAUDE_AGENTS_DIR="$CLAUDE_DIR/agents"
CODEX_SKILLS_DIR="${CODEX_SKILLS_DIR:-$HOME/.agents/skills}"
LEGACY_CODEX_SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
INSTALL_DIR="$HOME/.spellbook"
LEGACY_INSTALL_DIR="$HOME/.claude-arsenal"
TARGET="claude"

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║                  Spellbook Installer                      ║"
    echo "║     83 Skills | 7 Agents | Claude + Codex Ready           ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Print colored message
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."

    if ! command -v git &> /dev/null; then
        error "Git is not installed. Please install git first."
    fi

    success "Prerequisites check passed"
}

# Clone or update repository
setup_repo() {
    info "Setting up Spellbook repository..."

    if [ -d "$INSTALL_DIR" ]; then
        info "Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull --quiet
    elif [ -d "$LEGACY_INSTALL_DIR" ]; then
        info "Migrating existing Claude Arsenal checkout..."
        mv "$LEGACY_INSTALL_DIR" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
        git remote set-url origin "$REPO_URL" 2>/dev/null || true
        git pull --quiet || git pull --quiet "$LEGACY_REPO_URL" main
    else
        info "Cloning repository..."
        if ! git clone --quiet "$REPO_URL" "$INSTALL_DIR"; then
            warn "Primary Spellbook URL unavailable; falling back to legacy Claude Arsenal URL"
            git clone --quiet "$LEGACY_REPO_URL" "$INSTALL_DIR"
        fi
    fi

    success "Repository ready at $INSTALL_DIR"
}

# Target helpers
target_includes_claude() {
    [ "$TARGET" = "claude" ] || [ "$TARGET" = "all" ]
}

target_includes_codex() {
    [ "$TARGET" = "codex" ] || [ "$TARGET" = "all" ]
}

validate_target() {
    case "$TARGET" in
        claude|codex|all) ;;
        *) error "Invalid target: $TARGET (expected claude, codex, or all)" ;;
    esac
}

validate_skill_name() {
    local skill_name="$1"
    if [[ ! "$skill_name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
        error "Invalid skill name: $skill_name (expected kebab-case lowercase letters, digits, and hyphens)"
    fi
}

# Create target directories
setup_directories() {
    info "Setting up target directories for: $TARGET"

    if target_includes_claude; then
        mkdir -p "$CLAUDE_SKILLS_DIR"
        mkdir -p "$CLAUDE_AGENTS_DIR"
    fi

    if target_includes_codex; then
        mkdir -p "$CODEX_SKILLS_DIR"
    fi

    success "Directories created"
}

list_installable_skill_names() {
    for skill_dir in "$INSTALL_DIR/skills"/*/; do
        if [ -f "$skill_dir/SKILL.md" ]; then
            basename "${skill_dir%/}"
        fi
    done

    for skill_file in "$INSTALL_DIR/skills"/*.SKILL.md; do
        if [ -f "$skill_file" ]; then
            basename "$skill_file" .SKILL.md
        fi
    done
}

check_skill_conflicts() {
    local duplicates
    duplicates=$(list_installable_skill_names | sort | uniq -d)

    if [ -n "$duplicates" ]; then
        error "Duplicate skill install names found. Resolve these before installing:\n$duplicates"
    fi
}

validate_registry() {
    if [ ! -f "$INSTALL_DIR/scripts/validate_skills.py" ]; then
        warn "Skill validator not found; skipping registry validation"
        return
    fi

    if ! command -v python3 &> /dev/null; then
        error "python3 is required for skill registry validation."
    fi

    python3 "$INSTALL_DIR/scripts/validate_skills.py" --check
}

is_managed_path() {
    local path="$1"
    [ -n "$path" ] || return 1

    case "$path" in
        "$INSTALL_DIR"|"$INSTALL_DIR"/*|"$LEGACY_INSTALL_DIR"|"$LEGACY_INSTALL_DIR"/*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

read_managed_target() {
    local path="$1"
    readlink "$path" 2>/dev/null || readlink -f "$path" 2>/dev/null || true
}

is_current_installable_skill() {
    local skill_name="$1"
    local current_skill

    while IFS= read -r current_skill; do
        if [ "$current_skill" = "$skill_name" ]; then
            return 0
        fi
    done < <(list_installable_skill_names)

    return 1
}

prune_stale_managed_skills_from_dir() {
    local skills_dir="$1"
    local runtime_name="$2"

    [ -d "$skills_dir" ] || return

    local pruned=0
    local skill_path
    for skill_path in "$skills_dir"/*; do
        [ -e "$skill_path" ] || [ -L "$skill_path" ] || continue

        local skill_name
        skill_name=$(basename "$skill_path")

        if is_current_installable_skill "$skill_name"; then
            continue
        fi

        local target
        if [ -L "$skill_path" ]; then
            target=$(read_managed_target "$skill_path")
            if is_managed_path "$target"; then
                rm -f "$skill_path"
                pruned=$((pruned + 1))
            fi
        elif [ -d "$skill_path" ] && [ -L "$skill_path/SKILL.md" ]; then
            target=$(read_managed_target "$skill_path/SKILL.md")
            if is_managed_path "$target"; then
                rm -rf "$skill_path"
                pruned=$((pruned + 1))
            fi
        fi
    done

    if [ "$pruned" -gt 0 ]; then
        info "Pruned $pruned stale managed skill(s) for $runtime_name"
    fi
}

prune_all_managed_skills_from_dir() {
    local skills_dir="$1"
    local runtime_name="$2"

    [ -d "$skills_dir" ] || return

    local pruned=0
    local skill_path
    for skill_path in "$skills_dir"/*; do
        [ -e "$skill_path" ] || [ -L "$skill_path" ] || continue

        local target
        if [ -L "$skill_path" ]; then
            target=$(read_managed_target "$skill_path")
            if is_managed_path "$target"; then
                rm -f "$skill_path"
                pruned=$((pruned + 1))
            fi
        elif [ -d "$skill_path" ] && [ -L "$skill_path/SKILL.md" ]; then
            target=$(read_managed_target "$skill_path/SKILL.md")
            if is_managed_path "$target"; then
                rm -rf "$skill_path"
                pruned=$((pruned + 1))
            fi
        fi
    done

    if [ "$pruned" -gt 0 ]; then
        info "Pruned $pruned legacy managed skill(s) for $runtime_name"
    fi
}

prune_legacy_codex_skills() {
    if [ "$CODEX_SKILLS_DIR" = "$LEGACY_CODEX_SKILLS_DIR" ]; then
        return
    fi

    prune_all_managed_skills_from_dir "$LEGACY_CODEX_SKILLS_DIR" "legacy Codex"
}

prepare_directory_skill_target() {
    local skills_dir="$1"
    local skill_name="$2"
    local target="$skills_dir/$skill_name"

    if [ -L "$target" ]; then
        rm -f "$target"
    elif [ -d "$target" ] && [ -L "$target/SKILL.md" ]; then
        local linked_skill
        linked_skill=$(read_managed_target "$target/SKILL.md")
        if is_managed_path "$linked_skill"; then
            rm -rf "$target"
        fi
    fi
}

prepare_file_skill_target() {
    local skills_dir="$1"
    local skill_name="$2"
    local target="$skills_dir/$skill_name"

    if [ -L "$target" ]; then
        rm -f "$target"
    fi

    mkdir -p "$target"
}

# Install all skills into one runtime target
install_all_skills_to_dir() {
    local skills_dir="$1"
    local runtime_name="$2"

    info "Installing all skills for $runtime_name..."
    prune_stale_managed_skills_from_dir "$skills_dir" "$runtime_name"

    local count=0

    # Install directory-based skills
    for skill_dir in "$INSTALL_DIR/skills"/*/; do
        if [ -f "$skill_dir/SKILL.md" ]; then
            skill_name=$(basename "$skill_dir")
            prepare_directory_skill_target "$skills_dir" "$skill_name"
            ln -sfn "$skill_dir" "$skills_dir/$skill_name"
            count=$((count + 1))
        fi
    done

    # Install file-based skills (.SKILL.md files)
    for skill_file in "$INSTALL_DIR/skills"/*.SKILL.md; do
        if [ -f "$skill_file" ]; then
            skill_name=$(basename "$skill_file" .SKILL.md)
            prepare_file_skill_target "$skills_dir" "$skill_name"
            ln -sfn "$skill_file" "$skills_dir/$skill_name/SKILL.md"
            count=$((count + 1))
        fi
    done

    success "Installed $count skills for $runtime_name"
}

# Install all skills
install_all_skills() {
    if target_includes_claude; then
        install_all_skills_to_dir "$CLAUDE_SKILLS_DIR" "Claude Code"
    fi

    if target_includes_codex; then
        prune_legacy_codex_skills
        install_all_skills_to_dir "$CODEX_SKILLS_DIR" "Codex"
    fi
}

# Install specific skills into one runtime target
install_skills_to_dir() {
    local skills_dir="$1"
    local runtime_name="$2"
    local skills_list="$3"

    info "Installing selected skills for $runtime_name: $skills_list"

    IFS=',' read -ra SKILLS <<< "$skills_list"
    local count=0

    for skill in "${SKILLS[@]}"; do
        skill=$(echo "$skill" | xargs) # trim whitespace
        validate_skill_name "$skill"

        # Check if directory-based skill
        if [ -f "$INSTALL_DIR/skills/$skill/SKILL.md" ]; then
            prepare_directory_skill_target "$skills_dir" "$skill"
            ln -sfn "$INSTALL_DIR/skills/$skill" "$skills_dir/$skill"
            count=$((count + 1))
            info "  ✓ $skill"
        # Check if file-based skill
        elif [ -f "$INSTALL_DIR/skills/$skill.SKILL.md" ]; then
            prepare_file_skill_target "$skills_dir" "$skill"
            ln -sfn "$INSTALL_DIR/skills/$skill.SKILL.md" "$skills_dir/$skill/SKILL.md"
            count=$((count + 1))
            info "  ✓ $skill"
        else
            warn "  ✗ $skill (not found)"
        fi
    done

    success "Installed $count skills for $runtime_name"
}

# Install specific skills
install_skills() {
    local skills_list="$1"

    if target_includes_claude; then
        install_skills_to_dir "$CLAUDE_SKILLS_DIR" "Claude Code" "$skills_list"
    fi

    if target_includes_codex; then
        prune_legacy_codex_skills
        install_skills_to_dir "$CODEX_SKILLS_DIR" "Codex" "$skills_list"
    fi
}

# Install all agents
install_agents() {
    info "Installing agents..."

    local count=0

    for agent_file in "$INSTALL_DIR/agents"/*.md; do
        if [ -f "$agent_file" ]; then
            agent_name=$(basename "$agent_file")
            ln -sfn "$agent_file" "$CLAUDE_AGENTS_DIR/$agent_name"
            count=$((count + 1))
        fi
    done

    success "Installed $count agents"
}

# List available skills
list_skills() {
    echo -e "\n${BLUE}Available Skills:${NC}\n"

    echo "Directory-based skills:"
    for skill_dir in "$INSTALL_DIR/skills"/*/; do
        if [ -f "$skill_dir/SKILL.md" ]; then
            echo "  - $(basename "$skill_dir")"
        fi
    done

    echo -e "\nFile-based skills:"
    for skill_file in "$INSTALL_DIR/skills"/*.SKILL.md; do
        if [ -f "$skill_file" ]; then
            echo "  - $(basename "$skill_file" .SKILL.md)"
        fi
    done
}

# Uninstall
uninstall_from_skills_dir() {
    local skills_dir="$1"

    for skill_path in "$skills_dir"/*; do
        [ -e "$skill_path" ] || [ -L "$skill_path" ] || continue

        if [ -L "$skill_path" ]; then
            target=$(read_managed_target "$skill_path")
            if is_managed_path "$target"; then
                rm -f "$skill_path"
            fi
        elif [ -d "$skill_path" ] && [ -L "$skill_path/SKILL.md" ]; then
            target=$(read_managed_target "$skill_path/SKILL.md")
            if is_managed_path "$target"; then
                rm -rf "$skill_path"
            fi
        fi
    done
}

uninstall() {
    warn "Uninstalling Spellbook..."

    if target_includes_claude; then
        uninstall_from_skills_dir "$CLAUDE_SKILLS_DIR"

        for agent_file in "$CLAUDE_AGENTS_DIR"/*.md; do
            if [ -L "$agent_file" ]; then
                target=$(readlink -f "$agent_file" 2>/dev/null || readlink "$agent_file" 2>/dev/null)
                if is_managed_path "$target"; then
                    rm -f "$agent_file"
                fi
            fi
        done
    fi

    if target_includes_codex; then
        uninstall_from_skills_dir "$CODEX_SKILLS_DIR"
    fi

    if [ "$TARGET" = "all" ]; then
        rm -rf "$INSTALL_DIR"
        rm -rf "$LEGACY_INSTALL_DIR"
    else
        warn "Leaving shared source checkout at $INSTALL_DIR; use --target all --uninstall to remove it"
    fi

    success "Spellbook uninstalled for target: $TARGET"
}

# Print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --target TARGET       Install target: claude, codex, or all (default: claude)"
    echo "  --all                 Install all skills and supported agents"
    echo "  --skills SKILL_LIST   Install specific skills (comma-separated)"
    echo "  --agents              Install only Claude Code agents"
    echo "  --list                List available skills"
    echo "  --validate            Validate skill registry and metadata"
    echo "  --uninstall           Remove Spellbook symlinks for the selected target"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --target all --all"
    echo "  $0 --target codex --skills typescript-project,python-project"
    echo "  $0 --list"
}

parse_args() {
    POSITIONAL=()
    while [ $# -gt 0 ]; do
        case "$1" in
            --target)
                if [ -z "${2:-}" ]; then
                    error "Please provide a target: claude, codex, or all"
                fi
                TARGET="$2"
                shift 2
                ;;
            *)
                POSITIONAL+=("$1")
                shift
                ;;
        esac
    done

    set -- "${POSITIONAL[@]}"
    PARSED_ARGS=("$@")
}

install_supported_agents() {
    if target_includes_claude; then
        install_agents
    elif [ "$TARGET" = "codex" ]; then
        warn "Agents are Claude Code-specific; skipping agents for Codex target"
    fi
}

# Main
main() {
    parse_args "$@"
    set -- "${PARSED_ARGS[@]}"

    print_banner
    validate_target

    if [ $# -eq 0 ]; then
        check_prerequisites
        setup_repo
        check_skill_conflicts
        validate_registry
        setup_directories
        install_all_skills
        install_supported_agents
    else
        case "$1" in
            --all)
                check_prerequisites
                setup_repo
                check_skill_conflicts
                validate_registry
                setup_directories
                install_all_skills
                install_supported_agents
                ;;
            --skills)
                if [ -z "${2:-}" ]; then
                    error "Please provide a comma-separated list of skills"
                fi
                check_prerequisites
                setup_repo
                check_skill_conflicts
                validate_registry
                setup_directories
                install_skills "$2"
                ;;
            --agents)
                check_prerequisites
                setup_repo
                setup_directories
                install_supported_agents
                ;;
            --list)
                setup_repo
                check_skill_conflicts
                list_skills
                exit 0
                ;;
            --validate)
                setup_repo
                check_skill_conflicts
                validate_registry
                exit 0
                ;;
            --uninstall)
                uninstall
                exit 0
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1\nRun '$0 --help' for usage."
                ;;
        esac
    fi

    echo ""
    success "Installation complete!"
    echo ""
    info "Next steps:"
    if target_includes_claude; then
        echo "  - Claude Code: type '/' to see installed skills"
    fi
    if target_includes_codex; then
        echo "  - Codex: restart Codex so it reloads $CODEX_SKILLS_DIR"
    fi
    echo "  - Start using skills like /typescript-project"
    echo ""
    info "Installation directory: $INSTALL_DIR"
    if target_includes_claude; then
        info "Claude skills directory: $CLAUDE_SKILLS_DIR"
    fi
    if target_includes_codex; then
        info "Codex skills directory: $CODEX_SKILLS_DIR"
    fi
    echo ""
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
