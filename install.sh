#!/bin/bash

# Claude Arsenal Installer
# https://github.com/majiayu000/claude-arsenal

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
REPO_URL="https://github.com/majiayu000/claude-arsenal.git"
CLAUDE_DIR="$HOME/.claude"
SKILLS_DIR="$CLAUDE_DIR/skills"
INSTALL_DIR="$HOME/.claude-arsenal"

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║              Claude Arsenal Installer                     ║"
    echo "║     74 Skills | 7 Agents | Production Ready               ║"
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
    info "Setting up Claude Arsenal repository..."

    if [ -d "$INSTALL_DIR" ]; then
        info "Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull --quiet
    else
        info "Cloning repository..."
        git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    fi

    success "Repository ready at $INSTALL_DIR"
}

# Create claude directories
setup_directories() {
    info "Setting up Claude directories..."

    mkdir -p "$SKILLS_DIR"
    mkdir -p "$CLAUDE_DIR/agents"

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

prepare_directory_skill_target() {
    local skill_name="$1"
    local target="$SKILLS_DIR/$skill_name"

    if [ -L "$target" ]; then
        rm -f "$target"
    elif [ -d "$target" ] && [ -L "$target/SKILL.md" ]; then
        local linked_skill
        linked_skill=$(readlink "$target/SKILL.md" 2>/dev/null || true)
        if [[ "$linked_skill" == *"claude-arsenal"* ]]; then
            rm -rf "$target"
        fi
    fi
}

prepare_file_skill_target() {
    local skill_name="$1"
    local target="$SKILLS_DIR/$skill_name"

    if [ -L "$target" ]; then
        rm -f "$target"
    fi

    mkdir -p "$target"
}

# Install all skills
install_all_skills() {
    info "Installing all skills..."

    local count=0

    # Install directory-based skills
    for skill_dir in "$INSTALL_DIR/skills"/*/; do
        if [ -f "$skill_dir/SKILL.md" ]; then
            skill_name=$(basename "$skill_dir")
            prepare_directory_skill_target "$skill_name"
            ln -sfn "$skill_dir" "$SKILLS_DIR/$skill_name"
            count=$((count + 1))
        fi
    done

    # Install file-based skills (.SKILL.md files)
    for skill_file in "$INSTALL_DIR/skills"/*.SKILL.md; do
        if [ -f "$skill_file" ]; then
            skill_name=$(basename "$skill_file" .SKILL.md)
            prepare_file_skill_target "$skill_name"
            ln -sfn "$skill_file" "$SKILLS_DIR/$skill_name/SKILL.md"
            count=$((count + 1))
        fi
    done

    success "Installed $count skills"
}

# Install specific skills
install_skills() {
    local skills_list="$1"
    info "Installing selected skills: $skills_list"

    IFS=',' read -ra SKILLS <<< "$skills_list"
    local count=0

    for skill in "${SKILLS[@]}"; do
        skill=$(echo "$skill" | xargs) # trim whitespace

        # Check if directory-based skill
        if [ -f "$INSTALL_DIR/skills/$skill/SKILL.md" ]; then
            prepare_directory_skill_target "$skill"
            ln -sfn "$INSTALL_DIR/skills/$skill" "$SKILLS_DIR/$skill"
            count=$((count + 1))
            info "  ✓ $skill"
        # Check if file-based skill
        elif [ -f "$INSTALL_DIR/skills/$skill.SKILL.md" ]; then
            prepare_file_skill_target "$skill"
            ln -sfn "$INSTALL_DIR/skills/$skill.SKILL.md" "$SKILLS_DIR/$skill/SKILL.md"
            count=$((count + 1))
            info "  ✓ $skill"
        else
            warn "  ✗ $skill (not found)"
        fi
    done

    success "Installed $count skills"
}

# Install all agents
install_agents() {
    info "Installing agents..."

    local count=0

    for agent_file in "$INSTALL_DIR/agents"/*.md; do
        if [ -f "$agent_file" ]; then
            agent_name=$(basename "$agent_file")
            ln -sfn "$agent_file" "$CLAUDE_DIR/agents/$agent_name"
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
uninstall() {
    warn "Uninstalling Claude Arsenal..."

    # Remove skill symlinks
    for skill_dir in "$SKILLS_DIR"/*/; do
        if [ -L "$skill_dir" ] || [ -L "${skill_dir%/}" ]; then
            target=$(readlink -f "$skill_dir" 2>/dev/null || readlink "$skill_dir" 2>/dev/null)
            if [[ "$target" == *"claude-arsenal"* ]]; then
                rm -f "$skill_dir"
            fi
        fi
    done

    # Remove agent symlinks
    for agent_file in "$CLAUDE_DIR/agents"/*.md; do
        if [ -L "$agent_file" ]; then
            target=$(readlink -f "$agent_file" 2>/dev/null || readlink "$agent_file" 2>/dev/null)
            if [[ "$target" == *"claude-arsenal"* ]]; then
                rm -f "$agent_file"
            fi
        fi
    done

    # Remove installation directory
    rm -rf "$INSTALL_DIR"

    success "Claude Arsenal uninstalled"
}

# Print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --all                 Install all skills and agents"
    echo "  --skills SKILL_LIST   Install specific skills (comma-separated)"
    echo "  --agents              Install only agents"
    echo "  --list                List available skills"
    echo "  --validate            Validate skill registry and metadata"
    echo "  --uninstall           Remove Claude Arsenal"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --all"
    echo "  $0 --skills typescript-project,python-project,devops-excellence"
    echo "  $0 --list"
}

# Main
main() {
    print_banner

    # Parse arguments
    if [ $# -eq 0 ]; then
        # Default: install all
        check_prerequisites
        setup_repo
        check_skill_conflicts
        validate_registry
        setup_directories
        install_all_skills
        install_agents
    else
        case "$1" in
            --all)
                check_prerequisites
                setup_repo
                check_skill_conflicts
                validate_registry
                setup_directories
                install_all_skills
                install_agents
                ;;
            --skills)
                if [ -z "$2" ]; then
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
                install_agents
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
    echo "  1. Open Claude Code"
    echo "  2. Type '/' to see your installed skills"
    echo "  3. Start using skills like /typescript-project"
    echo ""
    info "Installation directory: $INSTALL_DIR"
    info "Skills directory: $SKILLS_DIR"
    echo ""
}

main "$@"
