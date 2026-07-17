# A: Mailbox Main Path Polish — Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** On mailbox **standard/compact** paths, empty states expose one primary next action (add group / import account / fetch mail).

**Architecture:** Thin pass only — inject CTA buttons into existing empty-state HTML builders; reuse `showAddGroupModal`, `showAddAccountModal`, `refreshEmails`. No backend changes; no unified command-center work (child C).

**Tech Stack:** Vanilla JS feature modules, Flask templates (unchanged structure), Python frontend contract tests.

## Global Constraints

- Collapse/add CTAs only; do not delete features or critical element ids  
- Do not change unified layout chrome (child C) or sidebar shell (child E)  
- Keep mode labels `统一工作台` / `账号视图` / `紧凑视图`  
- Topbar remains title `邮箱` with empty subtitle  
- Update contracts in the same change set  

## File map

| File | Change |
|------|--------|
| `static/js/features/groups/render.js` | Empty groups → 添加分组; empty accounts → 导入账号 |
| `static/js/features/emails/render.js` | Cold + empty list → 获取邮件 |
| `static/js/features/accounts/actions.js` | Cold empty → 获取邮件 |
| `static/js/features/mailbox_compact.js` | Compact empty groups/accounts CTAs |
| `tests/test_v190_frontend_contract.py` | Assert empty CTAs in groups/emails packages |
| `tests/test_v191_compact_mode_frontend_contract.py` | Assert compact empty CTAs |

---

### Task 1: Standard empty-state CTAs

**Files:**
- Modify: `static/js/features/groups/render.js`
- Modify: `static/js/features/emails/render.js`
- Modify: `static/js/features/accounts/actions.js`

- [ ] **Step 1: Groups empty + accounts empty**

In `renderGroupList` when `filteredGroups.length === 0`, use:

```javascript
container.innerHTML = `
    <div class="empty-state">
        <span class="empty-icon">📁</span>
        <p class="ui-empty-title">${translateAppTextLocal('暂无分组')}</p>
        <button type="button" class="btn btn-primary btn-sm" onclick="showAddGroupModal()">${translateAppTextLocal('添加分组')}</button>
    </div>
`;
```

In `renderAccountList` when `accounts.length === 0`, replace desc-only block with title + button:

```javascript
container.innerHTML = `
    <div class="empty-state">
        <span class="empty-icon" aria-hidden="true"></span>
        <p class="ui-empty-title">${translateAppTextLocal('该分组暂无邮箱')}</p>
        <button type="button" class="btn btn-primary btn-sm" onclick="showAddAccountModal()">${translateAppTextLocal('导入账号')}</button>
    </div>
`;
```

- [ ] **Step 2: Email cold + empty list**

In `paintEmailListColdFetchPrompt` and empty branch of `renderEmailList`, add:

```html
<button type="button" class="btn btn-primary btn-sm" onclick="refreshEmails()">${translateAppTextLocal('获取邮件')}</button>
```

Shorten/remove “点击右上角…” desc when button is present (title only is fine).

In `accounts/actions.js` cold empty (尚未加载邮件), same CTA pattern.

- [ ] **Step 3: Commit standard path** (optional mid-commit; may batch with Task 2)

---

### Task 2: Compact empty-state CTAs

**Files:**
- Modify: `static/js/features/mailbox_compact.js`

- [ ] **Step 1: Compact no groups**

When `visibleGroups.length === 0`, render empty with button `showAddGroupModal()` labeled 添加分组 (use `translateCompactText` for strings already going through compact translator).

- [ ] **Step 2: Compact no accounts**

When accounts empty, use empty-state with title + `showAddAccountModal()` 导入账号.

---

### Task 3: Contract tests

**Files:**
- Modify: `tests/test_v190_frontend_contract.py`
- Modify: `tests/test_v191_compact_mode_frontend_contract.py`

- [ ] **Step 1: Add assertions**

```python
# v190 — groups empty CTA
groups_js = load_feature_package_js("static/js/features/groups")
self.assertIn('onclick="showAddGroupModal()"', groups_js)
self.assertIn('onclick="showAddAccountModal()"', groups_js)

# v190 — emails empty CTA
emails_js = load_feature_package_js("static/js/features/emails")
self.assertIn('onclick="refreshEmails()"', emails_js)
self.assertIn("translateAppTextLocal('获取邮件')", emails_js)

# v191 compact
compact_js = self._get_text(client, "/static/js/features/mailbox_compact.js")
# or load file content
self.assertIn("showAddGroupModal()", compact_js)
self.assertIn("showAddAccountModal()", compact_js)
```

Place in a dedicated small test method if cleaner.

- [ ] **Step 2: Run tests**

```powershell
python -m unittest tests.test_v190_frontend_contract tests.test_v191_compact_mode_frontend_contract -v
python -m black --check tests/test_v190_frontend_contract.py tests/test_v191_compact_mode_frontend_contract.py
```

Expected: OK

- [ ] **Step 3: Commit**

```bash
git add static/js/features/groups/render.js static/js/features/emails/render.js static/js/features/accounts/actions.js static/js/features/mailbox_compact.js tests/test_v190_frontend_contract.py tests/test_v191_compact_mode_frontend_contract.py docs/superpowers/plans/2026-07-18-ui-polish-a-mailbox.md
git commit -m "feat(ui): mailbox empty-state next-action CTAs (polish A)"
```

## Spec coverage

| PRD | Task |
|-----|------|
| A1 standard/compact focus | Unchanged layout; CTAs reinforce path |
| A2 topbar | No change (already quiet) |
| A3 no extra essays | Remove cold “点击右上角” desc in favor of button |
| A4 empty next action | Tasks 1–2 |
| A5 contracts | Task 3 |

## Out of scope (do not implement)

- Unified command center / Setup Path  
- Import modal format hints  
- Sidebar nav renames  
