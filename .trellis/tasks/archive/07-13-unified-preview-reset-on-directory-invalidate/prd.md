# Reset unified preview when directory soft cache invalidates

## Goal
invalidateUnifiedMailboxDirectoryCache resets preview soft state so deleted mailboxes cannot keep painting warm messages.

## Acceptance
- [ ] resetUnifiedMessagePreview clears signatures/loadForce/seqs
- [ ] invalidateUnifiedMailboxDirectoryCache calls reset
- [ ] contract green
