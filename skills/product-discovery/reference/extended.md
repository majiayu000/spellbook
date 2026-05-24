# product-discovery Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Integrating Discovery with Delivery`.

## Integrating Discovery with Delivery

### Discovery Kanban

```markdown
## Discovery Board Columns

┌─────────────┬──────────────┬──────────────┬─────────────┐
│ OPPORTUNITIES│ ASSUMPTIONS  │  EXPERIMENTS │  VALIDATED  │
│             │              │              │             │
│ Customer    │ Riskiest     │ Running      │ Ready to    │
│ needs we've │ assumptions  │ tests        │ build       │
│ identified  │ to validate  │              │             │
└─────────────┴──────────────┴──────────────┴─────────────┘

## Flow
1. Opportunities flow from research
2. Solutions generate assumptions to test
3. Experiments validate/invalidate assumptions
4. Validated solutions enter delivery backlog
```

### Definition of Ready

Before moving from discovery to delivery:

```markdown
## Discovery Checklist
- [ ] Customer problem validated (5+ interviews)
- [ ] Solution tested with prototype (10+ users)
- [ ] Success metrics defined and measurable
- [ ] Technical feasibility confirmed by engineering
- [ ] Business case approved (revenue/retention impact)
- [ ] Design mocks completed and tested
- [ ] Open questions resolved or explicitly acknowledged
- [ ] Story broken into shippable increments
```

---

## Common Anti-Patterns

### What NOT to Do

```markdown
## ✗ Solution-First Discovery
Starting with "We should build X" then finding evidence to support it
→ Instead: Start with outcome and problem, explore multiple solutions

## ✗ Episodic Research
Doing discovery as a phase, then stopping when development starts
→ Instead: Continuous weekly discovery throughout product lifecycle

## ✗ Confirmation Bias
Only talking to users who will validate your ideas
→ Instead: Seek disconfirming evidence, talk to churned users

## ✗ Fake Validation
Asking "Would you use this?" and trusting the answer
→ Instead: Test with realistic prototypes, measure actual behavior

## ✗ Analysis Paralysis
Endless research without ever shipping
→ Instead: Define upfront what evidence is "enough" to move forward

## ✗ Building for Everyone
Trying to solve for all users at once
→ Instead: Focus on specific segment, nail it, then expand

## ✗ Ignoring Weak Signals
Dismissing early negative feedback as "just a few users"
→ Instead: Treat complaints as early warning signs, investigate
```

---

## See Also

- [reference/market-research.md](reference/market-research.md) — TAM/SAM/SOM, Porter's Five Forces
- [reference/user-research.md](reference/user-research.md) — Interview guides, survey methods, ethnography
- [reference/competitive-analysis.md](reference/competitive-analysis.md) — Competitive frameworks and analysis
- [reference/opportunity-frameworks.md](reference/opportunity-frameworks.md) — JTBD, Kano, Value Proposition Canvas
- [templates/discovery-template.md](templates/discovery-template.md) — Product discovery document template
