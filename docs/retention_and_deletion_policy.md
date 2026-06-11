# Retention and Deletion Policy

See [retention-deletion.md](retention-deletion.md) for detailed retention categories.

## Summary

- Webhook raw payloads: retained for debugging; access restricted to admins
- Failed job payloads: masked in API; underlying storage follows operational retention
- Simulation data: may be reset via simulator/TRL reset endpoints
- Customer PII: subject to shop operator deletion/export workflows (planned operational process)
