# Failed Jobs Runbook

Failed worker jobs are stored in the `failed_jobs` table and exposed through the admin-only failed jobs UI.

## Operator workflow

1. Open **Administration → Failed Jobs**.
2. Review the queue, job type, retry count, error, and masked payload.
3. Retry only after confirming the original operation is idempotent.
4. Ignore jobs only when the root cause is understood or the event is obsolete.

## Safety rules

- Do not use the deprecated `/api/v1/jobs/failed` compatibility endpoint for new tooling.
- Payloads returned by current failed-job APIs are masked for sensitive keys.
- Retry actions are audited as `failed_job_retried`; ignored jobs are audited as `failed_job_ignored`.
- If retries repeatedly fail, enable pilot emergency stop before investigating live automation.
