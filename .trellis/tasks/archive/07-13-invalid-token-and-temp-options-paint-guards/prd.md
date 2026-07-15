# Invalid-token + temp options paint guards

## Goal
Paint invalid-token governance only while refresh modal is open; paint temp domain options only on temp-emails page with matching provider.

## Done
- [x] loadInvalidTokenGovernanceCandidates modal paint guard + always warm cache
- [x] shouldPaintTempEmailOptions + loadTempEmailOptions paint guard
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
