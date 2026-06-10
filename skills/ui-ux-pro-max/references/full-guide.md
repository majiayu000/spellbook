# UI/UX Pro Max Full Guide

This file preserves the detailed guidance that previously lived in `SKILL.md`. Load it when the task needs concrete commands, templates, examples, or edge-case handling.

# UI/UX Pro Max - Design Intelligence

Comprehensive design guide for web and mobile applications. Contains compact reference tables for product patterns, visual styles, color palettes, typography, UX rules, chart choices, and technology stacks.

## When to Apply

Reference these guidelines when:
- Designing new UI components or pages
- Choosing color palettes and typography
- Reviewing code for UX issues
- Building landing pages or dashboards
- Implementing accessibility requirements

## Rule Categories by Priority

| Priority | Category | Impact | Domain |
|----------|----------|--------|--------|
| 1 | Accessibility | CRITICAL | `ux` |
| 2 | Touch & Interaction | CRITICAL | `ux` |
| 3 | Performance | HIGH | `ux` |
| 4 | Layout & Responsive | HIGH | `ux` |
| 5 | Typography & Color | MEDIUM | `typography`, `color` |
| 6 | Animation | MEDIUM | `ux` |
| 7 | Style Selection | MEDIUM | `style`, `product` |
| 8 | Charts & Data | LOW | `chart` |

## Quick Reference

### 1. Accessibility (CRITICAL)

- `color-contrast` - Minimum 4.5:1 ratio for normal text
- `focus-states` - Visible focus rings on interactive elements
- `alt-text` - Descriptive alt text for meaningful images
- `aria-labels` - aria-label for icon-only buttons
- `keyboard-nav` - Tab order matches visual order
- `form-labels` - Use label with for attribute

### 2. Touch & Interaction (CRITICAL)

- `touch-target-size` - Minimum 44x44px touch targets
- `hover-vs-tap` - Use click/tap for primary interactions
- `loading-buttons` - Disable button during async operations
- `error-feedback` - Clear error messages near problem
- `cursor-pointer` - Add cursor-pointer to clickable elements

### 3. Performance (HIGH)

- `image-optimization` - Use WebP, srcset, lazy loading
- `reduced-motion` - Check prefers-reduced-motion
- `content-jumping` - Reserve space for async content

### 4. Layout & Responsive (HIGH)

- `viewport-meta` - width=device-width initial-scale=1
- `readable-font-size` - Minimum 16px body text on mobile
- `horizontal-scroll` - Ensure content fits viewport width
- `z-index-management` - Define z-index scale (10, 20, 30, 50)

### 5. Typography & Color (MEDIUM)

- `line-height` - Use 1.5-1.75 for body text
- `line-length` - Limit to 65-75 characters per line
- `font-pairing` - Match heading/body font personalities

### 6. Animation (MEDIUM)

- `duration-timing` - Use 150-300ms for micro-interactions
- `transform-performance` - Use transform/opacity, not width/height
- `loading-states` - Skeleton screens or spinners

### 7. Style Selection (MEDIUM)

- `style-match` - Match style to product type
- `consistency` - Use same style across all pages
- `no-emoji-icons` - Use SVG icons, not emojis

### 8. Charts & Data (LOW)

- `chart-type` - Match chart type to data type
- `color-guidance` - Use accessible color palettes
- `data-table` - Provide table alternative for accessibility

## How to Use

Use the rules and reference tables below directly.

---

## How to Use This Skill

When user requests UI/UX work (design, build, create, implement, review, fix, improve), follow this workflow:

### Step 1: Analyze User Requirements

Extract key information from user request:
- **Product type**: SaaS, e-commerce, portfolio, dashboard, landing page, etc.
- **Style keywords**: minimal, playful, professional, elegant, dark mode, etc.
- **Industry**: healthcare, fintech, gaming, education, etc.
- **Stack**: React, Vue, Next.js, or default to `html-tailwind`

### Step 2: Generate Design System (REQUIRED)

Always start by synthesizing a compact design system from the rules in this
`SKILL.md`. Use the user's product type, industry, stack, and style keywords to
choose:

1. Product pattern and layout structure
2. Visual style and anti-patterns to avoid
3. Color palette direction and contrast rules
4. Typography direction
5. Motion, accessibility, and interaction checks

### Step 2b: Persist Design System (Master + Overrides Pattern)

When the work spans multiple pages or sessions, create a persistent design
system:

This creates:
- `design-system/MASTER.md` — Global Source of Truth with all design rules
- `design-system/pages/` — Folder for page-specific overrides

For a page-specific override, create `design-system/pages/<page-name>.md` with
only the page-specific deviations from `MASTER.md`.

**How hierarchical retrieval works:**
1. When building a specific page (e.g., "Checkout"), first check `design-system/pages/checkout.md`
2. If the page file exists, its rules **override** the Master file
3. If not, use `design-system/MASTER.md` exclusively

**Context-aware retrieval prompt:**
```
I am building the [Page Name] page. Please read design-system/MASTER.md.
Also check if design-system/pages/[page-name].md exists.
If the page file exists, prioritize its rules.
If not, use the Master rules exclusively.
Now, generate the code...
```

### Step 3: Supplement with Relevant Sections (as needed)

After getting the design system, consult the relevant sections below for extra
detail:

| Need | Domain | Use These Keywords |
|------|--------|--------------------|
| More style options | `style` | glassmorphism, minimalism, dark, brutalism, bento |
| Chart recommendations | `chart` | trend, comparison, real-time, funnel, distribution |
| UX best practices | `ux` | animation, accessibility, z-index, loading, keyboard |
| Alternative fonts | `typography` | elegant, luxury, playful, professional, data-dense |
| Landing structure | `landing` | hero, social proof, pricing, FAQ, conversion |

### Step 4: Stack Guidelines (Default: html-tailwind)

Use implementation-specific best practices. If user doesn't specify a stack,
**default to `html-tailwind`**.

Available stacks: `html-tailwind`, `react`, `nextjs`, `vue`, `svelte`, `swiftui`, `react-native`, `flutter`, `shadcn`, `jetpack-compose`

---

## Reference Index

### Available Domains

| Domain | Use For | Example Keywords |
|--------|---------|------------------|
| `product` | Product type recommendations | SaaS, e-commerce, portfolio, healthcare, beauty, service |
| `style` | UI styles, colors, effects | glassmorphism, minimalism, dark mode, brutalism |
| `typography` | Font pairings, Google Fonts | elegant, playful, professional, modern |
| `color` | Color palettes by product type | saas, ecommerce, healthcare, beauty, fintech, service |
| `landing` | Page structure, CTA strategies | hero, hero-centric, testimonial, pricing, social-proof |
| `chart` | Chart types, library recommendations | trend, comparison, timeline, funnel, pie |
| `ux` | Best practices, anti-patterns | animation, accessibility, z-index, loading |

### Available Stacks

| Stack | Focus |
|-------|-------|
| `html-tailwind` | Tailwind utilities, responsive, a11y (DEFAULT) |
| `react` | State, hooks, performance, patterns |
| `nextjs` | SSR, routing, images, API routes |
| `vue` | Composition API, Pinia, Vue Router |
| `svelte` | Runes, stores, SvelteKit |
| `swiftui` | Views, State, Navigation, Animation |
| `react-native` | Components, Navigation, Lists |
| `flutter` | Widgets, State, Layout, Theming |
| `shadcn` | shadcn/ui components, theming, forms, patterns |
| `jetpack-compose` | Composables, Modifiers, State Hoisting, Recomposition |

---

## Decision Reference

### Product Patterns

| Product Type | Layout Pattern | Visual Direction | Avoid |
|--------------|----------------|------------------|-------|
| SaaS / B2B | Sidebar or top nav, dense tables, filters, status summaries | Quiet surfaces, strong hierarchy, restrained accent color | Oversized marketing hero inside work screens |
| Dashboard / Admin | KPI row, searchable tables, charts, audit trail, empty states | Compact spacing, stable grid, readable numeric typography | Decorative cards that hide operational data |
| E-commerce | Product grid, filters, cart summary, trust markers, reviews | Product imagery first, clear price/CTA hierarchy | Low-contrast price or checkout controls |
| Beauty / Wellness | Service sections, booking CTA, testimonials, before/after imagery | Soft neutral base, botanical/rose/gold accent, elegant type | Thin low-contrast text and generic spa stock feel |
| Healthcare | Appointment flow, provider info, insurance/payment clarity | Calm blue/green palette, high contrast, plain labels | Playful styling that reduces trust |
| Portfolio / Agency | Case-study grid, project detail pages, proof and process | Strong type scale, real work imagery, focused accent | Abstract decoration without project evidence |
| Landing Page | Brand/product signal, primary CTA, proof, pricing or FAQ | First viewport shows offer and next section hint | Hero-only page with no visible proof path |

### Style, Color, And Typography

| Direction | Use | Color Guidance | Typography |
|-----------|-----|----------------|------------|
| Professional / Minimal | SaaS, finance, productivity | Neutral base plus blue, teal, or green accent | Inter, IBM Plex Sans, system UI |
| Elegant / Editorial | Luxury, wellness, portfolio | Warm neutral, charcoal, muted rose, gold, or botanical green | Playfair Display + Inter, Source Serif + Inter |
| Playful | Consumer apps, education, creator tools | Bright accent with generous white space; keep contrast AA | Nunito, Satoshi, system rounded |
| Dark Mode | Developer tools, media, dashboards | Near-black background, elevated surfaces, saturated accent | Inter or IBM Plex Sans; avoid thin weights |
| Glass / Bento | AI tools, premium marketing, dashboards | Translucent surfaces over stable solid backgrounds | Modern sans with tight hierarchy |
| Brutalist | Creative portfolios, launches | High-contrast monochrome plus one sharp accent | Archivo, Space Grotesk, Inter |

### Design System Source Rows

| Product / Industry | Structure | Palette | Type / Density | Interaction Notes |
|--------------------|-----------|---------|----------------|-------------------|
| Healthcare | Appointment, provider, insurance, results, and support flows | Blue/green, white, high-contrast neutrals | Clear sans, generous line-height, plain labels | Prioritize trust, readable errors, and visible privacy cues |
| Fintech | Account summary, transaction list, alerts, controls, audit trail | Deep neutral, blue/teal/green accent, semantic risk colors | Tabular numbers, compact labels, strong hierarchy | Avoid ambiguous money actions; confirm destructive transfers |
| Beauty / Wellness | Services, booking, proof, before/after, testimonials | Soft neutral with rose, gold, botanical green, or charcoal | Elegant display font plus readable sans | Keep CTAs obvious; do not let decorative type reduce contrast |
| Developer / AI Tool | Workspace, prompt/input, result panel, history, settings | Near-black or neutral light base with cyan/blue/green accent | Dense sans, monospace for code/data | Preserve keyboard flow, loading states, and copy/download actions |
| E-commerce | Product grid, filters, PDP, cart, checkout, trust markers | Product-led neutral with one CTA accent | Readable price, variant, and stock labels | Make cart and checkout states stable across breakpoints |
| Education / Creator | Lesson/content, progress, practice, feedback, community | Friendly accent, calm background, success/progress colors | Rounded sans, moderate density | Use clear progress and avoid hiding next actions |

### Landing Structure

| Cue | Section Order | CTA Strategy | Proof |
|-----|---------------|--------------|-------|
| Hero / offer | Brand or offer, value copy, primary CTA, next-section hint | One primary CTA; secondary only if it clarifies | Customer/logo row or concrete outcome near first viewport |
| Social proof | Hero, proof band, feature evidence, testimonial, CTA | Repeat CTA after proof | Logos, review snippets, usage metrics, case-study links |
| Pricing | Hero, value proof, plan comparison, FAQ, CTA | Keep plan CTA labels specific | Feature comparison, guarantee, support details |
| FAQ / conversion | Hero, objections, FAQ, final CTA | Match CTA to funnel stage | Risk reversal, security/compliance, support promise |
| Product launch | Product visual, benefits, demo, waitlist, proof | One signup/join action | Demo stills, roadmap, early-user quotes |

### Chart Choices

| Data Need | Use | Avoid | Notes |
|-----------|-----|-------|-------|
| Trend over time | Line or area chart | Pie chart | Show range, units, and empty/no-data state |
| Comparison | Bar chart | 3D chart | Sort by value unless chronology matters |
| Real-time metric | KPI + sparkline | Dense multi-series line | Include stale/loading indicators |
| Funnel | Funnel or stepped bar | Pie chart | Label conversion at each stage |
| Distribution | Histogram or box plot | Single KPI | Show sample size and outliers |
| Timeline | Timeline or Gantt | Table-only view | Pair with filters for long histories |
| Part-to-whole | Stacked bar or donut | Many-slice pie | Use only when categories are few and stable |

### HTML + Tailwind Guidance

| Area | Guidance |
|------|----------|
| Layout | Start mobile-first, use semantic landmarks, constrain content with `max-w-*`, and reserve dimensions for repeated cards, grids, and media. |
| Responsive | Prefer `grid-cols-1 md:grid-cols-*` and stable `min-h`/`aspect-*`; check 360px, 768px, and desktop widths. |
| Forms | Pair every input with a label, keep error text adjacent, use `aria-describedby`, and make submit/loading states explicit. |
| Components | Use Lucide/Heroicons for buttons, avoid card-in-card layouts, and keep hover/focus states from moving layout. |
| Assets | Use real product/place/person imagery when the user needs inspection; avoid purely atmospheric placeholders. |

### Stack Guidance

| Stack | Apply |
|-------|-------|
| `html-tailwind` | Use semantic HTML, mobile-first Tailwind breakpoints, constrained containers, fixed dimensions for toolbars/cards/grids, visible focus states, 44px touch targets, and static-friendly markup. Keep scripts small and avoid framework-only patterns. |
| `react` | Split stateful components by workflow, keep controlled forms explicit, memoize only proven hot paths, and preserve accessible labels for icon buttons. |
| `nextjs` | Use framework image/link primitives where available, keep server/client boundaries explicit, and avoid putting interactive-only code in server components. |
| `vue` / `svelte` | Keep reactive state local until shared state is truly needed; preserve semantic HTML and predictable transitions. |
| `shadcn` | Use tokens and component variants consistently; do not stack cards inside cards or override primitives ad hoc. |
| `swiftui` | Compose small `View`s, keep `@State` local, use `NavigationStack`, respect safe areas, and prefer system controls before custom gestures. |
| `react-native` | Use platform components, `FlatList` for long lists, navigation-safe screens, explicit loading/error states, and 44px minimum touch targets. |
| `flutter` | Use Material/Cupertino widgets deliberately, keep state ownership clear, rely on constraints for layout, and centralize theme tokens. |
| `jetpack-compose` | Hoist state, keep composables pure, use stable keys in lazy lists, avoid unnecessary recomposition, and respect Material touch targets. |

---

## Example Workflow

**User request:** "Làm landing page cho dịch vụ chăm sóc da chuyên nghiệp"

### Step 1: Analyze Requirements
- Product type: Beauty/Spa service
- Style keywords: elegant, professional, soft
- Industry: Beauty/Wellness
- Stack: html-tailwind (default)

### Step 2: Generate Design System (REQUIRED)

Create a compact design system for "Serenity Spa" with pattern, style, colors,
typography, effects, and anti-patterns.

### Step 3: Supplement with Relevant Sections (as needed)

Use the UX, product, style, color, and typography tables when animation,
accessibility, font direction, or page structure needs more detail.

### Step 4: Stack Guidelines

Apply the `html-tailwind` stack guidelines for layout, responsive behavior, and
forms.

**Then:** Synthesize the design system, relevant sections, and stack guidance before implementing the design.

---

## Tips for Better Results

1. **Be specific with keywords** - "healthcare SaaS dashboard" > "app"
2. **Check multiple reference rows** - Product, industry, and style rows often combine
3. **Combine domains** - Style + Typography + Color = Complete design system
4. **Always check UX** - Use "animation", "z-index", and "accessibility" as cues for common issues
5. **Use the stack section** - Apply implementation-specific best practices
6. **Iterate** - If the first reference row doesn't match, try adjacent keywords

---

## Common Rules for Professional UI

These are frequently overlooked issues that make UI look unprofessional:

### Icons & Visual Elements

| Rule | Do | Don't |
|------|----|----- |
| **No emoji icons** | Use SVG icons (Heroicons, Lucide, Simple Icons) | Use emojis like 🎨 🚀 ⚙️ as UI icons |
| **Stable hover states** | Use color/opacity transitions on hover | Use scale transforms that shift layout |
| **Correct brand logos** | Research official SVG from Simple Icons | Guess or use incorrect logo paths |
| **Consistent icon sizing** | Use fixed viewBox (24x24) with w-6 h-6 | Mix different icon sizes randomly |

### Interaction & Cursor

| Rule | Do | Don't |
|------|----|----- |
| **Cursor pointer** | Add `cursor-pointer` to all clickable/hoverable cards | Leave default cursor on interactive elements |
| **Hover feedback** | Provide visual feedback (color, shadow, border) | No indication element is interactive |
| **Smooth transitions** | Use `transition-colors duration-200` | Instant state changes or too slow (>500ms) |

### Light/Dark Mode Contrast

| Rule | Do | Don't |
|------|----|----- |
| **Glass card light mode** | Use `bg-white/80` or higher opacity | Use `bg-white/10` (too transparent) |
| **Text contrast light** | Use `#0F172A` (slate-900) for text | Use `#94A3B8` (slate-400) for body text |
| **Muted text light** | Use `#475569` (slate-600) minimum | Use gray-400 or lighter |
| **Border visibility** | Use `border-gray-200` in light mode | Use `border-white/10` (invisible) |

### Layout & Spacing

| Rule | Do | Don't |
|------|----|----- |
| **Floating navbar** | Add `top-4 left-4 right-4` spacing | Stick navbar to `top-0 left-0 right-0` |
| **Content padding** | Account for fixed navbar height | Let content hide behind fixed elements |
| **Consistent max-width** | Use same `max-w-6xl` or `max-w-7xl` | Mix different container widths |

---

## Pre-Delivery Checklist

Before delivering UI code, verify these items:

### Visual Quality
- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] Brand logos are correct (verified from Simple Icons)
- [ ] Hover states don't cause layout shift
- [ ] Use theme colors directly (bg-primary) not var() wrapper

### Interaction
- [ ] All clickable elements have `cursor-pointer`
- [ ] Hover states provide clear visual feedback
- [ ] Transitions are smooth (150-300ms)
- [ ] Focus states visible for keyboard navigation

### Light/Dark Mode
- [ ] Light mode text has sufficient contrast (4.5:1 minimum)
- [ ] Glass/transparent elements visible in light mode
- [ ] Borders visible in both modes
- [ ] Test both modes before delivery

### Layout
- [ ] Floating elements have proper spacing from edges
- [ ] No content hidden behind fixed navbars
- [ ] Responsive at 375px, 768px, 1024px, 1440px
- [ ] No horizontal scroll on mobile

### Accessibility
- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Color is not the only indicator
- [ ] `prefers-reduced-motion` respected
