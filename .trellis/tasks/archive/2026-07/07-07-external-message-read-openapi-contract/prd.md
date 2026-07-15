# External message read OpenAPI contract

## Goal

External clients should get a stable, typed OpenAPI contract for the message-reading and verification endpoints that actually power third-party mailbox automation.

## Background

The project already exposes a unified mailbox directory, provider discovery, health readiness, pool workflows, task temp-mail workflows, and OpenAPI. The remaining friction is that core read endpoints still have loose schemas for message detail, raw content, verification extraction, async probe status, and account status. Generated clients can discover endpoints but cannot rely on a strong response model for the high-value read path.

## Requirements

- Keep existing endpoint paths and runtime payloads compatible.
- Replace loose OpenAPI schemas for external read responses with typed schemas that match current runtime fields.
- Cover list messages, latest message, message detail, raw message content, verification code/link results, wait-message async probe status, and account status.
- Keep schemas secret-free and avoid documenting credential fields.
- Update backend provider-selection spec and tests so future read-contract changes stay aligned.

## Acceptance Criteria

- OpenAPI defines typed schemas for MessageSummary, MessageDetail, RawMessageData, VerificationResult, ProbeStatusData, and AccountStatusData.
- `/api/external/messages/{message_id}/raw` references RawMessageData instead of the broad MessageDetail schema.
- Verification code/link OpenAPI response schema requires stable fields such as formatted, verification_code, verification_link, confidence, matched_email_id, method, folder, and channel.
- Account status OpenAPI schema documents existing status/readability/probe fields without exposing secrets.
- Tests prove the schema refs and required fields are present.
- Focused external API tests pass and touched Python files compile.

## Out Of Scope

- Adding new external read endpoints.
- Changing message retrieval behavior or verification extraction logic.
- Adding frontend UI changes.
- Documenting or exposing account passwords, refresh tokens, task tokens, provider JWTs, API keys, or bearer token values.
