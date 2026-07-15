# Frontend Development Guidelines

> Best practices for frontend development in this project.

---

## Overview

This directory contains guidelines for frontend development. Fill in each file with your project's specific conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Flask templates, static assets, feature modules | Active |
| [Component Guidelines](./component-guidelines.md) | DOM blocks, renderers, accessibility, styling | Active |
| [Hook Guidelines](./hook-guidelines.md) | Stateful helpers and data fetching patterns | Active |
| [State Management](./state-management.md) | Global state, feature state, server contracts | Active |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | Active |
| [Type Safety](./type-safety.md) | Runtime validation, JSDoc, contract tests | Active |

---

## Pre-Development Checklist

Read these before frontend changes:

- `directory-structure.md` for template/static asset ownership and script load order.
- `component-guidelines.md` for DOM contracts, renderers, accessibility, and CSS patterns.
- `hook-guidelines.md` for stateful helpers, fetches, event wiring, and browser storage.
- `state-management.md` for global state, feature state, backend contract hydration, and derived state.
- `type-safety.md` for runtime normalization, safe DOM insertion, and contract-test expectations.
- `quality-guidelines.md` for responsive layout rules, secret safety, and visual QA requirements.

## Quality Check

- Run focused Python frontend contract tests for changed templates/static assets.
- Run relevant Jest/jsdom tests for standalone JavaScript modules.
- For material layout changes, verify mobile and desktop overflow at page and container levels, and capture screenshots when a visual surface changes.
- Run `git diff --check` before commit.

---

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

---

**Language**: All documentation should be written in **English**.
