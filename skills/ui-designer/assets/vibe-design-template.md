# Implementation Prompt Template

Use this final template after the design system and PRD are ready.

## Design System

`{项目设计指南}`

## MVP PRD

`{项目MVP PRD}`

## Task

Build implementation-ready UI that follows the design system and satisfies the
MVP PRD. Create polished, production-quality screens rather than a marketing
description.

## Requirements

- Use the existing project stack when one exists.
- Use Tailwind CSS or the local styling system if available.
- Use lucide icons when iconography is needed and the dependency exists.
- Create realistic data, empty states, loading states, and error states.
- Keep text readable on mobile and desktop.
- Ensure focus states, contrast, keyboard navigation, and touch targets are
  handled.
- Avoid generic centered layouts, default purple gradients, and interchangeable
  card-heavy UI unless the design system explicitly calls for them.

## Output Structure

- Implement screens as separate components when the project supports it.
- Keep reusable UI primitives small and local unless the repository already has
  a design system.
- Add a showcase/index page only when the user asks for variations or comparison.

## Verification

- Run the project's typecheck/build command if available.
- For browser UIs, open the result and inspect desktop and mobile viewport
  screenshots when tooling is available.
- Report any skipped verification with the reason.
