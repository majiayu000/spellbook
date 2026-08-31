# Spellbook UI for Codex

This is a focused Codex plugin pilot containing exactly four Spellbook skills:

- `frontend-design`
- `app-ui-design`
- `ui-design-system`
- `figma-to-react`

The files under `skills/` are packaged copies of the canonical catalog skills
at the repository root. Each directory includes the companion references,
scripts, templates, or evals used by that skill.

## Validate locally

From the Spellbook repository root, use the validator shipped with Codex's
`plugin-creator` skill:

```bash
PLUGIN_CREATOR="${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator"
python3 "$PLUGIN_CREATOR/scripts/validate_plugin.py" plugins/spellbook-ui
```

Then run the normal Spellbook checks:

```bash
python3 scripts/validate_skills.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q
```

## Install for a local pilot

Codex installs plugins from configured marketplace snapshots. This repository
does not publish a Codex marketplace entry yet. To test without changing that
distribution claim, create a temporary local marketplace with the supported
plugin creator, replace its placeholder plugin with this validated source, and
install from that local marketplace:

```bash
PLUGIN_CREATOR="${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator"
SPELLBOOK_ROOT="$(pwd)"
PILOT_ROOT="$(mktemp -d)"

python3 "$PLUGIN_CREATOR/scripts/create_basic_plugin.py" spellbook-ui \
  --path "$PILOT_ROOT/plugins" \
  --marketplace-path "$PILOT_ROOT/marketplace.json" \
  --marketplace-name spellbook-local \
  --with-skills \
  --with-marketplace
rsync -a --delete "$SPELLBOOK_ROOT/plugins/spellbook-ui/" \
  "$PILOT_ROOT/plugins/spellbook-ui/"
codex plugin marketplace add "$PILOT_ROOT"
codex plugin add spellbook-ui@spellbook-local
```

Start a new Codex thread after installation so the plugin skills are loaded.
Remove the temporary marketplace when the pilot is finished:

```bash
codex plugin remove spellbook-ui
codex plugin marketplace remove spellbook-local
```

These are local development instructions. They do not imply publication in an
OpenAI or Spellbook marketplace.
