# prd-master Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Agile Requirements Management`.

## Agile Requirements Management

### Backlog Structure

```
Initiatives    — Large strategic bets (12-24 months)
                 Example: "Expand to enterprise market"

Epics          — Major features (3-6 months)
                 Example: "SSO and enterprise authentication"

Stories        — User-facing functionality (1-2 weeks)
                 Example: "SAML login for enterprise users"

Tasks          — Technical implementation (1-3 days)
                 Example: "Set up SAML provider integration"

Bugs           — Defects to fix (varies)
                 Example: "Login fails on Safari 17"
```

### Backlog Refinement

```
Cadence: Weekly, 1 hour, mid-sprint

Activities:
1. Groom upcoming stories
   - Add acceptance criteria
   - Break down large stories
   - Clarify unknowns

2. Estimate effort
   - Planning poker or t-shirt sizes
   - Identify technical risks

3. Prioritize
   - Apply RICE/MoSCoW
   - Consider dependencies

4. Definition of Ready
   - [ ] User story is clear
   - [ ] Acceptance criteria defined
   - [ ] Dependencies identified
   - [ ] Designs available (if needed)
   - [ ] Estimated by team
   - [ ] No blocking questions
```

### Requirements Traceability

```
For regulated industries (healthcare, finance):

Requirement ID → User Story → Test Case → Implementation

Example:
REQ-AUTH-001: "System shall enforce 2FA for admin users"
  ↓
US-123: "As an admin, I want 2FA to secure my account"
  ↓
TEST-456: "Verify admin cannot login without 2FA code"
  ↓
PR-789: Implementation in auth-service

Use tools: Jira, Azure DevOps, Modern Requirements
```

---

## Writing Best Practices

### Be Specific and Quantifiable

```
❌ Vague: "The app should be fast"
✓ Specific: "Page load time < 2s on 4G, < 500ms on WiFi (p95)"

❌ Vague: "The product should be lightweight"
✓ Specific: "Weight < 500g including battery and accessories"

❌ Vague: "Support many users"
✓ Specific: "Handle 10,000 concurrent users with 99.9% uptime"
```

### Focus on Problem, Not Solution

```
❌ Solution-focused:
"Add a search bar to the navigation menu"

✓ Problem-focused:
"Users can't find products quickly (exit rate 40% on catalog page).
They need a way to filter 1000+ products by attributes."

→ This allows the team to explore multiple solutions:
  - Search bar
  - Smart filters
  - Category navigation
  - AI recommendations
```

### Include Context and Rationale

```
For each decision, explain WHY:

"We're building password reset via email (not SMS) because:
- 95% of users have verified email (only 60% have phone)
- Email is free, SMS costs $0.02 per message
- Competitors (Stripe, GitHub) use email
- SMS has security concerns (SIM swapping)"
```

### Keep it Concise

```
Use short paragraphs, bullet points, tables

❌ Wall of text:
"The user authentication system should support multiple authentication
methods including email and password which is the default method that
most users will use but we should also support social login via Google
and GitHub which are commonly requested features and will reduce friction
during signup and we should also consider adding two-factor authentication
for security..."

✓ Structured:
**Authentication Methods:**
- Email + Password (default, 80% of users)
- Social login (Google, GitHub)
- Two-factor authentication (optional, security-conscious users)

**Rationale:**
- Reduce signup friction (social login)
- Support security best practices (2FA)
- Follow industry standards
```

---

## Collaboration & Tools

### Modern PRD Tools

| Tool | Best For | Integration |
|------|----------|-------------|
| Notion | Customizable templates, collaboration | Slack, GitHub |
| Confluence | Enterprise, Jira integration | Jira, BitBucket |
| Productboard | User feedback integration, roadmaps | Jira, Intercom |
| Linear | Engineering-focused, fast workflow | GitHub, Slack |
| Coda | Interactive docs, automation | 3000+ integrations |
| Google Docs | Simple, universal access | Drive, Sheets |

### Version Control

```
✓ Use versioning: v1.0, v1.1, v2.0
✓ Track changes with comments
✓ Maintain changelog at top of doc
✓ Lock old versions (read-only)
✓ Link to source of truth (Figma, GitHub)

Example Changelog:
---
## Changelog
**v2.1** (2025-03-15)
- Added SAML authentication requirement
- Updated success metrics based on A/B test results

**v2.0** (2025-03-01)
- Simplified scope after engineering review
- Removed SMS authentication (moved to v3)

**v1.0** (2025-02-15)
- Initial PRD
---
```

### Stakeholder Review

```
Review Process:
1. Draft PRD (PM)
2. Technical feasibility review (Engineering)
3. Design review (Design)
4. Legal/compliance review (if needed)
5. Stakeholder sign-off (Leadership)
6. Publish and socialize

Use RACI matrix:
- Responsible: PM (writes PRD)
- Accountable: Product Lead (final approval)
- Consulted: Engineering, Design, Marketing
- Informed: Leadership, Support, Sales
```

---

## Checklist

```markdown
## PRD Quality Check

### Content
- [ ] Problem clearly stated
- [ ] Goals are measurable and quantifiable
- [ ] Target users and personas defined
- [ ] User stories follow INVEST criteria
- [ ] Acceptance criteria use Given-When-Then
- [ ] Out of scope explicitly listed
- [ ] Success metrics defined (leading + lagging)

### Technical
- [ ] Non-functional requirements included (performance, security)
- [ ] Dependencies and integrations identified
- [ ] API contracts defined (if applicable)
- [ ] Data model changes documented
- [ ] Technical risks and mitigations listed

### Design & UX
- [ ] Link to design files (Figma, Sketch)
- [ ] Accessibility requirements (WCAG 2.2 AA)
- [ ] Mobile and desktop specs
- [ ] Error states and edge cases designed

### Launch
- [ ] Rollout strategy defined (phased, A/B test, feature flags)
- [ ] Monitoring and alerts planned
- [ ] Rollback plan documented
- [ ] Documentation and training planned

### Stakeholders
- [ ] Engineering reviewed and estimated
- [ ] Design reviewed and approved
- [ ] Legal/compliance reviewed (if needed)
- [ ] Leadership approved
- [ ] All open questions resolved or acknowledged
```

---

## See Also

- [reference/user-stories.md](reference/user-stories.md) — User story writing guide
- [reference/prioritization.md](reference/prioritization.md) — Prioritization frameworks
- [reference/acceptance-criteria.md](reference/acceptance-criteria.md) — BDD and acceptance criteria patterns
- [templates/prd-template.md](templates/prd-template.md) — Copy-paste PRD template
