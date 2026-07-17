# Implement — UI workflow polish A–E

## Order (strict)

1. Start **A** only → implement → check → commit/push → CI green  
2. Then **B** → …  
3. **C** → **D** → **E**  
4. Parent acceptance + optional archive children  

Do **not** `task.py start` the parent for implementation; start the active child.

## Per-child checklist template

```
[ ] task.py start <child>
[ ] trellis-before-dev (frontend layer)
[ ] Implement thin pass per child prd
[ ] Update frontend contracts in same change set
[ ] black --check on touched tests
[ ] Run targeted unittest modules
[ ] Commit + push
[ ] CI: Code Quality + Python Tests green
[ ] task.py finish / archive when child accepted
```

## Validation commands (repo root)

```powershell
python -m unittest tests.test_v190_frontend_contract -v
python -m unittest tests.test_overview_frontend_contract tests.test_unified_mailbox_frontend_contract -v
python -m black --check tests/
```

(Add child-specific modules as needed.)

## Risky files

| File | Why |
|------|-----|
| `static/js/features/mailboxes/render.js` | Large unified chrome |
| `static/js/core/state/external_api_ui_*.js` | Command center coupling |
| `templates/index.html` | Shared shell + many pages |
| `tests/test_*frontend*contract*.py` | Brittle string asserts |

## Rollback points

- Each child commit is a rollback unit.
- Prefer not to mix A+C in one commit.

## Parent final check

- [ ] A–E acceptance in each prd  
- [ ] No default “指挥台/command center” hero on primary ops pages  
- [ ] Import / group / mailbox / temp / API key still reachable ≤3 clicks  
- [ ] Advanced sections still expandable  
- [ ] Publish CI green on latest main  

## Superpowers design mirror

After design approval, also write:

`docs/superpowers/specs/2026-07-18-ui-workflow-polish-ae-design.md`

(extends `2026-07-17-ui-simplify-workflow-b-design.md`)
