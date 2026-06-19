# Repo Agent Context Standard

Use this reference when scoring a repository's agent-readable context.

## Target Shape

| Layer | Purpose | Good Size | Contents |
|---|---|---:|---|
| Top-level router | Tell agents where to start and what must be obeyed | 80-150 lines | Scope, build/test commands, required workflows, high-risk rules |
| Skills | Repeatable procedures | 40-200 lines each | One task workflow, concrete steps, when to read references |
| Specs | Change-specific contracts | 40-200 lines normally | PRODUCT behavior invariants, TECH implementation and validation |
| References | Detailed context | Any size | Architecture notes, examples, schemas, historical context |

## Scoring Rubric

Score each category 0-2.

| Category | 0 | 1 | 2 |
|---|---|---|---|
| Top-level routing | Missing or unclear | Exists but noisy or incomplete | Short, scoped, points to deeper docs |
| Progressive disclosure | Everything in one file | Some splitting but unclear loading | Router, skills, specs, references are distinct |
| Procedural workflows | Vague advice | Partial checklist | Concrete ordered steps for common tasks |
| Decision gates | No "when to spec/test/escalate" rules | Some prose guidance | Tables or clear gates with defaults |
| Production examples | Pseudocode or none | Some real paths | Real repo paths, commands, snippets |
| Spec quality | No specs for complex work | Specs exist but mix product/tech | PRODUCT behavior and TECH implementation are separate |
| Validation mapping | "Run tests" only | Commands listed | Behavior invariants map to tests/artifacts |
| Staleness risk | Contradicts code or commands | Unknown freshness | Current, cited, and easy to verify |

Suggested interpretation:

- 14-16: healthy; avoid adding ceremony.
- 10-13: usable; make one or two focused improvements.
- 6-9: fragile; add a router or split overloaded docs.
- 0-5: missing core context; scaffold minimal structure before major agent work.

## Good Top-Level Router

A good `AGENTS.md` or repo-equivalent:

- states its scope
- lists exact build, typecheck, test, and lint commands
- says when specs are required
- points to task skills or deeper docs
- names high-risk rules, such as auth, migrations, generated files, or UI verification
- avoids long architecture explanations
- avoids repeating README content unless agents need a different workflow

## Good Product Spec

`PRODUCT.md` is the source of truth for behavior. It should:

- describe the consumer perspective, not implementation
- use numbered, testable behavior invariants
- include default, empty, loading, error, permission, cancellation, race, and accessibility states when relevant
- define non-goals when scope can drift
- avoid validation sections if the repo uses `TECH.md` for validation mapping

## Good Tech Spec

`TECH.md` is the implementation contract. It should:

- cite current code and files with line references when practical
- explain current state before proposed changes
- list modules, types, APIs, state, and data flow that will change
- call out rejected alternatives when there is a real tradeoff
- map product behavior numbers to tests, manual checks, screenshots, or release gates
- stay current as implementation changes

## Red Flags

- a 300+ line top-level instruction file with mixed rules, workflows, architecture, and examples
- many "do not" rules without "use this instead"
- spec templates that produce boilerplate "None" sections
- product specs that prescribe internal types
- tech specs that ignore current code and read like generic architecture
- generated or dependency-modified high-context files
- multiple instruction files with overlapping scope and no precedence note
- stale commands or paths that fail when run
