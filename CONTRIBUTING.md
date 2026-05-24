# Contributing to claude-arsenal

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/majiayu000/claude-arsenal.git
cd claude-arsenal
python3 scripts/validate_skills.py --check
bash -n install.sh
```

## Guidelines

- Follow existing code style
- Add tests for new features
- Run `python3 scripts/validate_skills.py --check` before opening a PR
- Commit messages: `<type>: <description>` (feat/fix/refactor/docs/test/chore)

## Adding or Updating a Skill

1. Add the new skill directory or `*.SKILL.md` file under `skills/`.
2. Map the skill to a category in `CATEGORY_BY_NAME` inside `scripts/validate_skills.py`.
3. Regenerate registry artifacts:
   ```bash
   python3 scripts/validate_skills.py --write
   ```
   This updates `registry/skills.json`, `registry/tags.json`, and `docs/skill-registry.md`.
4. If the keyword heuristic mis-tags or under-tags the skill, add a curated entry to
   `registry/tag_overrides.yml` (overrides extend, never replace, the auto-detected tags).
5. Update the skill counts in `README.md`, `README_CN.md`, and `install.sh` if a new
   skill was added.
6. Verify search behaves as expected:
   ```bash
   python3 scripts/validate_skills.py search <your-skill-name>
   ```

## Pull Requests

1. Fork the repo and create your branch from `main`
2. Ensure tests pass
3. Submit a PR with a clear description
