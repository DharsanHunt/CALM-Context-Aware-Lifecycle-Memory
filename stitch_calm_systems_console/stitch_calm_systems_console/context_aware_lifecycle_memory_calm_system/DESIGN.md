---
name: Context-Aware Lifecycle Memory (CALM) System
colors:
  surface: '#f8f9fb'
  surface-dim: '#d9dadc'
  surface-bright: '#f8f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#edeef0'
  surface-container-high: '#e7e8ea'
  surface-container-highest: '#e1e2e4'
  on-surface: '#191c1e'
  on-surface-variant: '#434655'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f3'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#505f76'
  on-secondary: '#ffffff'
  secondary-container: '#d0e1fb'
  on-secondary-container: '#54647a'
  tertiary: '#943700'
  on-tertiary: '#ffffff'
  tertiary-container: '#bc4800'
  on-tertiary-container: '#ffede6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb596'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#7d2d00'
  background: '#f8f9fb'
  on-background: '#191c1e'
  surface-variant: '#e1e2e4'
typography:
  display:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  h1:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  h2:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  code-md:
    fontFamily: IBM Plex Mono
    fontSize: 14px
    fontWeight: '450'
    lineHeight: 20px
  code-sm:
    fontFamily: IBM Plex Mono
    fontSize: 12px
    fontWeight: '450'
    lineHeight: 16px
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  container-max: 1440px
  gutter: 16px
---

## Brand & Style
The design system is rooted in **Modern Minimalism** with a focus on functional precision. It is designed for high-density technical environments where clarity of information is paramount. The aesthetic avoids decorative flourishes like gradients or glows, instead relying on rigorous alignment, consistent spacing, and a clear typographic hierarchy. The target audience includes researchers and engineers who require a quiet, reliable interface that facilitates deep focus and data analysis.

## Colors
The palette is built on a foundation of neutral grays and cool whites to minimize visual fatigue.
- **Primary:** A precise blue used sparingly for actions and focus states.
- **Surface & Background:** A subtle distinction between `#F7F8FA` for the application canvas and `#FFFFFF` for interactive cards and panels.
- **Semantic States:** Lifecycle states are represented by specific, high-contrast colors to ensure rapid identification in dense logs and tables. 
- **Borders:** Every container is defined by a consistent `#E4E7EB` stroke rather than shadows.

## Typography
This design system utilizes a dual-font approach. **Inter** handles all UI elements, navigation, and labels for maximum legibility. **IBM Plex Mono** is reserved for technical data, memory addresses, timestamps, and numerical values, reinforcing the "research-oriented" character of the product. 

For mobile screens, `display` and `h1` levels should scale down by 15% to maintain information density without inducing horizontal scrolling.

## Layout & Spacing
The layout follows a **4px baseline grid**. A fluid 12-column grid is used for dashboard layouts, while sidebar-heavy views utilize a fixed 240px navigation width with a fluid content area. 

- **Density:** High. Vertical padding in lists and tables should be kept to `8px` (sm) to ensure maximum data visibility.
- **Margins:** Standard page margins are `24px` on desktop and `16px` on mobile.
- **Breakpoints:**
  - Mobile: < 768px (single column)
  - Tablet: 768px - 1024px (compact sidebars)
  - Desktop: > 1024px (full layout)

## Elevation & Depth
Depth is communicated through **Tonal Layering** and **Borders** rather than shadows. 
- **Level 0 (Background):** `#F7F8FA` – The base canvas.
- **Level 1 (Surface):** `#FFFFFF` with a 1px border `#E4E7EB`. Used for primary cards and content blocks.
- **Level 2 (Interaction):** Subtle shifts to `#F9FAFB` for hover states on list items.
- **Overlays:** Only dropdown menus, modals, and drawers may use a soft, neutral shadow (`0 4px 6px -1px rgb(0 0 0 / 0.1)`) to separate them from the underlying data layer.

## Shapes
The shape language is disciplined. Larger containers (cards, panels) use an `8px` radius to feel modern and organized. Interactive elements (buttons, input fields, tags) use a slightly tighter `6px` radius to maintain a professional, tool-like appearance. Status dots and avatars are circular.

## Components
- **Buttons:** Solid primary blue for main actions; ghost/outline for secondary. Use `6px` radius. Content should be centered with `body-sm` typography.
- **Input Fields:** 1px border `#E4E7EB`. On focus, use a 1px solid primary blue stroke with no outer glow.
- **Status Chips:** Small, low-height indicators using the `label-caps` font. They should feature a background at 10% opacity of the state color with a solid color text and a 2px circular dot prefix.
- **Data Tables:** No vertical grid lines. Use horizontal lines in `#E4E7EB`. Header row uses `label-caps` typography with a subtle background tint.
- **Monospace Tags:** For memory addresses or IDs, use a light gray background `#F1F5F9` with `code-sm` typography.
- **Cards:** White background, 1px border, `8px` radius. Title sections should be separated by a thin horizontal rule.