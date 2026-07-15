# Force loadPoolAdmin supersede soft in-flight

## Problem
loadPoolAdmin coalesces all same-query in-flight; force does not supersede soft.

## Goal
Soft joins any same queryKey; force joins only force; force supersedes soft.

## Acceptance
- [ ] loadForce flag
- [ ] request identity guards
- [ ] contract tests green
