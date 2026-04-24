# Style Guide

## Brand Identity

### Core Visual Language
Our design system employs a sophisticated purple-based color palette with high contrast between light and dark modes, creating an elegant and professional interface optimized for parliamentary and video content management.

## Typography System

### Font Families

#### Primary Font - Roboto (Sans-serif)
- **Usage**: Body text, UI elements, navigation
- **Weights**: 300 (Light), 400 (Regular), 500 (Medium), 700 (Bold)
- **Line Height**: 1.5 for body, 1.2 for headings
- **Letter Spacing**: Normal (0em)

#### Display Font - Playfair Display (Serif)
- **Usage**: Large headings, hero sections, emphasis text
- **Weights**: 400 (Regular), 700 (Bold), 900 (Black)
- **Best for**: Headlines h1-h3, quotes, special callouts

#### Monospace Font - Fira Code
- **Usage**: Code blocks, data displays, technical information
- **Features**: Ligatures enabled for better code readability
- **Weights**: 400 (Regular), 500 (Medium)

### Type Scale (Mobile-First)

```css
/* Mobile (base) */
--text-xs: 0.75rem;    /* 12px */
--text-sm: 0.875rem;   /* 14px */
--text-base: 1rem;     /* 16px */
--text-lg: 1.125rem;   /* 18px */
--text-xl: 1.25rem;    /* 20px */
--text-2xl: 1.5rem;    /* 24px */
--text-3xl: 1.875rem;  /* 30px */
--text-4xl: 2.25rem;   /* 36px */

/* Tablet (768px+) */
--text-xl: 1.5rem;     /* 24px */
--text-2xl: 1.875rem;  /* 30px */
--text-3xl: 2.25rem;   /* 36px */
--text-4xl: 3rem;      /* 48px */

/* Desktop (1024px+) */
--text-3xl: 3rem;      /* 48px */
--text-4xl: 3.75rem;   /* 60px */
--text-5xl: 4.5rem;    /* 72px */
```

## Color System

### Primary Palette

#### Primary Purple
- **Light**: `oklch(0.6056 0.2189 292.7172)`
- **Usage**: CTAs, primary actions, brand elements
- **Hex Equivalent**: #7c3aed (approximate)

#### Secondary Colors
- **Light Mode Background**: Pure white `oklch(1.0000 0 0)`
- **Dark Mode Background**: Deep purple-black `oklch(0.2077 0.0398 265.7549)`
- **Light Mode Text**: Dark purple-gray `oklch(0.3588 0.1354 278.6973)`
- **Dark Mode Text**: Light purple-gray `oklch(0.9299 0.0334 272.7879)`

### Semantic Colors

#### Success
- Light: `oklch(0.7 0.15 142)` (green)
- Dark: `oklch(0.65 0.13 142)`

#### Warning
- Light: `oklch(0.75 0.18 85)` (amber)
- Dark: `oklch(0.7 0.16 85)`

#### Error/Destructive
- Both modes: `oklch(0.6368 0.2078 25.3313)` (red-orange)

#### Info
- Light: `oklch(0.65 0.15 230)` (blue)
- Dark: `oklch(0.6 0.13 230)`

### Neutral Scale

```css
--neutral-50: oklch(0.98 0.01 293);
--neutral-100: oklch(0.97 0.016 293);
--neutral-200: oklch(0.93 0.033 272);
--neutral-300: oklch(0.85 0.05 280);
--neutral-400: oklch(0.70 0.08 285);
--neutral-500: oklch(0.54 0.12 290);
--neutral-600: oklch(0.43 0.15 292);
--neutral-700: oklch(0.35 0.13 278);
--neutral-800: oklch(0.26 0.086 281);
--neutral-900: oklch(0.21 0.04 265);
```

## Spacing System

### Base Unit: 0.25rem (4px)

```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
--space-20: 5rem;     /* 80px */
--space-24: 6rem;     /* 96px */
```

### Mobile-First Spacing

- **Mobile Padding**: 16px (1rem) container padding
- **Tablet Padding**: 24px (1.5rem) container padding  
- **Desktop Padding**: 32px (2rem) container padding
- **Max Width**: 1440px for content containers

## Border & Radius System

### Border Radius Scale

```css
--radius-none: 0;
--radius-sm: 0.375rem;  /* 6px */
--radius-md: 0.5rem;    /* 8px */
--radius-lg: 0.625rem;  /* 10px (default) */
--radius-xl: 0.875rem;  /* 14px */
--radius-2xl: 1rem;     /* 16px */
--radius-full: 9999px;  /* Pills, circles */
```

### Border Widths

```css
--border-1: 1px;
--border-2: 2px;
--border-4: 4px;
```

## Shadow System

### Elevation Scale

```css
/* Subtle elevation */
--shadow-xs: 2px 2px 4px 0px hsl(255 86% 66% / 0.10);

/* Card elevation */
--shadow-sm: 2px 2px 4px 0px hsl(255 86% 66% / 0.20), 
             2px 1px 2px -1px hsl(255 86% 66% / 0.20);

/* Modal/dropdown elevation */
--shadow-md: 2px 2px 4px 0px hsl(255 86% 66% / 0.20), 
             2px 2px 4px -1px hsl(255 86% 66% / 0.20);

/* High elevation */
--shadow-lg: 2px 2px 4px 0px hsl(255 86% 66% / 0.20), 
             2px 4px 6px -1px hsl(255 86% 66% / 0.20);

/* Maximum elevation */
--shadow-2xl: 2px 2px 4px 0px hsl(255 86% 66% / 0.50);
```

## Component Patterns

### Buttons

#### Primary Button
```css
background: var(--primary);
color: var(--primary-foreground);
padding: 0.5rem 1rem;
border-radius: var(--radius-lg);
font-weight: 500;
min-height: 44px; /* Mobile touch target */
```

#### Secondary Button
```css
background: var(--secondary);
color: var(--secondary-foreground);
border: 1px solid var(--border);
```

#### Ghost Button
```css
background: transparent;
color: var(--foreground);
hover: background var(--accent);
```

### Cards

```css
background: var(--card);
border: 1px solid var(--border);
border-radius: var(--radius-lg);
padding: 1.5rem;
shadow: var(--shadow-sm);
```

### Forms

#### Input Fields
```css
background: var(--background);
border: 1px solid var(--input);
border-radius: var(--radius-md);
padding: 0.5rem 0.75rem;
min-height: 44px; /* Mobile accessibility */
font-size: 16px; /* Prevent zoom on iOS */
```

#### Focus States
```css
outline: 2px solid var(--ring);
outline-offset: 2px;
```

### Navigation

#### Mobile Navigation
- Hamburger menu for screens < 768px
- Full-screen overlay with smooth transitions
- Touch-friendly tap targets (min 44x44px)
- Sticky header with backdrop blur

#### Desktop Navigation
- Horizontal menu bar
- Dropdown menus for nested items
- Hover states with color transitions
- Active page indicators

## Responsive Breakpoints

```css
--mobile: 0px;
--tablet: 768px;
--desktop: 1024px;
--wide: 1440px;
--ultrawide: 1920px;
```

### Container Widths

```css
--container-mobile: 100%;
--container-tablet: 750px;
--container-desktop: 970px;
--container-wide: 1170px;
--container-max: 1440px;
```

## Animation & Transitions

### Timing Functions

```css
--ease-in: cubic-bezier(0.4, 0, 1, 1);
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
--ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
```

### Duration Scale

```css
--duration-75: 75ms;
--duration-100: 100ms;
--duration-150: 150ms;
--duration-200: 200ms;
--duration-300: 300ms;
--duration-500: 500ms;
--duration-700: 700ms;
```

### Standard Transitions

```css
/* Hover transitions */
transition: all 150ms ease-in-out;

/* Color transitions */
transition: background-color 200ms ease-in-out,
            color 200ms ease-in-out;

/* Transform transitions */
transition: transform 300ms ease-out;
```

## Icons & Imagery

### Icon Sizes

```css
--icon-xs: 12px;
--icon-sm: 16px;
--icon-md: 20px;
--icon-lg: 24px;
--icon-xl: 32px;
--icon-2xl: 48px;
```

### Image Aspect Ratios

- **Hero Images**: 16:9 (desktop), 4:3 (mobile)
- **Card Thumbnails**: 16:9
- **Avatar Images**: 1:1 (square)
- **Video Previews**: 16:9

## Accessibility Standards

### Color Contrast
- **Normal Text**: Minimum 4.5:1 ratio
- **Large Text**: Minimum 3:1 ratio
- **Interactive Elements**: Minimum 3:1 ratio

### Touch Targets
- **Minimum Size**: 44x44px for all interactive elements
- **Spacing**: Minimum 8px between touch targets

### Focus Indicators
- **Visible Focus**: 2px solid outline with offset
- **High Contrast**: Focus color meets WCAG AA standards

### Text Legibility
- **Minimum Font Size**: 14px for body text
- **Line Length**: 45-75 characters for optimal reading
- **Line Height**: Minimum 1.5 for body text

## Dark Mode Considerations

### Automatic Theme Detection
- Respect system preferences by default
- Provide manual toggle option
- Persist user preference

### Color Adjustments
- Reduce contrast slightly in dark mode (90% instead of 100%)
- Use warmer blacks (purple-tinted) instead of pure black
- Increase shadow opacity in dark mode

### Image Handling
- Apply opacity: 0.9 to images in dark mode
- Consider providing dark mode variants for graphics
- Use CSS filters for simple inversions where appropriate

## Performance Guidelines

### Font Loading
```css
font-display: swap; /* Ensure text remains visible during load */
```

### Image Optimization
- Use WebP/AVIF with fallbacks
- Implement lazy loading for below-fold images
- Provide responsive image sizes

### CSS Optimization
- Use CSS custom properties for theming
- Minimize specificity chains
- Leverage Tailwind's JIT compiler

## Component Library Integration

### Shadcn/UI Customization
- Use CSS variables for all color values
- Maintain consistent border radius across components
- Apply custom shadow system to all elevated elements
- Ensure all components meet mobile touch target requirements

### Form Components
- Consistent validation error styling
- Loading states with skeleton screens
- Disabled state opacity: 0.5
- Success feedback with semantic colors

## Code Examples

### Mobile-First Media Query
```css
/* Mobile styles (default) */
.container {
  padding: 1rem;
}

/* Tablet and up */
@media (min-width: 768px) {
  .container {
    padding: 1.5rem;
  }
}

/* Desktop and up */
@media (min-width: 1024px) {
  .container {
    padding: 2rem;
    max-width: 1440px;
    margin: 0 auto;
  }
}
```

### Dark Mode Implementation
```css
/* Light mode (default) */
.card {
  background: var(--card);
  color: var(--card-foreground);
}

/* Dark mode */
.dark .card {
  background: var(--card);
  color: var(--card-foreground);
}
```

### Responsive Typography
```css
.heading {
  font-family: var(--font-serif);
  font-size: 1.875rem; /* 30px mobile */
  line-height: 1.2;
}

@media (min-width: 768px) {
  .heading {
    font-size: 2.25rem; /* 36px tablet */
  }
}

@media (min-width: 1024px) {
  .heading {
    font-size: 3rem; /* 48px desktop */
  }
}
```