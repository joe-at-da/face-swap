# Design Principles

## Core Design Philosophy & Strategy

### Users First
Prioritize user needs, workflows, and ease of use in every design decision. The platform should feel intuitive for both parliament members and regular users, with clear pathways to accomplish their goals.

### Mobile-First Excellence
Every design decision starts with the mobile experience. With the majority of users accessing the platform via mobile devices, we prioritize thumb-friendly interactions, optimized performance, and seamless touch experiences.

### Meticulous Craft
Aim for precision, polish, and high quality in every UI element and interaction. Every pixel matters, every animation serves a purpose, and every component reflects our purple-themed brand identity.

### Speed & Performance
Design for fast load times and snappy, responsive interactions. Target < 1.5s First Contentful Paint on 3G, with immediate visual feedback for all user actions.

### Simplicity & Clarity
Strive for a clean, uncluttered interface. Ensure labels, instructions, and information are unambiguous. Complexity is hidden, functionality is obvious.

### Focus & Efficiency
Help users achieve their goals quickly and with minimal friction. Minimize unnecessary steps or distractions while maintaining powerful capabilities for parliament member interactions and video management.

### Consistency
Maintain a uniform design language using our purple-based color palette (`oklch(0.6056 0.2189 292.7172)`), Roboto/Playfair Display/Fira Code typography, and Shadcn/ui components across the entire platform.

### Accessibility (WCAG AA+)
Design for inclusivity. Ensure sufficient color contrast, keyboard navigability, and screen reader compatibility. We exceed WCAG 2.1 AA standards as the minimum baseline.

### Opinionated Design (Thoughtful Defaults)
Establish clear, efficient default workflows and settings, reducing decision fatigue for users while allowing customization where needed.

## General Best Practices

### Iterative Design & Testing
- Continuously test with users and iterate on designs
- Conduct A/B testing for critical user flows
- Gather feedback through analytics and user sessions
- Maintain a feedback loop with parliament members and regular users

### Clear Information Architecture
- Organize content and navigation logically
- Use familiar mental models and conventions
- Implement breadcrumbs for deep navigation
- Provide multiple paths to important features

### Responsive Design
- Ensure the dashboard is fully functional on all device sizes
- Test on real devices: mobile (375px), tablet (768px), desktop (1440px)
- Use fluid typography and flexible grids
- Optimize touch targets for mobile interfaces

### Documentation
- Maintain clear documentation for the design system and components
- Include usage guidelines and code examples
- Document accessibility requirements
- Keep design tokens and style guide up to date

## Module-Specific Design Principles

### Configuration Panels Module (Microsite, Admin Settings)

#### Clarity & Simplicity
- Clear, unambiguous labels for all settings using Roboto font
- Concise helper text or tooltips with `text-muted-foreground` color
- Avoid jargon - use plain language
- Use consistent terminology throughout

#### Logical Grouping
- Group related settings into sections with clear headers (Playfair Display)
- Use tabs for major configuration areas
- Apply card components (`bg-card` with `shadow-sm`) for visual separation
- Maintain consistent spacing using our 0.25rem base unit

#### Progressive Disclosure
- Hide advanced settings behind "Advanced Settings" toggle
- Use accordions for collapsible sections
- Show only essential options by default
- Implement smooth transitions (200-300ms) for reveals

#### Appropriate Input Types
- Text fields with 44px min-height for mobile
- Toggle switches for binary options
- Select dropdowns with clear options
- Sliders with visible values
- All inputs use `border-input` color and `radius-md`

#### Visual Feedback
- Immediate confirmation with toast notifications
- Success states use semantic green (`oklch(0.7 0.15 142)`)
- Error messages in destructive color (`oklch(0.6368 0.2078 25.3313)`)
- Loading states with skeleton screens
- Auto-save indicators where applicable

#### Sensible Defaults
- Provide intelligent default values
- Mark required fields clearly
- Show current values prominently
- Use placeholder text as examples, not labels

#### Reset Option
- "Reset to Defaults" button using secondary styling
- Confirmation dialog before reset
- Section-specific reset options
- Visual indication of modified settings

#### Microsite Preview
- Live or near-live preview panel
- Responsive preview options (mobile/tablet/desktop)
- Side-by-side configuration and preview on desktop
- Collapsible preview on mobile

### Data Tables Module (Contacts, Admin Settings)

#### Readability & Scannability
- **Smart Alignment**: Left-align text, right-align numbers
- **Clear Headers**: Bold Roboto headers with `font-weight: 600`
- **Zebra Striping**: Optional alternating row colors using `bg-muted/50`
- **Legible Typography**: Roboto 14px minimum for table content
- **Adequate Row Height**: Minimum 44px for mobile touch targets
- **Spacing**: Consistent padding using spacing scale (16px cells)

#### Interactive Controls
- **Column Sorting**: Clickable headers with arrow indicators
- **Sort Indicators**: Use chevron icons with smooth rotation
- **Intuitive Filtering**: Filter controls above table using form components
- **Global Search**: Prominent search bar with `bg-background` and `border-input`
- **Clear Filters**: "Clear all" option always visible

#### Large Datasets
- **Pagination**: Preferred for admin tables with page size selector
- **Page Navigation**: Previous/Next buttons with page numbers
- **Virtual Scroll**: For performance with 1000+ rows
- **Sticky Headers**: Fixed headers on scroll using `position: sticky`
- **Frozen Columns**: Lock important columns on horizontal scroll

#### Row Interactions
- **Expandable Rows**: Chevron indicator with smooth expansion
- **Inline Editing**: Click-to-edit with clear save/cancel actions
- **Bulk Actions**: Checkboxes with sticky action toolbar
- **Action Buttons**: Icon buttons (Edit, Delete, View) with tooltips
- **Hover States**: Subtle background change on row hover
- **Selection States**: Clear visual indication with `bg-primary/10`

### Multimedia Moderation Module

#### Clear Media Display
- **Grid View**: Card-based layout with consistent aspect ratios
- **List View**: Table format with thumbnails
- **Preview Size**: Large enough for content evaluation (min 200px)
- **Lazy Loading**: For performance with many images
- **Lightbox**: Full-size preview on click

#### Obvious Moderation Actions
- **Primary Actions**: Approve (primary color), Reject (destructive color)
- **Secondary Actions**: Flag, Hold for Review (secondary styling)
- **Icon Support**: Consistent icon set for quick recognition
- **Button Size**: Minimum 44px height for mobile
- **Action Grouping**: Related actions grouped together

#### Visible Status Indicators
- **Color-Coded Badges**:
  - Pending: `bg-warning` (amber)
  - Approved: `bg-success` (green)
  - Rejected: `bg-destructive` (red)
  - Flagged: `bg-info` (blue)
- **Badge Placement**: Consistent top-right corner
- **Status Text**: Clear labels alongside colors

#### Contextual Information
- **Metadata Display**: Uploader, timestamp, file size
- **Flag Count**: Visible flag indicators with count
- **User Reports**: Expandable report details
- **Content Tags**: Category/type badges
- **Typography**: Use `text-muted-foreground` for secondary info

#### Workflow Efficiency
- **Bulk Selection**: Select all/none options
- **Keyboard Shortcuts**: 
  - A: Approve
  - R: Reject
  - F: Flag
  - Space: Select
  - Arrow keys: Navigation
- **Queue Management**: Next/Previous navigation
- **Filters**: By status, date, uploader, flags
- **Batch Processing**: Progress indicators for bulk actions

#### Minimize Fatigue
- **Clean Interface**: Ample white space between items
- **Dark Mode**: Full dark mode support with reduced contrast
- **Customizable Density**: Compact/Comfortable/Spacious views
- **Break Reminders**: Optional fatigue warnings
- **Focus Mode**: Hide non-essential UI elements

## Interaction Design & Animations

### Purposeful Micro-interactions
- **Hover Effects**: Color shift using 150ms ease-in-out
- **Click Feedback**: Scale transform (0.98) on press
- **Form Submissions**: Button state changes with loading spinner
- **Status Changes**: Smooth color transitions with 200ms duration
- **Success Animations**: Brief checkmark or pulse effect

### Loading States
- **Skeleton Screens**: For page and component loads
- **Spinners**: For actions < 1 second
- **Progress Bars**: For longer operations
- **Optimistic Updates**: Update UI before server confirms
- **Loading Messages**: Context-specific messages after 2 seconds

### Transitions
- **State Changes**: 200-300ms with ease-in-out
- **Modal Appearances**: Fade in with slight scale (300ms)
- **Section Expansions**: Smooth height animations
- **Page Transitions**: Subtle fade or slide effects
- **Tab Switches**: Content fade with 150ms duration

### Animation Principles
- **Performance First**: Use GPU-accelerated properties only
- **Respect Preferences**: Honor prefers-reduced-motion
- **Subtle Enhancement**: Animations enhance, never distract
- **Consistent Timing**: Use standard duration scale
- **Natural Motion**: Follow real-world physics

### Keyboard Navigation
- **Full Keyboard Access**: All interactive elements reachable
- **Focus Indicators**: 2px solid `ring` color with offset
- **Tab Order**: Logical flow following visual hierarchy
- **Skip Links**: For navigation bypass
- **Shortcuts Documentation**: Accessible help overlay

## Layout, Visual Hierarchy & Structure

### Responsive Grid System
- **12-Column Grid**: Flexible foundation for all layouts
- **Breakpoints**:
  - Mobile: 0-767px (1-2 columns)
  - Tablet: 768-1023px (2-3 columns)
  - Desktop: 1024-1439px (3-4 columns)
  - Wide: 1440px+ (4+ columns)
- **Container Max-Width**: 1440px with auto margins
- **Gutter Width**: 16px mobile, 24px tablet, 32px desktop

### Strategic White Space
- **Component Spacing**: Use spacing scale (4px base unit)
- **Section Margins**: 48-64px between major sections
- **Breathing Room**: 24px minimum padding in cards
- **Line Height**: 1.5-1.7 for optimal readability
- **Paragraph Spacing**: 16px between paragraphs

### Clear Visual Hierarchy
- **Typography Scale**: Distinct sizes from H1-H4 and body variants
- **Color Contrast**: Primary content darkest, secondary lighter
- **Element Size**: Important elements larger
- **Position**: Critical actions above the fold
- **Visual Weight**: Bold for emphasis, light for secondary

### Consistent Alignment
- **Grid Alignment**: Snap to grid columns
- **Text Alignment**: Left-align for LTR languages
- **Number Alignment**: Right-align in tables
- **Center Alignment**: Sparingly for emphasis
- **Baseline Grid**: Align text to 4px baseline

### Main Dashboard Layout
- **Persistent Sidebar**: 
  - 280px width on desktop
  - Collapsible to icons
  - Full-screen overlay on mobile
  - Uses `bg-sidebar` with `border-sidebar-border`
- **Content Area**:
  - Flexible width with max-width constraints
  - Consistent padding (24-32px)
  - Scroll independently from sidebar
- **Top Bar** (Optional):
  - Fixed height (64px)
  - Global search with `bg-popover`
  - User menu and notifications
  - Breadcrumb navigation

### Mobile-First Considerations
- **Touch-Optimized**: All targets 44x44px minimum
- **Thumb-Friendly**: Primary actions in bottom third
- **Gesture Support**: Swipe for navigation
- **Responsive Images**: Art direction for different ratios
- **Progressive Disclosure**: Show less, reveal more

## Design System Foundation (Tokens & Core Components)

### Color Palette (OKLCH-based)

#### Primary Brand Colors
- **Primary**: `oklch(0.6056 0.2189 292.7172)` - Purple
- **Primary Foreground**: `oklch(1.0000 0 0)` - White
- **Usage**: CTAs, primary actions, active states, brand elements

#### Neutral Scale
```css
--neutral-50: oklch(0.98 0.01 293);   /* Nearly white */
--neutral-100: oklch(0.97 0.016 293); /* Light backgrounds */
--neutral-200: oklch(0.93 0.033 272); /* Borders, dividers */
--neutral-300: oklch(0.85 0.05 280);  /* Disabled states */
--neutral-400: oklch(0.70 0.08 285);  /* Placeholder text */
--neutral-500: oklch(0.54 0.12 290);  /* Secondary text */
--neutral-600: oklch(0.43 0.15 292);  /* Body text */
--neutral-700: oklch(0.35 0.13 278);  /* Headings */
--neutral-800: oklch(0.26 0.086 281); /* Dark backgrounds */
--neutral-900: oklch(0.21 0.04 265);  /* Nearly black */
```

#### Semantic Colors
- **Success**: `oklch(0.7 0.15 142)` / Dark: `oklch(0.65 0.13 142)`
- **Error/Destructive**: `oklch(0.6368 0.2078 25.3313)`
- **Warning**: `oklch(0.75 0.18 85)` / Dark: `oklch(0.7 0.16 85)`
- **Info**: `oklch(0.65 0.15 230)` / Dark: `oklch(0.6 0.13 230)`

#### Dark Mode Palette
- **Background**: `oklch(0.2077 0.0398 265.7549)` - Warm black
- **Foreground**: `oklch(0.9299 0.0334 272.7879)` - Light gray
- **Card**: `oklch(0.2573 0.0861 281.2883)` - Elevated surface
- **Reduced Contrast**: 90% brightness for comfort

#### Accessibility Requirements
- **Normal Text**: 4.5:1 contrast minimum
- **Large Text**: 3:1 contrast minimum
- **Interactive**: 3:1 contrast minimum
- **All combinations WCAG AA compliant**

### Typographic Scale

#### Font Families
- **Primary**: Roboto (body, UI elements)
- **Display**: Playfair Display (headings, emphasis)
- **Monospace**: Fira Code (code, data)

#### Modular Scale (Mobile → Desktop)
```css
H1: 30px → 48px (Playfair Display, Bold)
H2: 24px → 36px (Playfair Display, Bold)
H3: 20px → 30px (Roboto, SemiBold)
H4: 18px → 24px (Roboto, SemiBold)
Body Large: 18px → 20px (Roboto, Regular)
Body Default: 16px (Roboto, Regular)
Body Small: 14px (Roboto, Regular)
Caption: 12px (Roboto, Regular)
```

#### Font Weights
- Regular: 400
- Medium: 500
- SemiBold: 600
- Bold: 700

#### Line Heights
- Headings: 1.2
- Body: 1.5-1.7
- Captions: 1.4

### Spacing System

#### Base Unit: 4px (0.25rem)

#### Spacing Scale
```css
--space-1: 4px    /* Tight spacing */
--space-2: 8px    /* Small gaps */
--space-3: 12px   /* Component padding */
--space-4: 16px   /* Default spacing */
--space-5: 20px   /* Section gaps */
--space-6: 24px   /* Large padding */
--space-8: 32px   /* Section margins */
--space-10: 40px  /* Major gaps */
--space-12: 48px  /* Hero spacing */
--space-16: 64px  /* Page sections */
```

### Border System

#### Border Radii
```css
--radius-sm: 6px    /* Inputs, small buttons */
--radius-md: 8px    /* Default radius */
--radius-lg: 10px   /* Cards, modals (default) */
--radius-xl: 14px   /* Large cards */
--radius-2xl: 16px  /* Hero sections */
--radius-full: 9999px /* Pills, avatars */
```

#### Border Widths
- Default: 1px
- Thick: 2px
- Focus: 2px with offset

### Shadow System (Purple-tinted)

```css
--shadow-xs: 2px 2px 4px 0px hsl(255 86% 66% / 0.10);
--shadow-sm: /* Card elevation */
--shadow-md: /* Modal elevation */
--shadow-lg: /* High elevation */
--shadow-2xl: /* Maximum elevation */
```

### Core UI Components

#### Buttons
**States**: Default, Hover, Active, Focus, Disabled, Loading

**Variants**:
- **Primary**: `bg-primary` with white text, min-height 44px
- **Secondary**: `bg-secondary` with border
- **Tertiary/Ghost**: Transparent with hover state
- **Destructive**: `bg-destructive` for dangerous actions
- **Link**: Text-only with underline on hover

**Icon Support**: Leading/trailing icons with proper spacing

#### Input Fields
- **Text Input**: Single line, 44px height, `border-input`
- **Textarea**: Multi-line with resize handle
- **Select**: Dropdown with chevron indicator
- **Date Picker**: Calendar popup with mobile fallback
- **Search**: With magnifying glass icon
- **Labels**: Above field, Roboto Medium
- **Helper Text**: Below field, `text-muted-foreground`
- **Error Messages**: Below field, `text-destructive`
- **Required Indicator**: Red asterisk

#### Checkboxes & Radio Buttons
- 20x20px size with 44x44px touch target
- Custom styled with smooth transitions
- Clear checked state with primary color
- Group layouts with proper spacing

#### Toggles/Switches
- iOS-style sliding toggle
- 44px width, 24px height
- Smooth slide animation (200ms)
- Clear on/off states with colors

#### Cards
- `bg-card` background
- `border` with `radius-lg`
- `shadow-sm` for elevation
- Consistent padding (24px)
- Header/body/footer sections
- Hover state for interactive cards

#### Tables
- Clear header row with `font-semibold`
- Alternating row colors optional
- Hover states on rows
- Responsive horizontal scroll
- Sticky headers for long tables
- Action columns with icon buttons

#### Modals/Dialogs
- Centered overlay with backdrop
- `bg-popover` background
- `radius-lg` corners
- Clear header with close button
- Body with scrollable content
- Footer with action buttons
- Smooth fade-in animation

#### Navigation Elements
**Sidebar**:
- Collapsible with animation
- Icon + label format
- Active state indication
- Nested menu support

**Tabs**:
- Horizontal tab bar
- Clear active indicator
- Smooth transitions
- Icon support

#### Badges/Tags
- Pill-shaped with `radius-full`
- Color-coded by type
- Small size (20px height)
- Dismissible variant with X

#### Tooltips
- Dark background with white text
- Arrow pointing to trigger
- 8px offset from element
- Max-width 200px
- Appear on hover/focus

#### Progress Indicators
**Spinners**:
- Circular animation
- Primary color
- Multiple sizes (sm, md, lg)

**Progress Bars**:
- Horizontal bar with percentage
- Smooth animation
- Color variants for states

#### Icons
- Single icon library (Lucide/Heroicons)
- Consistent 20x20px default size
- Stroke width 1.5-2px
- Color inherits from text

#### Avatars
- Circular with `radius-full`
- Multiple sizes (32px, 40px, 48px)
- Fallback initials
- Status indicator option

## Implementation Checklist

### Before Development
- [ ] Mobile wireframes created first
- [ ] Touch targets verified (44x44px minimum)
- [ ] Color contrast checked (WCAG AA)
- [ ] Performance budget defined (< 1.5s FCP)
- [ ] Accessibility plan documented
- [ ] Component inventory completed
- [ ] Design tokens defined

### During Development
- [ ] Components from Shadcn/ui used
- [ ] Theme CSS variables applied (no hardcoded colors)
- [ ] Responsive testing on real devices
- [ ] Keyboard navigation verified
- [ ] Screen reader testing completed
- [ ] Loading states implemented
- [ ] Error states handled
- [ ] Animation performance checked

### After Development
- [ ] Lighthouse scores verified (all green)
- [ ] Cross-browser testing completed
- [ ] User testing on mobile devices
- [ ] Accessibility audit passed
- [ ] Performance monitoring active
- [ ] Documentation updated
- [ ] Design system compliance checked
- [ ] Screenshots captured with Playwright

## Design Review Criteria

### Visual Design
1. **Consistency**: Uses design tokens and purple theme consistently?
2. **Hierarchy**: Clear visual hierarchy with Playfair/Roboto typography?
3. **Balance**: Proper use of white space and grid alignment?
4. **Contrast**: Meets WCAG AA accessibility standards?
5. **Brand**: Aligns with purple-based color palette?

### Interaction Design
1. **Intuitive**: Actions obvious without instruction?
2. **Feedback**: All interactions provide immediate feedback?
3. **Responsive**: Works across all breakpoints (mobile-first)?
4. **Accessible**: Keyboard and screen reader friendly?
5. **Performant**: Meets performance budget (< 1.5s FCP)?

### Content Design
1. **Scannable**: Easy to scan with clear typography hierarchy?
2. **Concise**: No unnecessary words, clear labels?
3. **Helpful**: Error messages actionable with next steps?
4. **Consistent**: Same terminology throughout?
5. **Accessible**: Reading level appropriate, min 14px text?

### Component Quality
1. **Shadcn/ui First**: Using existing components?
2. **Theme Compliance**: Only CSS variables used for colors?
3. **Mobile Optimized**: 44px touch targets maintained?
4. **State Coverage**: All states (hover, focus, disabled) defined?
5. **Documentation**: Usage guidelines provided?

## Platform-Specific Optimizations

### iOS Optimization
- Input font-size: 16px (prevents zoom)
- -webkit-tap-highlight-color: transparent
- Safe area insets for notched devices
- Momentum scrolling: -webkit-overflow-scrolling: touch
- Native-feeling interactions

### Android Optimization
- Material Design influences where appropriate
- System font stack fallbacks
- Proper viewport configuration
- Touch feedback via ripple effects
- Appropriate keyboard types

### Desktop Optimization
- Hover states for all interactive elements
- Right-click context menus where useful
- Keyboard shortcuts for power users
- Dense information layouts available
- Multi-column layouts for wide screens

## Maintenance & Evolution

### Design Debt Management
- Monthly consistency audits
- Component consolidation reviews
- Performance regression testing
- Accessibility regression testing
- Design token updates

### Innovation Framework
1. **Identify**: User pain point or opportunity
2. **Prototype**: Low-fidelity mobile-first
3. **Test**: With real users on mobile devices
4. **Refine**: Based on feedback and metrics
5. **Document**: Add to design system

### Continuous Improvement
- Weekly design reviews
- Monthly accessibility audits
- Quarterly performance reviews
- Bi-annual user testing sessions
- Annual design system overhaul

### Quality Metrics
- **Performance**: Core Web Vitals green
- **Accessibility**: WCAG AA compliance 100%
- **Consistency**: Design token usage > 95%
- **Mobile**: Touch target compliance 100%
- **User Satisfaction**: NPS > 50