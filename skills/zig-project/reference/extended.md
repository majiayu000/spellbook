# zig-project Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Checklist`.

## Checklist

```markdown
## Project Setup
- [ ] build.zig configured
- [ ] build.zig.zon with metadata
- [ ] Source in src/ directory

## Architecture
- [ ] Explicit allocators everywhere
- [ ] No global state
- [ ] Error sets defined
- [ ] errdefer for cleanup

## Quality
- [ ] Tests with std.testing
- [ ] Memory leak detection in tests
- [ ] zig fmt applied
- [ ] Comptime validation where appropriate

## Build
- [ ] Debug and Release configs
- [ ] Cross-compilation targets
- [ ] Test step defined
```

---

## See Also

- [reference/architecture.md](reference/architecture.md) — Project structure patterns
- [reference/tech-stack.md](reference/tech-stack.md) — Libraries and tools
- [reference/patterns.md](reference/patterns.md) — Zig idioms and patterns
