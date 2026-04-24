# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**IMPORTANT: This project runs entirely via Docker Compose. Do NOT use `pnpm dev` or `npx supabase start` directly.**

- **Start everything**: `./setup-worktree.sh` — starts Next.js, Supabase, Mailpit, and all services, runs migrations and seeds the database
- **Stop everything**: `./cleanup-worktree.sh` — stops containers and removes volumes
- `pnpm build` - Build production application with Turbopack
- `pnpm lint` - Run ESLint for code quality checks
- `pnpm genTypes` - Generate TypeScript types from local Supabase instance

### Supabase Local Development

**Supabase runs as part of the Docker Compose stack — do NOT use `npx supabase start`/`stop`.**

- `supabase migration new migration_name` - Create new migration file
- Apply migrations: `PGSSLMODE=disable npx supabase db push --db-url 'postgres://postgres:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/postgres' --include-all`
- After successful migration: `pnpm genTypes` - Update TypeScript types from database
- Seed data: `supabase/seed.sql` is automatically applied by `setup-worktree.sh` (parliament members, clips, events, etc.)

### Email Testing with Mailpit

When running local Supabase, all emails (magic links, OTPs, password resets, etc.) are captured by Mailpit:

- **Mailpit Web Interface**: http://127.0.0.1:55324
- **Use for testing**: Magic link authentication, OTP verification, password resets
- **Email capture**: All Supabase Auth emails are automatically routed to Mailpit
- **No real emails sent**: Safe for development and testing without sending actual emails

### Docker Development Environment

This project uses Docker Compose (`docker-compose.development.yml`) for local development with a complete Supabase stack. **This is the only supported way to run the app locally.**

**Setup:**
1. Run `./setup-worktree.sh` to auto-configure unique ports for your directory
2. The script creates/updates `.env` with calculated ports and generates required secrets
3. Starts all services via `docker compose -f docker-compose.development.yml up -d`
4. Runs Supabase migrations automatically
5. Seeds the database with parliament data from `supabase/seed.sql`

**Teardown:**
- Run `./cleanup-worktree.sh` to stop containers and remove volumes
- Use `./cleanup-worktree.sh --keep-volumes` to stop containers but keep database data

**Access Points (ports auto-configured by setup-worktree.sh):**
- Next.js App: `http://localhost:${NEXTJS_PORT}` (default: 3001)
- Supabase Studio: `http://localhost:${KONG_PORT}` (default: 8000)
- PostgreSQL: `localhost:${POSTGRES_PORT}` (default: 5432)

**Executing Commands:**
Since the project directory is mounted into the container, you can run pnpm commands either on the host or in the container:

- **On host (recommended)**: Run `pnpm add`, `pnpm lint`, etc. directly - changes sync to container automatically
- **In container**: Use when you need the container's Node environment or don't have pnpm locally:
  - Enter container: `docker exec -it ${COMPOSE_PROJECT_NAME}-nextjs-app sh`
  - Run directly: `docker exec -it ${COMPOSE_PROJECT_NAME}-nextjs-app pnpm <command>`

**IMPORTANT**: Never run `pnpm dev` or `npx supabase start` on the host — the dev server and Supabase run inside Docker containers.

**Common Docker Commands:**
- View logs: `docker compose -f docker-compose.development.yml logs -f`
- View Next.js logs: `docker compose -f docker-compose.development.yml logs -f nextjs-app`
- Stop services: `docker compose -f docker-compose.development.yml down`
- Restart: `docker compose -f docker-compose.development.yml down && docker compose -f docker-compose.development.yml up -d`

**setup-worktree.sh Options:**
- `./setup-worktree.sh` - Standard setup
- `./setup-worktree.sh --force` - Force full setup even if services are running
- `./setup-worktree.sh --live` - Stream Next.js logs after setup

## Architecture Overview

This is a **full-stack Next.js 15 application** using the App Router, built for parliament member interaction and video clip management. The project integrates with Supabase for authentication, database, and storage.

**Deployment Architecture:**
- **Self-hosted on Coolify** - Both Next.js and Supabase are self-hosted on a Coolify server
- **Full-stack architecture** - Next.js handles both frontend and backend operations
- **Backend Implementation** - Uses Next.js Server Actions and API routes (`app/api/`) for server-side logic
- **UI Framework** - Shadcn/ui components for consistent, accessible user interface
- **Database** - Supabase with migrations stored in `@/supabase/migrations/`

**Application Purpose:**
The MP AI website allows UK MPs and their staff to create, search, and share clips of UK MPs from parliament sessions. Features include:
- AI-powered search by topic, context, or specific statements
- Social media scheduling and analytics for clips
- MP following system with notifications when MPs speak in parliament
- Watermark functionality for created clips

### Key Architectural Patterns

**Route Structure:**

- `app/(publicPages)/` - Public routes accessible without authentication
- `app/(privatePages)/` - Protected routes requiring authentication
- `app/api/` - API routes including cron jobs for parliament data sync

**Authentication & Authorization:**

- Middleware-based auth using Supabase SSR
- Special handling for parliament.uk email addresses (redirect to `/mp-setup`)
- Regular users go through `/setup` on first login
- Protected routes: `/dashboard`, `/setup`, `/mp-setup` and `/dashboard/*`

**Data Layer:**

- Supabase integration with separate client configurations:
  - `@/supabase/supabaseServerClient.ts` - Server-side operations
  - `@/supabase/supabaseBrowserClient.ts` - Client-side operations  
  - `@/supabase/supabaseAdmin.ts` - Admin operations
- Supabase migrations located in `@/supabase/migrations/`
- Generated TypeScript types in `@/supabaseTypes.ts`
- Parliament API integration with rate limiting (4 requests/burst, 500ms intervals)

**State Management:**

- Uses Legend State v3 (`@legendapp/state`) for client state management
- Store files should be placed in `stores/` directory and accessed via `@/stores` alias
- React Hook Form with Zod validation for forms
- Schemas defined in `schemas/` directory

### Component Architecture

**UI Framework:**

- Shadcn/ui components with Radix UI primitives
- Tailwind CSS v4 for styling
- Components configured for "new-york" style with CSS variables
- All UI components located in `components/ui/`

**Component Organization:**

- **Shared components** used across multiple pages → `@/components/` directory
- **Page-specific components** used in only one page → Place in the same folder as the page in `@/app/`
- Example: A component only used in `/dashboard` should be in `@/app/(privatePages)/dashboard/components/`
- Example: A reusable header component should be in `@/components/header.tsx`

**Component Size Guidelines:**

- **AVOID large components** - Large components are very hard to manage, debug, and maintain
- **ALWAYS break down complex components** into smaller, focused, manageable components
- **Single Responsibility Principle** - Each component should have one clear purpose
- **Aim for components under 100 lines** when possible
- **Extract reusable logic** into custom hooks or utility functions
- **Split UI sections** into separate components even within the same page
- Example: A large form should be split into multiple smaller form sections, each as its own component

**Codebase Cleanup Guidelines:**

- **MANDATORY cleanup after every task** - Always clean up after completing any development task
- **RUN LINT AFTER EVERY CODE CHANGE** - Always run `pnpm lint` after any code changes and fix all linting errors before considering the task complete
- **Remove unused files** - Delete any temporary files, test files, or components that are no longer needed
- **Remove unused code** - Clean up unused imports, dead code, commented-out sections, and unreferenced functions
- **Remove unused dependencies** - Check package.json and remove any packages that are no longer used
- **Clean up development artifacts** - Remove console.logs, debugging code, TODO comments, and temporary variables
- **Organize file structure** - Ensure files are in the correct directories according to the component organization guidelines
- **Update imports** - Ensure all imports use the correct `@` alias paths after moving or refactoring components
- **Verify functionality** - Test that all features still work after cleanup and refactoring
- **Example cleanup checklist:**
  - Delete old component files after splitting them into smaller ones
  - Remove unused imports from refactored files
  - Clean up any debugging console.logs added during development
  - **Run `pnpm lint` and fix all reported issues**
  - Verify no broken import paths exist
  - Remove any temporary test components or files

**Server vs Client Components:**

- **ALWAYS use Server Components by default** for pages and components
- **Only use Client Components when absolutely necessary** (interactivity, browser APIs, state, event handlers)
- **When client-side functionality is needed:**
  - Isolate the interactive parts into the smallest possible component
  - Mark only that specific component with `"use client"`
  - Keep the parent component as a Server Component
  - Example: A page with a form should have the form as a separate client component, not the entire page

**Loading and Error Page Requirements:**

- **MANDATORY: Create skeleton loading pages for ALL routes** - Every page MUST have a corresponding `loading.tsx` file
- **MANDATORY: Create error pages for ALL routes** - Every page MUST have a corresponding `error.tsx` file  
- **MANDATORY: Add Suspense boundaries for async server components** - Any server component with `await` or async operations MUST be wrapped in `<Suspense>` with fallback
- **Loading State Guidelines:**
  - Use Shadcn/ui Skeleton components for loading states
  - Match the layout structure of the actual content
  - Maintain visual consistency with theme colors
  - Show appropriate loading duration (skeleton screens for <3 seconds, spinners for quick operations)
- **Error Handling Guidelines:**
  - Create user-friendly error messages
  - Include retry functionality where appropriate
  - Log errors to Glitchtip using established error logging patterns
  - Provide fallback content or navigation options
- **File Structure:**
  ```
  app/(privatePages)/dashboard/
  ├── page.tsx
  ├── loading.tsx    ← REQUIRED
  ├── error.tsx      ← REQUIRED
  └── components/
  ```
- **Suspense Implementation:**
  ```tsx
  // For any async server component
  <Suspense fallback={<ComponentSkeleton />}>
    <AsyncServerComponent />
  </Suspense>
  ```

**Key Services:**

- `services/parliament/` - Parliament API integration and data transformation
- Rate-limited API calls with retry logic and burst control
- Cron jobs for automated parliament data synchronization

## Development Guidelines

### Testing

- Playwright configured for E2E testing in `tests/` directory
- **E2E Test Guide**: See `tests/e2e/CLAUDE.md` for conventions on auth fixtures, test data cleanup, Mailpit email helpers, rate limit avoidance, and test organization
- Example tests available in `tests-examples/`

**Test Commands:**
- `pnpm test:e2e` - Run all E2E tests with HTML report
- `pnpm test:e2e:headless` - Run tests without blocking (for automation/CI)
- `pnpm test:e2e:ui` - Interactive UI mode for test development
- `pnpm test:e2e:debug` - Debug mode with browser dev tools

**Test-Automator Agent Fix:**
When using the test-automator agent, always use `PLAYWRIGHT_HEADLESS_REPORT=true` or the `pnpm test:e2e:headless` command to prevent the HTML report server from hanging the process. See `TEST_AUTOMATOR_FIX.md` for detailed documentation.

### Database Operations & Migrations

**Migration Workflow:**
1. **ALWAYS** use Context7 MCP tools first to get up-to-date Supabase migration syntax and best practices
2. Create new migration: `supabase migration new migration_name`
3. Write migration SQL in the created file in `@/supabase/migrations/`
4. Apply migration locally: `supabase db push --local`
5. If errors occur:
   - Edit the migration file to fix issues
   - Re-apply with `supabase db push --local`
6. After successful migration: Run `pnpm genTypes` to update TypeScript types

**Important Locations:**
- Supabase clients: `@/supabase/` directory
- Migration files: `@/supabase/migrations/`
- TypeScript types: `@/supabaseTypes.ts`
- Local config: `supabase/config.toml`

### API Integration

- Parliament API service includes sophisticated rate limiting
- All external API calls should follow the error handling patterns in `lib/getErrorMessage.ts`
- Server-only operations must import `"server-only"`

### Error Handling and Logging

**Glitchtip Integration:**
This project uses Glitchtip (compatible with Sentry SDK) for comprehensive error monitoring and logging.

- **ALL errors (server-side and client-side) must be logged to Glitchtip**
- Use proper error logging patterns for both Server Components and Client Components
- Follow the error handling patterns established in `lib/getErrorMessage.ts` and `lib/errorLogger.ts`
- Ensure sensitive information is not logged while maintaining useful debugging context

**Error Logging Utilities:**
- `ErrorLogger.logError()` - General error logging with context
- `ErrorLogger.logAuthError()` - Authentication-specific errors
- `ErrorLogger.logApiError()` - API request/response errors
- `ErrorLogger.logDatabaseError()` - Database operation errors
- `ErrorLogger.logClientError()` - React component errors
- `ErrorLogger.logEvent()` - Custom events and monitoring
- `handleError()` - Enhanced error handler that logs to Glitchtip and returns user-friendly messages

**Error Boundaries:**
- Root layout includes `ErrorBoundary` component for catching React errors
- Use `withErrorBoundary` HOC for wrapping specific components
- Use `useErrorHandler` hook for error handling in functional components

**Configuration:**
- Client config: `sentry.client.config.ts`
- Server config: `sentry.server.config.ts` 
- Edge config: `sentry.edge.config.ts`
- Global instrumentation: `instrumentation.ts`

**Environment Variables:**
- `NEXT_PUBLIC_GLITCHTIP_DSN` - Public DSN for client-side error reporting
- `GLITCHTIP_DSN` - Server-side DSN for backend error reporting
- Optional: `SENTRY_ORG`, `SENTRY_PROJECT`, `SENTRY_AUTH_TOKEN` for source map uploads

### Form Handling

**ALWAYS use Shadcn/ui Form components with Zod validation for all forms.**

- Use `@/components/ui/form` for form components (built on React Hook Form)
- Zod schemas are stored in `schemas/` directory and accessed via `@/schemas` alias
- Form components should leverage the existing validation patterns in `@/schemas`
- Follow Shadcn/ui form patterns with proper error handling and accessibility
- Examples: `@/schemas/authSchema.ts`, `@/schemas/settingsSchema.ts`

### File Structure Notes

- Path aliases configured: `@/*` maps to project root
- **IMPORTANT: All imports in TypeScript files MUST use the `@` alias**
  - ✅ Correct: `import { Button } from "@/components/ui/button"`
  - ❌ Wrong: `import { Button } from "../../../components/ui/button"`
  - ❌ Wrong: `import { Button } from "./components/ui/button"`
- Components, utils, lib, hooks, stores, and schemas have dedicated alias mappings
- **Component placement:**
  - Shared components → `@/components/` directory
  - Page-specific components → Place in the same folder as the page in `@/app/`
- **Component types:**
  - Server components (default) → Use `createSupabaseServerClient()`
  - Client components (only when needed) → Use browser client from `@/supabase/supabaseBrowserClient.ts`
  - Always prefer Server Components and isolate client functionality to minimal components
- Store files should be placed in `stores/` directory and imported via `@/stores`
- Zod schemas should be placed in `schemas/` directory and imported via `@/schemas`

## Documentation and Resources

### Getting Up-to-Date Documentation

When working with libraries and frameworks in this project, use the Context7 MCP tools to get current documentation:

- Use `mcp__context7__resolve-library-id` to find the correct library ID for any package
- Use `mcp__context7__get-library-docs` to fetch up-to-date documentation and examples

Key libraries to reference:

- Next.js (`/vercel/next.js`) - App Router patterns, middleware, API routes
- **Supabase (`/supabase/supabase`)** - Auth, database operations, SSR patterns, **migrations syntax**
- React Hook Form (`/react-hook-form/react-hook-form`) - Form handling patterns
- Zod (`/colinhacks/zod`) - Schema validation
- Tailwind CSS (`/tailwindlabs/tailwindcss`) - Styling patterns
- Legend State (`/legendapp/legend-state`) - State management patterns and v3 features

**IMPORTANT for Supabase Migrations:**
- Always use `mcp__context7__get-library-docs` with `/supabase/supabase` to get current migration syntax
- Topics to query: "migrations", "RLS policies", "triggers", "functions", "indexes"
- This ensures migrations use the latest Supabase SQL patterns and best practices

### Shadcn/ui Components

**ALWAYS use Shadcn/ui components for UI elements.** This project is configured with Shadcn/ui and has extensive components available.

- Use `mcp__shadcn__getComponents` to list all available Shadcn/ui components
- Use `mcp__shadcn__getComponent` to get detailed information and examples for specific components
- All Shadcn/ui components are located in `components/ui/`
- Components are configured for "new-york" style with CSS variables
- Never create custom UI components when a Shadcn/ui equivalent exists

### Local Website Testing

Use Playwright MCP tools to browse and test the local website:

- Use `mcp__playwright__browser_navigate` to navigate to `http://localhost:3000`
- Use `mcp__playwright__browser_snapshot` to capture page state for analysis
- Use `mcp__playwright__browser_click`, `mcp__playwright__browser_type` for interactions
- Use `mcp__playwright__browser_take_screenshot` to capture visual state when needed

## Visual Development & Design System

### Style Guide & Design Principles

**CRITICAL: Always follow the established design system:**

- **Style Guide**: `.claude/style-guide.md` - Contains typography, colors, spacing, components patterns
- **Design Principles**: `.claude/design-principles.md` - Mobile-first approach, accessibility standards, interaction patterns
- **Review both documents before any UI implementation**

### Color Usage Guidelines

**NEVER hardcode colors. ALWAYS use CSS variables from the theme:**

❌ **WRONG - Never do this:**

```jsx
// Never hardcode Tailwind colors
<div className="bg-purple-600 text-white">
<button className="bg-blue-500 hover:bg-blue-600">

// Never use inline color styles
<div style={{ backgroundColor: '#7c3aed' }}>
```

✅ **CORRECT - Always do this:**

```jsx
// Use theme CSS variables via Tailwind classes
<div className="bg-primary text-primary-foreground">
<button className="bg-secondary hover:bg-secondary/90">
<div className="border-border bg-card text-card-foreground">

// Available theme color classes:
// bg-background, bg-foreground
// bg-primary, bg-primary-foreground
// bg-secondary, bg-secondary-foreground
// bg-muted, bg-muted-foreground
// bg-accent, bg-accent-foreground
// bg-destructive, bg-destructive-foreground
// bg-card, bg-card-foreground
// bg-popover, bg-popover-foreground
// border-border, border-input, ring-ring
// For charts: bg-chart-1 through bg-chart-5
// For sidebar: bg-sidebar, bg-sidebar-foreground, etc.
```

**Theme colors are defined in `app/globals.css` using OKLCH color space for perceptual uniformity and automatic dark mode support.**

### UI Verification Requirements

**MANDATORY: After ANY frontend changes, you MUST:**

1. **Take Screenshots**: Use `mcp__playwright__browser_take_screenshot` to capture the UI
2. **Verify Appearance**: Check if the UI looks good and matches design principles
3. **Iterate if Needed**: If the UI doesn't look good, make improvements and re-verify
4. **Test Responsiveness**: Check mobile (375px), tablet (768px), and desktop (1440px) viewports
5. **Verify Dark Mode**: Toggle dark mode and ensure proper color contrast

**Visual Verification Workflow:**

```
1. Make UI changes
2. Navigate to page with `mcp__playwright__browser_navigate`
3. Take screenshot with `mcp__playwright__browser_take_screenshot`
4. Assess against style guide and design principles
5. If issues found:
   - Fix the issues
   - Return to step 2
6. Document the final screenshot for reference
```

### Component Edit Workflow with Design Review

**MANDATORY: When editing ANY component, you MUST follow this workflow:**

1. **Take BEFORE Screenshot**: 
   - Navigate to the page containing the component
   - Take a screenshot with `mcp__playwright__browser_take_screenshot` to capture current state
   - Document this as the "before" state

2. **Make Component Changes**: 
   - Edit the component code following all established guidelines
   - Ensure proper theming, accessibility, and mobile-first approach

3. **Take AFTER Screenshot**:
   - Navigate to the page with the updated component
   - Take a screenshot with `mcp__playwright__browser_take_screenshot` to capture new state
   - Document this as the "after" state

4. **Design Review with Agent**:
   - Launch the design-reviewer agent using the Task tool
   - Provide both before/after screenshots for comparison
   - Request comprehensive design review focusing on:
     - Visual consistency and improvement
     - Accessibility compliance
     - User experience quality
     - Responsive design effectiveness
     - Design system adherence
   - **TARGET: Achieve 10/10 design rating**

5. **Iterate Based on Feedback**:
   - If design review identifies issues or gives < 10/10 rating:
     - Address all feedback and suggestions
     - Repeat steps 3-4 until achieving 10/10 rating
   - Only consider the component edit complete when design review gives 10/10

**Example Usage:**
```
Task: "Edit the login form component"
1. Take screenshot of current login form
2. Edit the component (improve styling, accessibility, etc.)
3. Take screenshot of updated login form
4. Launch design-reviewer agent with both screenshots
5. Address any feedback until 10/10 rating achieved
```

This ensures every component edit results in measurable design improvement and maintains world-class UI standards.

### Quick Visual Check

IMMEDIATELY after implementing any front-end change:

1. **Identify what changed** - Review the modified components/pages
2. **Navigate to affected pages** - Use `mcp__playwright__browser_navigate` to visit each changed view
3. **Take screenshots** - Capture current state with `mcp__playwright__browser_take_screenshot`
4. **Verify design compliance** - Compare against `.claude/design-principles.md` and `.claude/style-guide.md`
5. **Check theme colors** - Ensure only CSS variables are used, no hardcoded colors
6. **Test interactions** - Verify hover states, focus states, and animations work correctly
7. **Validate responsiveness** - Check mobile, tablet, and desktop breakpoints
8. **Capture evidence** - Take full page screenshot at desktop viewport (1440px) of each changed view
9. **Check for errors** - Run `mcp__playwright__browser_console_messages`
10. **Iterate if needed** - If UI doesn't meet standards, improve and re-verify

This verification ensures changes meet design standards and user requirements.

### Mobile-First Development

**ALWAYS develop with mobile-first approach:**

- Start designs at 375px viewport
- Progressive enhancement for larger screens
- Touch targets minimum 44x44px
- Test on actual mobile viewport sizes
- Ensure text is readable without zooming (min 14px)

### Accessibility Requirements

**Every UI component MUST be accessible:**

- Keyboard navigable (test with Tab key)
- Screen reader compatible (proper ARIA labels)
- Color contrast meets WCAG AA (4.5:1 for normal text)
- Focus indicators visible and clear
- Error messages associated with form fields

### Component Consistency

**Use Shadcn/ui components and follow patterns:**

- Never create custom components if Shadcn/ui has equivalent
- Follow established patterns from style guide
- Maintain consistent spacing (0.25rem base unit)
- Use standard border radius (0.625rem default)
- Apply theme shadows for elevation

### Performance Considerations

**Optimize for mobile performance:**

- Lazy load images below the fold
- Use responsive image sizes
- Minimize JavaScript bundle size
- Implement skeleton screens for loading states
- Target < 1.5s First Contentful Paint on 3G

## Local Development Notes

- **ALWAYS use `./setup-worktree.sh` to start** and `./cleanup-worktree.sh` to stop the local environment
- **NEVER run `pnpm dev`** — the Next.js dev server runs inside the Docker container
- **NEVER run `npx supabase start`/`stop`** — the complete Supabase stack (DB, Auth, Storage, Kong, Studio) runs via `docker-compose.development.yml`
- The database is automatically seeded with parliament data (members, clips, events, etc.) on first setup
- To regenerate the seed file from production: `./scripts/generate-seed.sh`