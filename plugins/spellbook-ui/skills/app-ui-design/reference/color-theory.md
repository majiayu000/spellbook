# Color Theory for Mobile Apps

Essential color selection and usage guidelines for mobile app design.

## Color Fundamentals

### Color Properties

```markdown
HUE        → The color itself (red, blue, green)
             Measured in degrees (0-360°)

SATURATION → Color intensity/purity
             0% = gray, 100% = pure color

LIGHTNESS  → How light or dark
             0% = black, 100% = white

BRIGHTNESS → Perceived luminance
             How much light appears to emit
```

### Color Wheel

```
              Yellow (60°)
                  ●
            /           \
     Yellow-Green      Orange
          /               \
    Green ●               ● Red (0°/360°)
          \               /
       Cyan           Magenta
            \         /
                ●
              Blue (240°)
```

---

## Color Relationships

### Monochromatic
Single hue with varying saturation/lightness.

```
████████████████████████████████
Light ←──────────────────→ Dark

Use: Clean, professional, minimalist apps
Example: Different shades of blue
```

### Complementary
Colors opposite on the wheel (high contrast).

```
    ●──────────────●
   Red            Cyan

Use: CTAs, important elements, contrast
Caution: Can be jarring if overused
```

### Analogous
Adjacent colors on the wheel (harmonious).

```
        ● ● ●
    Blue Cyan Green

Use: Cohesive, calming palettes
Example: Nature apps, wellness apps
```

### Triadic
Three colors equally spaced (balanced variety).

```
          ●
         /  \
        /    \
       ●──────●

Use: Vibrant, balanced palettes
Example: Red, Yellow, Blue (primary)
```

### Split-Complementary
One color + two adjacent to its complement.

```
          ●
         /|\
        / | \
       ●     ●

Use: Contrast with less tension
Example: Blue + Yellow-Orange + Red-Orange
```

---

## The 60-30-10 Rule

```markdown
60% → Primary/Neutral color (backgrounds, large areas)
30% → Secondary color (cards, sections, supporting)
10% → Accent color (CTAs, icons, highlights)

Example:
┌────────────────────────────────────────────┐
│                                            │
│  ████████████████████████████████████████  │ 60% Light Gray
│  ████████████████████████████████████████  │ (Background)
│  ████████████████████████████████████████  │
│                                            │
│     ┌────────────────────────────────┐     │
│     │  ████████████████████████████  │     │ 30% White
│     │  ████████████████████████████  │     │ (Cards)
│     │          ┌──────────┐          │     │
│     │          │  Submit  │          │     │ 10% Blue
│     │          └──────────┘          │     │ (CTA Button)
│     └────────────────────────────────┘     │
│                                            │
└────────────────────────────────────────────┘
```

---

## Semantic Colors

### Standard Meanings

| Color | Meaning | Use Cases |
|-------|---------|-----------|
| Blue | Trust, security, calm | Primary actions, links |
| Green | Success, growth, go | Confirmations, positive |
| Red | Error, danger, stop | Errors, destructive actions |
| Yellow | Warning, caution | Alerts, warnings |
| Orange | Energy, enthusiasm | Secondary CTAs, highlights |
| Purple | Premium, creative | Luxury, creative apps |
| Gray | Neutral, secondary | Text, borders, disabled |

### Semantic Token Structure

```markdown
## Color Token Naming

Semantic (Recommended):
├── color-primary
├── color-primary-variant
├── color-secondary
├── color-background
├── color-surface
├── color-error
├── color-success
├── color-warning
├── color-on-primary
├── color-on-background
└── color-on-surface

Avoid Literal Names:
├── color-blue ← Don't use
├── color-red ← Don't use
└── color-green ← Don't use
```

---

## Dark Mode Colors

### Adaptation Principles

```markdown
DON'T just invert colors. Instead:

1. Reduce saturation for dark surfaces
2. Use elevation with lighter overlays
3. Keep brand colors recognizable
4. Test contrast in both modes

Light Mode → Dark Mode
───────────────────────────────────────
White background → Dark gray (#121212), not pure black
Black text → Light gray (#E0E0E0), not pure white
Vibrant primary → Slightly desaturated primary
White on colored → Dark on lighter colored
```

### Surface Elevation (Material 3)

```markdown
Dark Mode Surface Colors:

Level 0: #121212 (base surface)
Level 1: #1E1E1E (+ 5% white overlay)
Level 2: #232323 (+ 7% white overlay)
Level 3: #272727 (+ 8% white overlay)
Level 4: #2C2C2C (+ 9% white overlay)
Level 5: #323232 (+ 11% white overlay)

Cards and elevated elements use higher levels
to create visual hierarchy without shadows.
```

### OLED Optimization

```markdown
For OLED screens:
- True black (#000000) saves battery
- Use for backgrounds where appropriate
- Avoid large areas of pure white
- Test for "smearing" effect on scrolling

Recommendation:
Use near-black (#0A0A0A) instead of pure black
for main backgrounds to reduce contrast issues.
```

---

## Accessibility & Contrast

### WCAG Contrast Requirements

```markdown
Minimum Contrast Ratios:

Text (< 18pt / 14pt bold):     4.5:1  [AA]
Large Text (≥ 18pt / 14pt bold): 3:1  [AA]
UI Components:                   3:1  [AA]

Enhanced (AAA):
Text:       7:1
Large Text: 4.5:1
```

### Color Contrast Examples

```markdown
Good Contrast ✓
─────────────────────────────────────────
#000000 on #FFFFFF → 21:1 (Excellent)
#333333 on #FFFFFF → 12.6:1 (Excellent)
#0066CC on #FFFFFF → 5.3:1 (Good for AA)
#1A73E8 on #FFFFFF → 4.5:1 (Minimum AA)

Poor Contrast ✗
─────────────────────────────────────────
#777777 on #FFFFFF → 4.5:1 (Borderline)
#999999 on #FFFFFF → 2.8:1 (Fail)
#AAAAAA on #FFFFFF → 2.3:1 (Fail)
```

### Colorblind Considerations

```markdown
Types of Color Blindness:
├── Deuteranopia (red-green, most common)
├── Protanopia (red-green)
├── Tritanopia (blue-yellow, rare)
└── Achromatopsia (complete, very rare)

Guidelines:
1. Don't rely on color alone
2. Add icons, patterns, or text
3. Test with color blindness simulators
4. Avoid red/green combinations for distinctions

Tools:
- Color Oracle (desktop simulator)
- Figma A11y plugin
- Chrome DevTools → Rendering → Emulate
```

---

## Brand Color Guidelines

### Choosing Primary Color

```markdown
Considerations:
1. Industry conventions
2. Target audience expectations
3. Cultural meanings
4. Competitor differentiation
5. Accessibility requirements

Industry Trends:
├── Finance: Blue (trust, security)
├── Health: Green, Blue (calm, growth)
├── Food: Red, Orange (appetite, energy)
├── Luxury: Black, Gold, Purple (premium)
├── Tech: Blue, Purple (innovation)
└── Children: Bright, varied (fun)
```

### Creating a Palette

```markdown
Step 1: Choose primary color
        ████████████
        Brand Blue #1A73E8

Step 2: Generate tonal variations
        100 ██████████ Lightest
        200 ██████████
        300 ██████████
        400 ██████████
        500 ██████████ ← Primary
        600 ██████████
        700 ██████████
        800 ██████████
        900 ██████████ Darkest

Step 3: Select secondary color
        (Complementary or analogous)

Step 4: Add semantic colors
        (Error, warning, success)

Step 5: Define neutrals
        (Gray scale for text, borders)
```

### Palette Sizes

```markdown
Minimal Palette (Simple Apps):
├── Primary (1 shade)
├── Secondary (1 shade)
├── Neutrals (3-5 grays)
├── Error (red)
└── Success (green)

Standard Palette (Most Apps):
├── Primary (5 tonal variations)
├── Secondary (5 tonal variations)
├── Tertiary (3 tonal variations)
├── Neutrals (7-10 grays)
├── Semantic (error, warning, success, info)
└── Surfaces (light/dark backgrounds)

Extended Palette (Complex Apps):
├── Primary family (10 variations)
├── Secondary family (10 variations)
├── Tertiary family (10 variations)
├── Extended neutrals
├── Extended semantics
└── Special purpose colors
```

---

## 2025 Color Trends

### Popular Palettes

```markdown
1. Muted & Desaturated
   Soft, gentle colors with reduced saturation
   ██████ #8B9A7D (Sage)
   ██████ #B8A9C9 (Lavender)
   ██████ #F2E8DC (Cream)

2. Bold Gradients
   Vibrant color transitions
   ██████ → ██████ (Sunset: Orange to Pink)
   ██████ → ██████ (Ocean: Blue to Teal)

3. Neo-Brutalism
   High contrast, bold primaries
   ██████ #FF5733 (Bold Orange)
   ██████ #000000 (Black)
   ██████ #FFFFFF (White)

4. Digital Nature
   Tech meets organic
   ██████ #0A6847 (Forest)
   ██████ #7ABA78 (Leaf)
   ██████ #F6E9B2 (Sand)
```

### Material You Dynamic Color

```markdown
Android 12+ extracts colors from wallpaper:

User Wallpaper
      ↓
Color Extraction Algorithm
      ↓
├── Primary color
├── Secondary color
├── Tertiary color
├── Neutral color
└── Neutral variant

App automatically adapts to user's palette.
```

---

## Quick Reference

### Color Token Template

```json
{
  "colors": {
    "primary": {
      "main": "#1A73E8",
      "light": "#4285F4",
      "dark": "#1557B0",
      "contrast": "#FFFFFF"
    },
    "secondary": {
      "main": "#34A853",
      "light": "#5BB974",
      "dark": "#1E8E3E",
      "contrast": "#FFFFFF"
    },
    "background": {
      "default": "#FFFFFF",
      "paper": "#F5F5F5"
    },
    "text": {
      "primary": "#202124",
      "secondary": "#5F6368",
      "disabled": "#9AA0A6"
    },
    "error": "#D93025",
    "warning": "#F9AB00",
    "success": "#1E8E3E",
    "info": "#1A73E8"
  }
}
```

### Contrast Checker Tools

```markdown
Online Tools:
- WebAIM Contrast Checker
- Coolors Contrast Checker
- Color Review

Design Tool Plugins:
- Stark (Figma, Sketch)
- A11y Color Contrast
- Contrast (Figma)

Browser DevTools:
- Chrome: Inspect → Color picker
- Firefox: Accessibility Inspector
```

---

## Resources

- [Coolors](https://coolors.co/) - Palette generator
- [Adobe Color](https://color.adobe.com/) - Color wheel
- [Realtime Colors](https://www.realtimecolors.com/) - Preview on mock UI
- [Material Theme Builder](https://m3.material.io/theme-builder) - Material 3
- [Paletton](https://paletton.com/) - Color scheme designer
- [Color Hunt](https://colorhunt.co/) - Curated palettes
