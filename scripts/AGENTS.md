# Scripts Directory Contract

Scripts are operational entry points for validation, registry generation, and
quality audits. Prefer small, explicit changes that preserve existing command
interfaces.

## Before Editing

- Search for an existing parser, renderer, validator, or helper before adding a
  new one.
- Inspect tests and callers with `rg <function-or-command>`.
- For skill metadata behavior, read `scripts/validate_skills.py` before changing
  generated files.

## Rules

- Do not silently swallow exceptions. Return clear validation errors or fail
  with a useful message.
- Do not parse structured files with ad hoc string slicing when an existing
  parser or standard library parser is available.
- Preserve deterministic output ordering for generated files.
- Keep command-line behavior backward compatible unless the user explicitly asks
  for a breaking change.
- Avoid public helpers that are only used once.
- Do not hardcode credentials, local-only absolute paths, or private machine
  state.

## Validation

- Python syntax check:

```bash
python3 -m py_compile scripts/*.py
```

- Skill and registry behavior:

```bash
python3 scripts/validate_skills.py --check
```

- Skill quality audit behavior:

```bash
python3 scripts/audit_skill_quality.py
```

Run narrower targeted tests when they exist, then the relevant workflow command
that proves the changed script behavior.
