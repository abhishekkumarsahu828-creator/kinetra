# Security, privacy and deployment release gates

This repository is a **release candidate starter**, not an externally audited production deployment. The application was generated in an environment without installed Django/PostgreSQL packages; the server integration test suite must be run in a fully provisioned environment before it can be considered verified.

## Before a real launch

1. Run migrations and tests against actual PostgreSQL using Docker or CI.
2. Run `python manage.py makemigrations --check --dry-run` and review any schema drift.
3. Configure actual DNS, HTTPS, allowed hosts, trusted origins and reverse proxy. Set `DJANGO_DEBUG=false`.
4. Configure SMTP and verify password reset delivery and operational notifications (currently in-app events; email delivery integration for booking events is not implemented).
5. Replace local media volume with encrypted private object storage for multi-instance deployment and verify signed/protected download routing.
6. Review and improve upload scanning and content processing. Enforce quotas and rate limits at reverse proxy.
7. Add account email verification before accepting public self-registration as verified identity.
8. Implement an institution-specific agreement and privacy notice, retention and deletion procedures before handling real people's data.
9. Add offsite encrypted backups; perform and record a full restore rehearsal.
10. Execute external authorisation, security, accessibility and load tests with recorded results.
11. Add telemetry, error alerting, operational runbooks and monitoring.
12. Put confirmed release ownership, on-call contact and incident procedures in place.
13. Add email reminder scheduling and delivery or acknowledge in-app reminders require site visits.
14. Run a limited supervised pilot with real institutional owner authorisation, safety policies and facility procedures.

## Known limitations of this iteration

- No public hosted link is created automatically (requires hosting account and domain).
- External SMTP delivery is configurable for password resets but booking-event emails are not implemented.
- In-app alerts are stored in DB; an hourly container service can create overdue notices when Docker is running.
- Fairness policy covers simple quotas, waitlist promotion and explanation, not complex institutional priority tiers.
- Resource schedules use fixed weekdays and same-day start/end; no holidays calendar or overnight appointments.
- No QR/NFC physical handover; human confirmation is required.
- No billing or deposits, SSO, AI search, push messaging or mobile app.
- File content checking covers Pillow-supported image formats and max size, not antivirus scanning or advanced metadata stripping.
- Organisation onboarding is performed by a trusted superadmin; public self-service organisation creation is deliberately restricted.
- CSV exports, booking extensions, cancellation penalties and maintenance conflict resolution are not automated.
- Schema and functional tests included but not exercised in this sandbox without Django/PostgreSQL.
- UI uses Google Fonts with system fallbacks; review consent and self-hosting requirements for your jurisdiction.
- A single persistent media volume is only suitable for a single-instance deployment; multi-instance needs private object storage.
- Application-level audit rows are append-only via the supplied management UI, but not cryptographically immutable against database administrators.

## Deployment security checklist

- Ensure no `.env` or real passwords are committed.
- Do not enable `ALLOW_SEED_DEMO=yes` in production.
- Disable superadmin exposure publicly unless necessary or restrict by network.
- Configure `SECURE_SSL_REDIRECT`, HSTS and `TRUST_PROXY_SSL_HEADER` correctly behind a *trusted* proxy.
- Use managed database TLS when connecting across external networks.
- Restrict PostgreSQL to private network access.
- Limit reverse proxy upload body size (<= 12MB suggested) and add per-IP throttling.
- Configure application encryption keys/secrets rotation and access policies.
- Back up the PostgreSQL data volume and private media together.
- Use a separate database account for backups and migration access when practical.
- Review national data protection and institution-specific restrictions before collecting personal data.
