# External message read OpenAPI contract design

## Boundary

This task strengthens the machine-readable OpenAPI contract only. Runtime controllers and services keep their existing payloads unless tests reveal a schema/runtime mismatch that must be fixed for compatibility.

## Current Runtime Shapes

- MessagesData: emails, count, has_more.
- MessageSummary: id, email_address, from_address, subject, content_preview, has_html, timestamp, created_at, is_read, method.
- MessageDetail: MessageSummary fields plus to_address, content, html_content, raw_content, method.
- RawMessageData: id, email_address, raw_content, method.
- VerificationResult: formatted, verification_code, verification_link, confidence fields, matched_email_id, method, folder, channel and optional diagnostic flags.
- ProbeStatusData: probe_id, status, email, result, error_code, error_message, created_at, updated_at and timing fields where present.
- AccountStatusData: email, exists, can_read, account_type, provider, status, preferred_method, upstream_probe_ok, probe_method, last_probe_at, last_probe_error, last_refresh_at.

## OpenAPI Changes

- Keep MessageSummary and MessagesData typed; add has_more to MessagesData required/properties.
- Expand MessageDetail into an explicit object with required content fields instead of allOf plus additionalProperties.
- Add RawMessageData and point /api/external/messages/{message_id}/raw to it.
- Replace loose VerificationResult, ProbeStatusData, and AccountStatusData schemas with typed objects.

## Compatibility

The schema remains permissive where runtime may include extra diagnostic fields by using additionalProperties where needed. Secret-bearing fields are not documented.

## Rollback

Revert schema/test/spec changes. No database or runtime migration is involved.
