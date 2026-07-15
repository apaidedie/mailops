# Force PluginManager loadPlugins supersede soft in-flight

## Problem
loadPlugins soft-joins all in-flight; force refresh during soft load does not supersede.

## Goal
Soft joins any; force joins only force; force supersedes soft with request identity.

## Acceptance
- [ ] _pluginsLoadForce
- [ ] contract tests green
