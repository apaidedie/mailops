# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory contains guidelines for backend development. Fill in each file with your project's specific conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | Active |
| [Database Guidelines](./database-guidelines.md) | SQLite, repositories, migrations | Active |
| [Error Handling](./error-handling.md) | Error envelopes, trace IDs, external API errors | Active |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | Active |
| [Logging Guidelines](./logging-guidelines.md) | Runtime logs, audit logs, secret safety | Active |
| [Provider Selection Contract](./provider-selection-contract.md) | Mailbox provider discovery and selection policy API contract | Active |

---

## Pre-Development Checklist

Read these before backend changes:

- `directory-structure.md` for route/controller/service/repository ownership.
- `database-guidelines.md` when touching persistence, migrations, settings, or SQLite queries.
- `error-handling.md` when adding API errors, response envelopes, guards, or validation.
- `logging-guidelines.md` when adding diagnostics, audit events, or exception logging.
- `quality-guidelines.md` for backend tests, route aliases, secret safety, and release gates.
- `provider-selection-contract.md` for mailbox provider, external API, unified mailbox, or integration readiness work.

## Quality Check

- Verify changed code respects route -> controller -> service -> repository boundaries.
- Run focused tests for touched API/service contracts.
- Run `python scripts/project_readiness_check.py` when integration docs, provider onboarding, examples, OpenAPI, readiness checks, or secret-scanned assets change.
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
