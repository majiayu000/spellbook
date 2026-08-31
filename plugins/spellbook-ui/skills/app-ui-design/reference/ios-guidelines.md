# iOS Human Interface Guidelines

Quick reference for iOS app design following Apple's Human Interface Guidelines (2025).

## Design Principles

### Clarity
- Text must be legible at every size
- Icons must be precise and understandable
- Adornments must be subtle and appropriate
- Focus on functionality drives design

### Deference
- Fluid motion and crisp interface help understanding
- Content fills the screen
- Translucency and blur hint at more content
- Minimal use of bezels, gradients, and shadows

### Depth
- Distinct visual layers convey hierarchy
- Transitions provide sense of depth
- Touch and discoverability enhance delight

## Typography

### SF Pro Font Family

| Style | Size | Weight | Use Case |
|-------|------|--------|----------|
| Large Title | 34pt | Bold | Screen titles, first visible element |
| Title 1 | 28pt | Bold | Major section headers |
| Title 2 | 22pt | Bold | Secondary headers |
| Title 3 | 20pt | Semibold | Tertiary headers |
| Headline | 17pt | Semibold | List item titles |
| Body | 17pt | Regular | Main content text |
| Callout | 16pt | Regular | Supplementary text |
| Subhead | 15pt | Regular | Metadata |
| Footnote | 13pt | Regular | Small details |
| Caption 1 | 12pt | Regular | Image captions |
| Caption 2 | 11pt | Regular | Timestamps |

### Dynamic Type Support

Always support Dynamic Type for accessibility:

```swift
// SwiftUI
Text("Hello")
    .font(.body) // Automatically scales

// UIKit
label.font = UIFont.preferredFont(forTextStyle: .body)
label.adjustsFontForContentSizeCategory = true
```

## Layout & Spacing

### Safe Areas

```
┌──────────────────────────────────┐
│         Status Bar (47pt)        │  ← Top safe area
├──────────────────────────────────┤
│                                  │
│                                  │
│         Content Area             │
│                                  │
│                                  │
├──────────────────────────────────┤
│     Home Indicator (34pt)        │  ← Bottom safe area
└──────────────────────────────────┘
```

### Standard Margins

| Element | Margin |
|---------|--------|
| Screen edge (iPhone) | 16pt |
| Screen edge (iPad) | 20pt |
| Between sections | 35pt |
| Between related elements | 8pt |

### Touch Targets

- **Minimum size**: 44×44pt
- **Recommended size**: 48×48pt for primary actions
- **Spacing between targets**: 8pt minimum

## Navigation

### Tab Bar

```
┌──────────────────────────────────┐
│         Content Area             │
├──────────────────────────────────┤
│  🏠    🔍    ➕    ❤️    👤  │
│ Home Search  Add  Favs Profile  │
└──────────────────────────────────┘
Height: 49pt (83pt on Face ID devices)
```

- 3-5 tabs maximum
- Always show labels
- Use SF Symbols for icons
- Highlight active tab with fill or tint

### Navigation Bar

```
┌──────────────────────────────────┐
│  ‹ Back       Title        Edit  │
│  (or Menu)                       │
└──────────────────────────────────┘
Height: 44pt (96pt with large title)
```

- Large title: Use for primary screens
- Standard title: Use for secondary screens
- Back button shows previous screen title (truncated)

### Sheets & Modals

```
Types:
- Sheet (.sheet) → Partial screen, swipe to dismiss
- Full Screen (.fullScreenCover) → Complete takeover
- Popover (iPad) → Contextual floating panel
- Alert → Critical information, requires action
```

## Components

### Buttons

| Type | Appearance | Use Case |
|------|------------|----------|
| Filled | Solid background | Primary action |
| Gray | Gray background | Secondary action |
| Tinted | Colored text | Tertiary action |
| Plain | Text only | Navigation, links |
| Borderless | Icon only | Toolbar actions |

### Lists

```swift
List {
    Section("Section Header") {
        ForEach(items) { item in
            HStack {
                Image(systemName: item.icon)
                VStack(alignment: .leading) {
                    Text(item.title)
                    Text(item.subtitle)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}
```

- Use standard row height (44pt minimum)
- Group related items in sections
- Provide swipe actions for common tasks
- Support pull-to-refresh when appropriate

### Text Fields

```
┌──────────────────────────────────┐
│  Label                           │
│  ┌────────────────────────────┐  │
│  │ Placeholder text           │  │
│  └────────────────────────────┘  │
│  Helper text or error message    │
└──────────────────────────────────┘
```

- Clear button on right
- Show appropriate keyboard type
- Support password autofill
- Indicate required fields

## Colors

### System Colors

```swift
// Semantic colors (adapt to light/dark mode)
Color.primary      // Primary text
Color.secondary    // Secondary text
Color.accentColor  // App tint color

// System colors
Color.red          // #FF3B30
Color.orange       // #FF9500
Color.yellow       // #FFCC00
Color.green        // #34C759
Color.mint         // #00C7BE
Color.teal         // #30B0C7
Color.cyan         // #32ADE6
Color.blue         // #007AFF
Color.indigo       // #5856D6
Color.purple       // #AF52DE
Color.pink         // #FF2D55
Color.brown        // #A2845E
```

### Dark Mode

```swift
// Backgrounds
Color(.systemBackground)       // White / Black
Color(.secondarySystemBackground)  // Light gray / Dark gray
Color(.tertiarySystemBackground)   // Darker variations

// Always use semantic colors for automatic adaptation
```

## 2025: Liquid Glass

Apple's new design language introduces:

### Characteristics
- **Translucency**: Background content visible through controls
- **Depth**: Floating elements with subtle shadows
- **Dynamic materials**: Responsive to underlying content
- **Vibrancy**: Text and icons adjust based on background

### Usage
```swift
// Apply glass effect
.background(.ultraThinMaterial)
.background(.regularMaterial)
.background(.thickMaterial)
```

## Icons

### SF Symbols

- Use SF Symbols for consistency
- Match symbol weight to text weight
- Use rendering modes appropriately:
  - Monochrome: Single color
  - Hierarchical: Primary/secondary emphasis
  - Palette: Custom colors
  - Multicolor: Original colors

```swift
Image(systemName: "heart.fill")
    .symbolRenderingMode(.hierarchical)
    .foregroundStyle(.red)
```

## Gestures

### Standard Gestures

| Gesture | Action |
|---------|--------|
| Tap | Select, activate |
| Long press | Preview, context menu |
| Swipe (edge) | Back navigation |
| Swipe (list item) | Quick actions |
| Pull down | Refresh, dismiss sheet |
| Pinch | Zoom |
| Rotate | Rotate content |

### Best Practices
- Always provide alternative for gestures
- Don't override system gestures
- Provide haptic feedback for actions

## Accessibility

### Requirements
- [ ] VoiceOver labels for all interactive elements
- [ ] Dynamic Type support (up to xxxLarge)
- [ ] Sufficient color contrast (4.5:1 minimum)
- [ ] Reduce Motion support
- [ ] High Contrast mode support
- [ ] Button Shapes support

```swift
Button("Submit") {
    submit()
}
.accessibilityLabel("Submit form")
.accessibilityHint("Double tap to submit your information")
```

## Device Considerations

### Screen Sizes (Points)

| Device | Width | Height | Safe Areas |
|--------|-------|--------|------------|
| iPhone SE | 375 | 667 | Top: 20, Bottom: 0 |
| iPhone 14 | 390 | 844 | Top: 47, Bottom: 34 |
| iPhone 14 Pro | 393 | 852 | Top: 59, Bottom: 34 |
| iPhone 14 Plus | 428 | 926 | Top: 47, Bottom: 34 |
| iPhone 15 Pro Max | 430 | 932 | Top: 59, Bottom: 34 |
| iPad Mini | 744 | 1133 | Varies |
| iPad Pro 11" | 834 | 1194 | Varies |
| iPad Pro 12.9" | 1024 | 1366 | Varies |

### Design Recommendations
- Start with iPhone 14 (390×844)
- Use Auto Layout / SwiftUI for adaptivity
- Test on smallest and largest devices
- Consider landscape orientation
