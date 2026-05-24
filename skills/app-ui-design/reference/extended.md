# app-ui-design Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Accessibility Checklist`.

## Accessibility Checklist

### Visual Accessibility

```markdown
## Vision Accessibility Checklist

### Color & Contrast
- [ ] Text contrast ≥ 4.5:1 (normal), ≥ 3:1 (large)
- [ ] UI component contrast ≥ 3:1
- [ ] Color is not the only indicator (use icons, text)
- [ ] Works for colorblind users (test with simulators)

### Text & Typography
- [ ] Base font size ≥ 16px
- [ ] Supports Dynamic Type (iOS) / Font Scaling (Android)
- [ ] Line height ≥ 1.4× for body text
- [ ] Text can scale to 200% without loss of content

### Focus & Navigation
- [ ] Visible focus indicators
- [ ] Logical tab order
- [ ] Skip links for repetitive content
- [ ] Keyboard-accessible (external keyboards)
```

### Motor Accessibility

```markdown
## Motor Accessibility Checklist

### Touch Targets
- [ ] Minimum size: 44×44pt (iOS) / 48×48dp (Android)
- [ ] Spacing between targets ≥ 8px
- [ ] No time-limited interactions (or extendable)
- [ ] Alternative to drag gestures (WCAG 2.2)

### Interaction
- [ ] Single-tap for all actions (no double-tap required)
- [ ] Undo available for destructive actions
- [ ] No precision requirements (fine motor)
- [ ] Support for Switch Control / Voice Access
```

### Screen Reader

```markdown
## Screen Reader Checklist

### Content
- [ ] All images have descriptive alt text
- [ ] Decorative images have empty alt (alt="")
- [ ] Buttons/links have descriptive labels
- [ ] Form inputs have associated labels
- [ ] Headings used for structure (not styling)

### Navigation
- [ ] Logical reading order
- [ ] Meaningful link text (not "click here")
- [ ] State changes announced
- [ ] Modal focus properly trapped
- [ ] Custom components have ARIA roles
```

---

## Component Patterns

### Button Design

```markdown
## Button Hierarchy

### Primary Button
- Most important action on screen
- Filled/solid style
- High contrast
- Only ONE per view section

### Secondary Button
- Alternative actions
- Outlined or tonal style
- Medium contrast

### Tertiary Button
- Low-priority actions
- Text-only or ghost style
- Subtle appearance

### Destructive Button
- Delete, remove, cancel
- Red/error color
- Requires confirmation for important data

### Button States
- Default → Normal appearance
- Pressed → Scale down, darker
- Disabled → 50% opacity, no interaction
- Loading → Spinner, disabled
```

### Form Design

```markdown
## Form Best Practices

### Input Fields
- Clear labels (above input, not placeholder-only)
- Helpful placeholder text
- Error states with specific messages
- Success validation feedback
- Appropriate keyboard types

### Layout
- Single column for mobile
- Group related fields
- Logical tab order
- Primary action at bottom
- Sticky submit button if long form

### Validation
- Inline validation (on blur or after input)
- Clear error messages with fix suggestions
- Don't clear fields on error
- Mark required fields clearly
```

### Navigation Patterns

```markdown
## Mobile Navigation

### Bottom Navigation (Primary)
- 3-5 destinations
- Icons + labels
- Active state indicator
- Consistent across app

### Tab Bar (Content Switching)
- Horizontal tabs for related content
- Swipe between tabs
- Indicator for active tab

### Navigation Stack
- Clear back navigation
- Meaningful titles
- Breadcrumbs for deep hierarchies

### Gestures
- Swipe back (iOS standard)
- Pull to refresh
- Swipe actions on list items
- Long press for context menus
```

---

## Design Process

### Workflow

```markdown
## App Design Workflow

1. Research & Discovery
   ├── User research and personas
   ├── Competitor analysis
   ├── Platform guidelines review
   └── Technical constraints

2. Information Architecture
   ├── User flows
   ├── Navigation structure
   ├── Content hierarchy
   └── Sitemap

3. Design System Setup
   ├── Color tokens
   ├── Typography scale
   ├── Spacing system
   ├── Component library
   └── Icon set

4. Wireframing
   ├── Low-fidelity layouts
   ├── Flow validation
   ├── Stakeholder review
   └── Iteration

5. Visual Design
   ├── High-fidelity mockups
   ├── Interaction design
   ├── Prototype creation
   └── Accessibility audit

6. Handoff & Implementation
   ├── Design specs documentation
   ├── Asset export
   ├── Developer collaboration
   └── QA review
```

---

## Anti-Patterns to Avoid

```markdown
## Common Mistakes

### Visual Design
❌ Using more than 3 fonts
❌ Inconsistent spacing values
❌ Low contrast text
❌ Overly complex gradients/effects
❌ Ignoring safe areas

### Interaction Design
❌ Hidden navigation
❌ Gesture-only actions without alternatives
❌ Tiny touch targets
❌ No loading states
❌ Confusing back navigation

### Accessibility
❌ Placeholder-only labels
❌ Color-only information
❌ Auto-playing media
❌ Timed interactions without extension
❌ Missing screen reader labels

### Platform
❌ iOS patterns on Android (or vice versa)
❌ Custom controls when standard works
❌ Ignoring platform conventions
❌ Not supporting dark mode
```

---

## Checklist

### Before Design
- [ ] Reviewed platform guidelines (iOS HIG / Material Design 3)
- [ ] Defined target users and their needs
- [ ] Analyzed competitor apps
- [ ] Identified accessibility requirements
- [ ] Set up design system tokens

### During Design
- [ ] Following 8-point grid
- [ ] Using defined color tokens
- [ ] Typography from scale only
- [ ] Touch targets meet minimum size
- [ ] Contrast ratios verified
- [ ] All states designed (default, pressed, disabled, error)
- [ ] Dark mode variant created

### Before Handoff
- [ ] Accessibility audit completed
- [ ] Tested with screen reader
- [ ] Verified on multiple screen sizes
- [ ] Motion/animation documented
- [ ] Design specs annotated
- [ ] Assets exported correctly

---

## Tools & Resources

### Design Tools
- Figma → Industry standard, collaboration
- Sketch → Mac-native, established ecosystem
- Adobe XD → Adobe integration

### Prototyping
- Figma Prototyping → Built-in, quick
- ProtoPie → Advanced interactions
- Principle → Mac, detailed animations

### Accessibility Testing
- Stark → Contrast checker (Figma plugin)
- Color Oracle → Colorblind simulator
- VoiceOver (iOS) / TalkBack (Android)

### Platform Resources
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Google Material Design](https://m3.material.io/)
- [WCAG 2.2 Guidelines](https://www.w3.org/TR/WCAG22/)

---

## See Also

- [reference/ios-guidelines.md](reference/ios-guidelines.md) — iOS Human Interface Guidelines summary
- [reference/material-design.md](reference/material-design.md) — Material Design 3 summary
- [reference/accessibility.md](reference/accessibility.md) — WCAG 2.2 mobile checklist
- [reference/color-theory.md](reference/color-theory.md) — Color selection and contrast
- [templates/design-system-template.md](templates/design-system-template.md) — Design system starter

---

## Sources

Research based on 2025 best practices from:
- [Mobile App UI Design Best Practices 2025](https://wezom.com/blog/mobile-app-design-best-practices-in-2025)
- [UI/UX Design Trends 2025](https://www.chopdawg.com/ui-ux-design-trends-in-mobile-apps-for-2025/)
- [Mobile App Design Trends 2025](https://fuselabcreative.com/mobile-app-design-trends-for-2025/)
- [Accessibility in UI/UX Design 2025](https://orbix.studio/blogs/accessibility-uiux-design-best-practices-2025)
- [iOS Design Guidelines 2025](https://www.bairesdev.com/blog/ios-design-guideline/)
- [Mobile App Design Guidelines iOS/Android](https://medium.com/@CarlosSmith24/mobile-app-design-guidelines-for-ios-and-android-in-2025-82e83f0b942b)
