# KINETRA — Trusted Institutional Resource Exchange

KINETRA is a **Django / PostgreSQL** web application for securely sharing underused equipment and spaces across an institution. It combines resource discovery, verified eligibility, owner approvals, fair waiting lists, supervised condition reports, incident handling and audit events in one operational workflow.

**Status:** Source-built release candidate, not externally deployed or fully integration-tested in the creation environment. Requires a provisioned Docker/Python environment and successful CI tests before public launch.

## Included features

- Premium responsive HTML/CSS/Vanilla JS user experience.
- Sign-up, login, password recovery and verified institutional membership workflow.
- Organisation-scoped roles (borrower, owner, manager and administrator).
- Equipment listings, search and category/institution filters.
- Training verification and eligibility checks.
- Booking requests, human approve/reject/waitlist decisions, conflict checks, quota limits and fair waitlist promotion.
- Human-confirmed check-in and return with before-and-after condition records and private photos.
- Incident reporting and human-documented resolutions.
- In-app notifications, overdue alert scheduler and append-oriented organisation audit history.
- PostgreSQL migration, Docker Compose, GitHub Actions and tests.

## 1. Start with Docker (recommended)

Install Docker Engine + Docker Compose v2, then:

```bash
cp .env.example .env
# Generate unique, strong DJANGO_SECRET_KEY and POSTGRES_PASSWORD, edit .env
# Keep DJANGO_DEBUG=true locally ONLY
docker compose up --build -d
docker compose logs -f web
```

Open **http://localhost:8000**. The startup process applies migrations and collects static files.

> The provided `compose.yaml` binds HTTP to localhost, *not* the public internet. Public deployment requires a trusted HTTPS ingress, a domain, secure environment variables and the release checklist.

## 2. Seed fictional demo resources

Choose a unique password (12+ characters) in your environment and execute:

```bash
DEMO_PASSWORD='YourUniqueDemoSecret123!' docker compose exec -e DEMO_PASSWORD web python manage.py seed_demo
```

Demo usernames (password is whatever you explicitly provide to the seed command):

| Account | Role | Primary purpose |
|---|---|---|
| `demo_admin` | Organisation admin | Verify members and qualifications |
| `demo_owner` | Resource owner | Create resources, approve bookings, confirm return |
| `demo_student` | Borrower | Has fictional verified 3D Printer Safety training |
| `demo_student2` | Borrower | Unverified 3D Printer Safety — may request verification |

All demo names, organisations and resources are fictional. Never run seeded demo login accounts on public production infrastructure.

## 3. Judge test path

1. Sign in as `demo_owner`; open **My workspace** → **List resource** to create a new listing. Or use the seeded `Ultimaker S5 · 3D Printer`.
2. Sign in as `demo_student`; open **Explore** → select the printer. Choose a weekday time within its opening hours and within its max duration.
3. Submit a booking, open its transaction page, note status `Awaiting review`.
4. Sign in as `demo_owner`; open **Manage**, review eligibility and approve.
5. Sign in as `demo_student`; return to booking page within 30 minutes of its scheduled start and submit the before-use condition. For a convenient judge demo, request a slot starting within the next 30 minutes while within resource hours.
6. Owner confirms physical handover.
7. Student records final condition and initiates return.
8. Owner confirms return. Borrower and reviewer see completed state, condition evidence and audit timeline.
9. For fairness, a second student with verified required training can request the same already-approved time to enter waiting list; owner cancellation promotes it for new human review.
10. Use **Report incident** on an approved or later booking to demonstrate escalation and resolution.

### Important time-window behaviour

Check-in may be initiated from 30 minutes before start until reservation end; it is not allowed for arbitrary future dates. For a time-independent automated integration test, the test suite overrides the clock.

## 4. Run checks and tests

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web python manage.py test exchange -v 2
docker compose exec web python manage.py check --deploy
```

`check --deploy` may report expected issues with local `DJANGO_DEBUG=true`; review and resolve all findings in the production configuration.

## 5. Python development alternative

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Configure PostgreSQL and environment variables
python manage.py migrate
python manage.py runserver
```

Dev-only SQLite smoke mode is permitted with `DJANGO_DEBUG=true ALLOW_SQLITE_DEV=1`. It is not valid for PostgreSQL concurrency verification or production deployment.

## 6. Production rollout

Set `DJANGO_DEBUG=false`, a fresh secret, strong PostgreSQL credentials, allowed hostnames, CSRF trusted origins, correct HTTPS proxy settings and SMTP credentials as needed. Deploy behind TLS termination, configure backup/monitoring and finish [`docs/SECURITY_AND_RELEASE.md`](docs/SECURITY_AND_RELEASE.md). This code **must not** be advertised as secure or production-tested until appropriate live checks pass.

### Important operational limitations

- SMTP password reset links need a real mail provider. In-app booking updates work without external APIs.
- Demo seeding requires an explicit admin choice and password.
- Equipment access decisions require authorised institutional reviewers.
- No public hosting or GitHub repository is created automatically; the project can be uploaded and deployed using your accounts.

## 7. Documentation and disclosure

- Architecture and trust model: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Release and privacy checklist: [`docs/SECURITY_AND_RELEASE.md`](docs/SECURITY_AND_RELEASE.md)
- Hackathon guide: [`docs/HACKATHON_SUBMISSION.md`](docs/HACKATHON_SUBMISSION.md)

**Third-party components:** Django (BSD-3-Clause), psycopg, Pillow, Gunicorn, WhiteNoise, Python and PostgreSQL; Google Fonts used by the stylesheet. Confirm all dependency and asset licences before distribution.

**AI assistance disclosure:** Initial application code, templates, tests and documentation were generated with OpenAI ChatGPT assistance. Team members must verify, adapt, test and document their actual work. Do not misrepresent development history or prebuilt code. Follow the event's 48-hour original-build rule; if the build window has not begun, use this project for planning and produce authorised original code during the event.

## 8. Optional public HTTPS deployment configuration

For an owned VPS with a real domain, see [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md) and the optional Caddy overlay `compose.prod.yaml`. It does **not** provision hosting, purchase a domain or automatically complete safety/security release validation.

## 9. Trusted institution onboarding

Organisation creation is restricted to trusted operators. Independently verify the intended administrator's identity and institutional authority. With an **existing** account, run:

```bash
docker compose exec web python manage.py bootstrap_org --name 'Your Institution' --slug your-institution --username actual_admin_username --city 'Your City'
```

The one-time command creates the institution and its first administrator membership with audit events. Existing organisations cannot be overwritten this way. Django's `/superadmin/` views are read-only for operational domain records so core lifecycle actions must pass through the audited application views.


For the **first account**, securely set a temporary password via the operator's environment and include `--email` (never put passwords in terminal command arguments or code):

```bash
BOOTSTRAP_PASSWORD='UniqueTemporaryPasswordHere' docker compose exec -e BOOTSTRAP_PASSWORD web python manage.py bootstrap_org --name 'Your Institution' --slug your-institution --username actual_admin_username --email admin@institution.example
```

Have the administrator change the password using a configured secure password-reset channel before real use. This bootstrap path is for a trusted, verified institution operator—not public self-signup. Do not use fictitious credentials or the demo command for a real institution.
