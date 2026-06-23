# Registry Directory Contract

The registry is derived from skill source files and tag overrides. Treat this
directory as generated metadata unless you are editing a declared source of
truth.

## Sources Of Truth

| Need | Edit |
|---|---|
| Skill name or description | The skill's frontmatter in `skills/` |
| Manual tag correction | `registry/tag_overrides.yml` |
| Category, discovery, render, or validation behavior | `scripts/validate_skills.py` |
| Generated registry payload | Regenerate with `python3 scripts/validate_skills.py --write` |

## Rules

- Do not manually edit `registry/skills.json` or `registry/tags.json`.
- Do not invent registry fields. Add validator, renderer, docs, and tests for
  any real schema change.
- Keep generated output deterministic and sorted so diffs stay reviewable.
- If `docs/skill-registry.md` is stale, regenerate it through the validator
  instead of editing it directly.

## Validation

Run after registry source changes:

```bash
python3 scripts/validate_skills.py --write
python3 scripts/validate_skills.py --check
```

If only inspecting registry state, run `python3 scripts/validate_skills.py --check`.
