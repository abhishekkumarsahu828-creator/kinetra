# VPS deployment with managed HTTPS (optional Caddy overlay)

**Prerequisites:** Server with Docker and Docker Compose, a public domain with A/AAAA DNS pointing at the server, ports 80/443 open, confirmed institution permission, private backups, and all required real-world operational checks.

1. Copy `.env.example` to `.env`. Set `DJANGO_DEBUG=false` and unique production secrets. Set `DJANGO_ALLOWED_HOSTS=yourdomain.example`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.example`, and `TRUST_PROXY_SSL_HEADER=true`. Use a real SMTP provider and set the permitted from address. Do not seed public demo accounts.
2. Define `CADDY_DOMAIN=yourdomain.example` and `CADDY_EMAIL=ops@yourdomain.example` in `.env`.
3. Start `docker compose -f compose.yaml -f compose.prod.yaml up -d --build`.
4. Verify certificate acquisition in `docker compose -f compose.yaml -f compose.prod.yaml logs caddy`.
5. Open the HTTPS domain. Run migrations and unit/integration/security checks. Verify health and access controls over HTTPS.
6. Arrange offsite PostgreSQL and private media backups, alerting and retention procedures. Perform a restore exercise.

`web` remains bound to localhost port 8000 for local diagnostics; Caddy talks to it over the private Compose network. Never expose PostgreSQL or media paths publicly.

**Important:** This is a single-server rollout pattern, not a validated high-availability deployment. Multiple app instances require shared private object storage, centralised sessions/caching strategy, job scheduling coordination and capacity validation. CDN, encrypted backup replication and enterprise controls should be introduced after a successful measured pilot.
