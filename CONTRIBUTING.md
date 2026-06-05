# Contributing to claude-arsenal

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/majiayu000/claude-arsenal.git
cd claude-arsenal
python3 scripts/validate_skills.py --check
python3 scripts/audit_skill_quality.py
bash -n install.sh
```

## Guidelines

- Follow existing code style
- Add tests for new features
- Run `python3 scripts/validate_skills.py --check` before opening a PR
- Run `python3 scripts/audit_skill_quality.py <skill-name>` when adding or materially updating a skill
- Commit messages: `<type>: <description>` (feat/fix/refactor/docs/test/chore)

## Adding or Updating a Skill

1. Add the new skill directory or `*.SKILL.md` file under `skills/`.
2. Pick one primary skill type and follow [Skill Quality Playbook](./docs/skill-quality-playbook.md).
3. Write the `description` as a model-facing trigger: include "Use when" style intent, user phrasing, symptoms, and near-boundary context when relevant.
4. For mature workflow skills, add gotchas and concrete verification signals. If the skill has `references/`, `scripts/`, `assets/`, `templates/`, or `evals/`, point to them from `SKILL.md`.
5. Map the skill to a category in `CATEGORY_BY_NAME` inside `scripts/validate_skills.py`.
6. Regenerate registry artifacts:
   ```bash
   python3 scripts/validate_skills.py --write
   ```
   This updates `registry/skills.json`, `registry/tags.json`, and `docs/skill-registry.md`.
7. If the keyword heuristic mis-tags or under-tags the skill, add a curated entry to
   `registry/tag_overrides.yml` (overrides extend, never replace, the auto-detected tags).
8. Update the skill counts in `README.md`, `README_CN.md`, and `install.sh` if a new
   skill was added.
9. Verify search and quality signals behave as expected:
   ```bash
   python3 scripts/validate_skills.py search <your-skill-name>
   python3 scripts/audit_skill_quality.py <your-skill-name>
   ```

## Pull Requests

1. Fork the repo and create your branch from `main`
2. Ensure tests pass
3. Submit a PR with a clear description
