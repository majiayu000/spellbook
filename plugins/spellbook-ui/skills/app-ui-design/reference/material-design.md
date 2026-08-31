# Material Design 3 Guidelines

Quick reference for Android app design following Google's Material Design 3 (2025).

## Design Principles

### Material You
- **Personal**: Adapts to user preferences
- **Adaptive**: Responds to device and context
- **Expressive**: Communicates brand and emotion

### Core Concepts
- Surfaces over layers
- Motion with meaning
- Color from user wallpaper
- Accessibility built-in

## Typography

### Roboto Font Family

| Role | Size | Weight | Line Height | Tracking |
|------|------|--------|-------------|----------|
| Display Large | 57sp | Regular | 64sp | -0.25sp |
| Display Medium | 45sp | Regular | 52sp | 0sp |
| Display Small | 36sp | Regular | 44sp | 0sp |
| Headline Large | 32sp | Regular | 40sp | 0sp |
| Headline Medium | 28sp | Regular | 36sp | 0sp |
| Headline Small | 24sp | Regular | 32sp | 0sp |
| Title Large | 22sp | Regular | 28sp | 0sp |
| Title Medium | 16sp | Medium | 24sp | 0.15sp |
| Title Small | 14sp | Medium | 20sp | 0.1sp |
| Body Large | 16sp | Regular | 24sp | 0.5sp |
| Body Medium | 14sp | Regular | 20sp | 0.25sp |
| Body Small | 12sp | Regular | 16sp | 0.4sp |
| Label Large | 14sp | Medium | 20sp | 0.1sp |
| Label Medium | 12sp | Medium | 16sp | 0.5sp |
| Label Small | 11sp | Medium | 16sp | 0.5sp |

### Font Scaling

```kotlin
// Support system font scaling
Text(
    text = "Hello",
    style = MaterialTheme.typography.bodyLarge
)
```

## Color System

### Dynamic Color (Material You)

Material You extracts colors from user's wallpaper:

```
┌─────────────────────────────────────────┐
│            User Wallpaper                │
│               🖼️                         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Primary    Secondary   Tertiary        │
│  ████████   ████████   ████████         │
│                                         │
│  Neutral    NeutralVar  Error           │
│  ████████   ████████   ████████         │
└─────────────────────────────────────────┘
```

### Color Roles

| Role | Light | Dark | Usage |
|------|-------|------|-------|
| Primary | Tonal 40 | Tonal 80 | Key components, FAB, active states |
| On Primary | Tonal 100 | Tonal 20 | Text/icons on primary |
| Primary Container | Tonal 90 | Tonal 30 | Less emphasis containers |
| On Primary Container | Tonal 10 | Tonal 90 | Text/icons on container |
| Secondary | Tonal 40 | Tonal 80 | Less prominent components |
| Tertiary | Tonal 40 | Tonal 80 | Contrasting accents |
| Surface | Neutral 99 | Neutral 10 | Backgrounds, cards |
| On Surface | Neutral 10 | Neutral 90 | Body text |
| Surface Variant | NeutralVar 90 | NeutralVar 30 | Decorative elements |
| Outline | NeutralVar 50 | NeutralVar 60 | Dividers, borders |
| Error | Error 40 | Error 80 | Error states |

### Tonal Palette

```
Tonal values: 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99, 100

0   = Black
100 = White

Light mode typically uses: 40 (primary), 90 (container)
Dark mode typically uses: 80 (primary), 30 (container)
```

## Elevation

### Surface Tones

Material 3 uses tonal elevation instead of shadows:

```
┌────────────────────────────────────────────┐
│ Level  │ Elevation │ Tonal Offset          │
├────────────────────────────────────────────┤
│ 0      │ 0dp       │ Surface color         │
│ 1      │ 1dp       │ +5% primary           │
│ 2      │ 3dp       │ +8% primary           │
│ 3      │ 6dp       │ +11% primary          │
│ 4      │ 8dp       │ +12% primary          │
│ 5      │ 12dp      │ +14% primary          │
└────────────────────────────────────────────┘
```

### When to Use Elevation

- Level 0: Page backgrounds
- Level 1: Cards, sheets
- Level 2: Navigation bars
- Level 3: FABs, dialogs
- Level 4: Search bars
- Level 5: Snackbars, tooltips

## Shape

### Shape Scale

| Size | Corner Radius | Use Case |
|------|---------------|----------|
| None | 0dp | Dividers, full-bleed images |
| Extra Small | 4dp | Small chips, compact elements |
| Small | 8dp | Buttons, text fields |
| Medium | 12dp | Cards, dialogs |
| Large | 16dp | FAB, navigation drawers |
| Extra Large | 28dp | Large containers |
| Full | 50% | Circles, pills |

### Shape Family

```kotlin
// Define shapes
val shapes = Shapes(
    extraSmall = RoundedCornerShape(4.dp),
    small = RoundedCornerShape(8.dp),
    medium = RoundedCornerShape(12.dp),
    large = RoundedCornerShape(16.dp),
    extraLarge = RoundedCornerShape(28.dp)
)
```

## Components

### Buttons

| Type | Container | Text | Use |
|------|-----------|------|-----|
| Filled | Primary | On Primary | Highest emphasis |
| Filled Tonal | Secondary Container | On Secondary Container | Medium emphasis |
| Outlined | None + outline | Primary | Low emphasis |
| Text | None | Primary | Lowest emphasis |
| Elevated | Surface + elevation | Primary | Needs shadow |

```kotlin
// Compose examples
Button(onClick = {}) { Text("Filled") }
FilledTonalButton(onClick = {}) { Text("Tonal") }
OutlinedButton(onClick = {}) { Text("Outlined") }
TextButton(onClick = {}) { Text("Text") }
ElevatedButton(onClick = {}) { Text("Elevated") }
```

### FAB (Floating Action Button)

```
┌─────────────────────────────────┐
│ Size    │ Diameter │ Icon Size │
├─────────────────────────────────┤
│ Small   │ 40dp     │ 24dp      │
│ Regular │ 56dp     │ 24dp      │
│ Large   │ 96dp     │ 36dp      │
│ Extended│ 56dp h   │ 24dp      │
└─────────────────────────────────┘
```

Position: Bottom right, 16dp from edges

### Text Fields

```
┌──────────────────────────────────────────┐
│  Filled (default)                        │
│  ┌────────────────────────────────────┐  │
│  │ Label                              │  │
│  │ Input text                         │  │
│  │ ─────────────────────────────────  │  │
│  │ Supporting text                    │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Outlined                                │
│  ┌────────────────────────────────────┐  │
│  │ Label ─────────────────────────────│  │
│  │ Input text                         │  │
│  │ ─────────────────────────────────  │  │
│  │ Supporting text                    │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

### Cards

| Type | Elevation | Use Case |
|------|-----------|----------|
| Elevated | Level 1 | Default, needs shadow |
| Filled | Level 0 | On elevated surfaces |
| Outlined | Level 0 | On same-color surfaces |

### Chips

| Type | Use Case |
|------|----------|
| Assist | Smart suggestions, shortcuts |
| Filter | Filtering content |
| Input | Tags, entered information |
| Suggestion | Dynamic recommendations |

## Navigation

### Bottom Navigation

```
┌──────────────────────────────────────────┐
│              Content                      │
├──────────────────────────────────────────┤
│   🏠        🔍        ❤️        👤      │
│  Home    Search   Favorites  Profile     │
└──────────────────────────────────────────┘
Height: 80dp
```

- 3-5 destinations
- Icon + label always visible
- Active indicator pill around icon

### Navigation Rail (Tablets)

```
┌─────┬───────────────────────────────────┐
│ ≡   │                                   │
│     │                                   │
│ 🏠  │                                   │
│Home │          Content                  │
│     │                                   │
│ 🔍  │                                   │
│Srch │                                   │
│     │                                   │
│ ❤️  │                                   │
│Favs │                                   │
└─────┴───────────────────────────────────┘
Width: 80dp
```

### Navigation Drawer

```
┌──────────────────────────┬──────────────┐
│                          │              │
│  App Name                │              │
│  ─────────────────────   │              │
│                          │              │
│  🏠  Home                │    Content   │
│  ●══════════════●        │              │
│                          │              │
│  📁  Files               │              │
│  👥  Shared              │              │
│  ⭐  Starred             │              │
│                          │              │
│  ─────────────────────   │              │
│                          │              │
│  ⚙️  Settings            │              │
│                          │              │
└──────────────────────────┴──────────────┘
Width: 360dp max
```

### Top App Bar

| Type | Scroll Behavior | Use Case |
|------|-----------------|----------|
| Small | Fixed or scroll | General use |
| Medium | Scroll to collapse | With prominent titles |
| Large | Scroll to collapse | Hero moments |
| Center-aligned | Fixed | Simple apps |

## Motion

### Duration Scale

| Token | Duration | Use Case |
|-------|----------|----------|
| Short 1 | 50ms | Simple selections |
| Short 2 | 100ms | Icon changes |
| Short 3 | 150ms | Snackbar entry |
| Short 4 | 200ms | Dialogs, sheets |
| Medium 1 | 250ms | Tabs, navigation |
| Medium 2 | 300ms | Expanding components |
| Medium 3 | 350ms | Navigation transitions |
| Medium 4 | 400ms | Complex layouts |
| Long 1 | 450ms | Page transitions |
| Long 2 | 500ms | Large surface changes |
| Long 3 | 550ms | View transitions |
| Long 4 | 600ms | Reveal animations |
| Extra Long | 700ms+ | Onboarding, tutorials |

### Easing

```kotlin
// Standard easing
val emphasized = CubicBezier(0.2f, 0f, 0f, 1f)
val emphasizedDecelerate = CubicBezier(0.05f, 0.7f, 0.1f, 1f)
val emphasizedAccelerate = CubicBezier(0.3f, 0f, 0.8f, 0.15f)

// Linear (rarely used)
val linear = CubicBezier(0f, 0f, 1f, 1f)
```

## 2025: Material 3 Expressive

### New Features

- **Springy Motion**: Physics-based animations
- **Bolder Typography**: More expressive type choices
- **Emotional Connection**: Design that makes users feel
- **Personal Expression**: Beyond wallpaper colors

### Recommendations

```markdown
✓ Use dynamic color for personalization
✓ Add meaningful microinteractions
✓ Consider emotional impact of choices
✓ Balance expression with usability
```

## Accessibility

### Touch Targets
- Minimum: 48×48dp
- Visual can be smaller, touch area must be 48dp

### Contrast
- Normal text: 4.5:1 minimum
- Large text (18sp+): 3:1 minimum
- UI components: 3:1 minimum

### Focus
- Visible focus indicator for all interactive elements
- Logical focus order (left-to-right, top-to-bottom)

### Screen Readers
```kotlin
Modifier.semantics {
    contentDescription = "Add item to cart"
    stateDescription = "Selected"
}
```

## Layout

### Grid System

| Screen Size | Columns | Margins | Gutters |
|-------------|---------|---------|---------|
| < 600dp (Phone) | 4 | 16dp | 8dp |
| 600-904dp (Tablet) | 8 | 32dp | 24dp |
| ≥ 905dp (Desktop) | 12 | 32dp | 24dp |

### Canonical Layouts

```markdown
## List-Detail
For master-detail patterns on tablets
├── List pane (1/3 width)
└── Detail pane (2/3 width)

## Supporting Panel
For content with auxiliary info
├── Main content (2/3 width)
└── Side panel (1/3 width)

## Feed
For scrolling content
└── Single column, card-based
```

## Resources

- [Material Design 3](https://m3.material.io/)
- [Material Theme Builder](https://m3.material.io/theme-builder)
- [Material Components](https://github.com/material-components)
