# Security Policy

## Supported versions

Security fixes are applied to the default branch (`main` / `master`) and released through the normal deployment pipeline. Older commits and tags are not actively supported unless noted in a release advisory.

## Reporting a vulnerability

**Do not open a public GitHub issue** for exploitable security problems.

Instead:

1. Use [GitHub Private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) for this repository when enabled, **or**
2. Contact the maintainers through your organization's secure channel.

Include enough detail to reproduce the issue (affected routes, versions, configuration) without attaching production secrets.

We aim to acknowledge reports within **5 business days** and will coordinate disclosure timing with the reporter when possible.

## Do not share secrets publicly

Never paste the following in issues, pull requests, discussions, or CI logs:

- `.env` values or production configuration
- JWT secrets, encryption keys, or database credentials
- Channel provider tokens (Meta, WhatsApp, Telegram, etc.)
- Customer data or message content from production systems

Use redacted examples and synthetic test data only.

## Automated security checks

This repository uses layered checks:

| Check | When it runs |
|-------|----------------|
| [CI](.github/workflows/ci.yml) — Ruff, tests, migrations, frontend/landing build | Push and pull request |
| [CodeQL](.github/workflows/codeql.yml) — static analysis for Python and JavaScript/TypeScript | Push, pull request, weekly schedule |
| [Dependency review](.github/workflows/dependency-review.yml) — flags vulnerable dependency changes | Pull request |
| [Dependabot](.github/dependabot.yml) — pip, npm, and GitHub Actions update PRs | Weekly |

Repository administrators should set **Settings → Actions → General → Workflow permissions** to **Read repository contents and packages permissions** so workflows run with least privilege by default. Individual workflows declare any additional permissions they require.

## Dependency hygiene

- Python dependencies are declared in `backend/pyproject.toml`.
- Frontend and landing npm dependencies must use pinned semver ranges; `"latest"` is not allowed in `package.json`.
- Production must keep `WEBHOOK_SIGNATURE_BYPASS=false`, use a strong `TOKEN_ENCRYPTION_KEY`, and restrict `CORS_ORIGINS`.

See [AGENTS.md](AGENTS.md) for full security rules enforced in development.
