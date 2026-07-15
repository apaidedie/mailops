# Plugins list paint only when card expanded

## Goal
Temp-mail Settings soft-preload of plugins must not flash/repaint plugin manager list chrome while the collapsible card is collapsed.

## Done
- [x] shouldPaintPluginList() based on _cardExpanded
- [x] loadPlugins / ensureLoaded / language soft-paint gated
- [x] catalog/radio/select side effects still run after network success
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
