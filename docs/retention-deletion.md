# Retention and Deletion Notes

This product stores customer messages, raw webhook payloads, order details, payment metadata, decision traces, and audit logs.

## Current controls

- Instagram access tokens are encrypted at rest and omitted from API responses.
- Failed-job payloads are masked in current API responses.
- Simulation reset removes simulation conversations only.

## Production requirements

Before production launch, define retention windows for raw webhook payloads, failed jobs, decision traces, and customer PII. Add admin workflows for customer export/deletion where legally required, and document which audit records must be retained for fraud/accounting purposes.
