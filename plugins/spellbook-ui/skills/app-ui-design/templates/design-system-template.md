# Design System Template

Use this template to define your app's design system.

## App Information

| Property | Value |
|----------|-------|
| App Name | [Your App Name] |
| Platform | iOS / Android / Cross-platform |
| Last Updated | [Date] |
| Design Tool | Figma / Sketch / Adobe XD |

---

## Color Tokens

### Primary Colors

```css
/* Primary */
--color-primary: #[HEX];
--color-primary-light: #[HEX];
--color-primary-dark: #[HEX];
--color-on-primary: #[HEX];

/* Secondary */
--color-secondary: #[HEX];
--color-secondary-light: #[HEX];
--color-secondary-dark: #[HEX];
--color-on-secondary: #[HEX];

/* Tertiary (Optional) */
--color-tertiary: #[HEX];
--color-on-tertiary: #[HEX];
```

### Background & Surface

```css
/* Light Mode */
--color-background: #FFFFFF;
--color-surface: #F5F5F5;
--color-surface-variant: #E8E8E8;

/* Dark Mode */
--color-background-dark: #121212;
--color-surface-dark: #1E1E1E;
--color-surface-variant-dark: #2C2C2C;
```

### Text Colors

```css
/* Light Mode */
--color-text-primary: #1A1A1A;
--color-text-secondary: #666666;
--color-text-disabled: #999999;
--color-text-hint: #AAAAAA;

/* Dark Mode */
--color-text-primary-dark: #FFFFFF;
--color-text-secondary-dark: #B3B3B3;
--color-text-disabled-dark: #666666;
```

### Semantic Colors

```css
/* Status */
--color-error: #D32F2F;
--color-error-light: #FFEBEE;
--color-on-error: #FFFFFF;

--color-warning: #F9A825;
--color-warning-light: #FFF8E1;
--color-on-warning: #000000;

--color-success: #388E3C;
--color-success-light: #E8F5E9;
--color-on-success: #FFFFFF;

--color-info: #1976D2;
--color-info-light: #E3F2FD;
--color-on-info: #FFFFFF;
```

### Outline & Divider

```css
--color-outline: #E0E0E0;
--color-outline-variant: #BDBDBD;
--color-divider: #EEEEEE;
```

---

## Typography

### Font Families

```css
/* iOS */
--font-family-primary: 'SF Pro Text', -apple-system, sans-serif;
--font-family-display: 'SF Pro Display', -apple-system, sans-serif;

/* Android */
--font-family-primary: 'Roboto', sans-serif;
--font-family-display: 'Roboto', sans-serif;

/* Cross-platform alternative */
--font-family-primary: 'Inter', system-ui, sans-serif;
```

### Type Scale

| Token | Size | Weight | Line Height | Use |
|-------|------|--------|-------------|-----|
| display-large | 57px | 400 | 64px | Hero text |
| display-medium | 45px | 400 | 52px | Large headers |
| display-small | 36px | 400 | 44px | Section titles |
| headline-large | 32px | 400 | 40px | Page titles |
| headline-medium | 28px | 400 | 36px | Section headers |
| headline-small | 24px | 400 | 32px | Card titles |
| title-large | 22px | 500 | 28px | List item titles |
| title-medium | 16px | 500 | 24px | Subtitles |
| title-small | 14px | 500 | 20px | Captions |
| body-large | 16px | 400 | 24px | Main body text |
| body-medium | 14px | 400 | 20px | Secondary text |
| body-small | 12px | 400 | 16px | Helper text |
| label-large | 14px | 500 | 20px | Button text |
| label-medium | 12px | 500 | 16px | Chips, badges |
| label-small | 11px | 500 | 16px | Timestamps |

### CSS Variables

```css
--font-size-display-large: 57px;
--font-size-display-medium: 45px;
--font-size-display-small: 36px;
--font-size-headline-large: 32px;
--font-size-headline-medium: 28px;
--font-size-headline-small: 24px;
--font-size-title-large: 22px;
--font-size-title-medium: 16px;
--font-size-title-small: 14px;
--font-size-body-large: 16px;
--font-size-body-medium: 14px;
--font-size-body-small: 12px;
--font-size-label-large: 14px;
--font-size-label-medium: 12px;
--font-size-label-small: 11px;
```

---

## Spacing

### Base Unit

```css
--spacing-unit: 8px;
```

### Spacing Scale

```css
--spacing-0: 0px;
--spacing-1: 4px;   /* 0.5 units */
--spacing-2: 8px;   /* 1 unit */
--spacing-3: 12px;  /* 1.5 units */
--spacing-4: 16px;  /* 2 units */
--spacing-5: 20px;  /* 2.5 units */
--spacing-6: 24px;  /* 3 units */
--spacing-8: 32px;  /* 4 units */
--spacing-10: 40px; /* 5 units */
--spacing-12: 48px; /* 6 units */
--spacing-16: 64px; /* 8 units */
--spacing-20: 80px; /* 10 units */
```

### Layout Spacing

```css
/* Screen margins */
--layout-margin-mobile: 16px;
--layout-margin-tablet: 24px;
--layout-margin-desktop: 32px;

/* Content spacing */
--layout-gutter: 16px;
--layout-section-gap: 32px;
--layout-card-gap: 16px;

/* Component internal padding */
--padding-button-horizontal: 24px;
--padding-button-vertical: 12px;
--padding-card: 16px;
--padding-input: 12px;
```

---

## Border Radius

```css
--radius-none: 0px;
--radius-xs: 4px;
--radius-sm: 8px;
--radius-md: 12px;
--radius-lg: 16px;
--radius-xl: 24px;
--radius-2xl: 32px;
--radius-full: 9999px;
```

### Component Defaults

```css
--radius-button: 8px;
--radius-button-pill: 9999px;
--radius-card: 12px;
--radius-input: 8px;
--radius-dialog: 16px;
--radius-fab: 16px;
--radius-chip: 8px;
--radius-avatar: 9999px;
```

---

## Shadows & Elevation

### Light Mode

```css
--shadow-1: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-2: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
--shadow-3: 0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06);
--shadow-4: 0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05);
--shadow-5: 0 20px 25px rgba(0, 0, 0, 0.1), 0 10px 10px rgba(0, 0, 0, 0.04);
```

### Dark Mode (Tonal Elevation)

```css
--elevation-1: linear-gradient(0deg, rgba(255,255,255,0.05), rgba(255,255,255,0.05));
--elevation-2: linear-gradient(0deg, rgba(255,255,255,0.08), rgba(255,255,255,0.08));
--elevation-3: linear-gradient(0deg, rgba(255,255,255,0.11), rgba(255,255,255,0.11));
--elevation-4: linear-gradient(0deg, rgba(255,255,255,0.12), rgba(255,255,255,0.12));
--elevation-5: linear-gradient(0deg, rgba(255,255,255,0.14), rgba(255,255,255,0.14));
```

### Component Elevation

| Component | Level | Shadow |
|-----------|-------|--------|
| Flat elements | 0 | None |
| Cards | 1 | shadow-1 |
| Navigation | 2 | shadow-2 |
| FAB | 3 | shadow-3 |
| Dialogs | 4 | shadow-4 |
| Modals | 5 | shadow-5 |

---

## Motion

### Duration

```css
--duration-instant: 50ms;
--duration-fast: 100ms;
--duration-normal: 200ms;
--duration-slow: 300ms;
--duration-slower: 400ms;
--duration-slowest: 500ms;
```

### Easing

```css
--easing-standard: cubic-bezier(0.4, 0.0, 0.2, 1);
--easing-decelerate: cubic-bezier(0.0, 0.0, 0.2, 1);
--easing-accelerate: cubic-bezier(0.4, 0.0, 1, 1);
--easing-sharp: cubic-bezier(0.4, 0.0, 0.6, 1);
--easing-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275);
```

### Common Transitions

```css
--transition-color: color var(--duration-fast) var(--easing-standard);
--transition-background: background-color var(--duration-fast) var(--easing-standard);
--transition-transform: transform var(--duration-normal) var(--easing-standard);
--transition-opacity: opacity var(--duration-normal) var(--easing-standard);
--transition-all: all var(--duration-normal) var(--easing-standard);
```

---

## Components

### Buttons

| Variant | Background | Text | Border |
|---------|------------|------|--------|
| Primary | --color-primary | --color-on-primary | None |
| Secondary | --color-secondary | --color-on-secondary | None |
| Outline | Transparent | --color-primary | --color-primary |
| Ghost | Transparent | --color-primary | None |
| Destructive | --color-error | --color-on-error | None |

### States

| State | Opacity | Additional |
|-------|---------|------------|
| Default | 100% | - |
| Hover | - | +8% overlay |
| Pressed | - | +12% overlay |
| Focused | - | Focus ring |
| Disabled | 50% | cursor: not-allowed |

### Sizes

| Size | Height | Padding | Font |
|------|--------|---------|------|
| Small | 32px | 12px 16px | label-medium |
| Medium | 40px | 12px 24px | label-large |
| Large | 48px | 14px 32px | label-large |

---

## Icons

### Size Scale

```css
--icon-xs: 16px;
--icon-sm: 20px;
--icon-md: 24px;
--icon-lg: 32px;
--icon-xl: 48px;
```

### Icon Sets

- iOS: SF Symbols
- Android: Material Symbols
- Cross-platform: [Your chosen set]

---

## Touch Targets

```css
/* Minimum sizes */
--touch-target-min: 44px;  /* iOS */
--touch-target-min-android: 48px;  /* Android */

/* Recommended */
--touch-target-recommended: 48px;

/* Spacing between targets */
--touch-target-gap: 8px;
```

---

## Breakpoints

```css
--breakpoint-mobile: 0px;      /* 0-599 */
--breakpoint-tablet: 600px;    /* 600-904 */
--breakpoint-laptop: 905px;    /* 905-1239 */
--breakpoint-desktop: 1240px;  /* 1240-1439 */
--breakpoint-wide: 1440px;     /* 1440+ */
```

---

## Z-Index Scale

```css
--z-base: 0;
--z-dropdown: 100;
--z-sticky: 200;
--z-overlay: 300;
--z-modal: 400;
--z-popover: 500;
--z-toast: 600;
--z-tooltip: 700;
```

---

## Checklist

Before using this design system, verify:

- [ ] All color tokens defined
- [ ] Light and dark mode variants
- [ ] Typography scale complete
- [ ] Spacing scale consistent
- [ ] All component states defined
- [ ] Accessibility requirements met (contrast, touch targets)
- [ ] Motion tokens defined
- [ ] Breakpoints defined
- [ ] Design tool file linked
- [ ] Documentation complete
