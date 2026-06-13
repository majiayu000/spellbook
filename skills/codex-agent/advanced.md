# Advanced Configuration

Advanced usage patterns, MCP integration, and configuration options.

## Configuration Files

Codex CLI reads configuration from `~/.codex/config.toml`.

### Basic Config

```toml
# ~/.codex/config.toml

# Default model
# Omit this to use the installed Codex default, or set a model supported by
# your current Codex CLI.
# model = "<codex-model>"

# Default sandbox mode
sandbox_mode = "read-only"

# Enable web search
search = true
```

### Profiles

Create a separate profile file for each use case. In Codex 0.134.0 and later,
`--profile <name>` overlays `$CODEX_HOME/<name>.config.toml` on top of the base
config; it does not read `[profiles.<name>]` tables from `config.toml`.

```toml
# ~/.codex/review.config.toml
sandbox_mode = "read-only"
```

```toml
# ~/.codex/implement.config.toml
sandbox_mode = "workspace-write"
```

Do not persist a `danger-full-access` + no-approval profile. If broad access is
unavoidable, use it as a one-off command after explicit user approval and record
what directory or system boundary required it.

Use with `-p` / `--profile`:

```bash
codex exec -p review -C /project "Analyze code"
codex exec -p implement -C /project "Add feature"
```

## MCP Integration

Codex supports Model Context Protocol (MCP) for external tool integration.

### Add MCP Server (stdio)

```bash
codex mcp add my-server -- /path/to/mcp-server
```

### Add MCP Server (HTTP)

```bash
codex mcp add remote-server --url https://mcp.example.com/api
```

### List MCP Servers

```bash
codex mcp list --json
```

### Run Codex as MCP Server

```bash
codex mcp-server
```

This allows other MCP clients to use Codex as a tool provider.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CODEX_API_KEY` | OpenAI API key (alternative to login) |
| `CODEX_MODEL` | Default model override |
| `CODEX_SANDBOX` | Default sandbox mode |

### CI/CD Usage

```bash
export CODEX_API_KEY="<load from your secret manager or environment>"
codex exec --json "Generate changelog from git log"
```

## Feature Flags

Enable/disable experimental features:

```bash
# Enable feature
codex exec --enable some-feature "task"

# Disable feature
codex exec --disable some-feature "task"
```

## Custom Instructions (AGENTS.md)

Create `AGENTS.md` in your project root to provide project-specific context:

```markdown
# Project Context

This is a TypeScript Node.js project using Express.

## Conventions
- Use async/await, not callbacks
- Use Zod for validation
- Tests use Jest with supertest

## Architecture
- src/api/ - Express routes
- src/services/ - Business logic
- src/models/ - Data models
```

Codex will read this file for context.

## Shell Completions

Generate shell completions:

```bash
# Bash
codex completion bash > /etc/bash_completion.d/codex

# Zsh
codex completion zsh > ~/.zfunc/_codex

# Fish
codex completion fish > ~/.config/fish/completions/codex.fish
```

## JSON Schema Validation

Enforce structured output:

```bash
# schema.json
{
  "type": "object",
  "properties": {
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "file": { "type": "string" },
          "line": { "type": "integer" },
          "severity": { "type": "string" },
          "message": { "type": "string" }
        }
      }
    }
  }
}

# Use with Codex
codex exec -C /project --output-schema schema.json \
  "Find all security issues and output as structured JSON"
```

## Local/OSS Mode

Run with local models via Ollama:

```bash
# Requires Ollama installed with compatible model
codex exec --oss "Explain this code"
```

## Running in Sandbox

Test sandbox policies:

```bash
# Run a command through Codex's sandbox helper.
codex sandbox -C /project -- cat /etc/passwd

# Inspect available sandbox flags for the installed CLI.
codex sandbox --help
```
