# Failed Job Runbook

See also [failed-jobs-runbook.md](failed-jobs-runbook.md).

## When jobs fail

Worker failures are persisted in `failed_jobs` with masked payloads exposed as `redacted_payload` in the API.

## Operator actions

- **Retry** — requeue job (admin/owner only)
- **Ignore** — mark resolved without retry (admin/owner only)

## Escalation

Escalate when the same queue/job_type fails repeatedly, payloads indicate external API outage, or payment/webhook jobs fail in bulk.

## Audit

Actions `failed_job_viewed`, `failed_job_retried`, and `failed_job_ignored` are written to admin audit logs.
