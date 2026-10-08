# CivicPulse competition MVP upgrade

## What changed
- Added `/business` municipal SaaS/business page.
- Upgraded the public landing page with problem, solution flow, MVP, business model, revenue, demo-metric labeling, competitive advantage, GTM, scalability and pilot CTA.
- Added public navigation links for product flow and municipalities.
- Added municipal intelligence snapshot to the admin dashboard.
- Added civic-intelligence framing to admin issue details.
- Added pilot-oriented analytics context.
- Added responsive premium startup presentation styles while preserving the petrol/amber identity.
- Added a configurable `PILOT_CONTACT_EMAIL` environment variable for the pilot CTA email draft.

## Business model
Citizens are free users. Municipalities / urban local bodies are the paying B2B SaaS customers.
Pricing displayed in the MVP is explicitly a proposed competition business hypothesis, not a market claim.

## Pilot CTA
To make the pilot form open a real email draft, add:
`PILOT_CONTACT_EMAIL=your-team-email@example.com`
to the deployment environment. The form does not change the database schema or store pilot leads.

## Existing functionality
No database schema was changed. Existing Flask routes, authentication, services, clustering, AI/local analysis, priority scoring, maps, analytics and resolution workflows were preserved.

## Run locally
1. Create/activate a Python virtual environment.
2. Install `requirements.txt`.
3. Configure `.env` for SQLite or MySQL.
4. Run `python app.py`.
5. Open `http://127.0.0.1:5000`.

## Validation
Python source files were syntax-checked and all Jinja templates were parsed successfully. A full Flask browser/runtime smoke test could not be executed in the build environment because Flask dependencies were not installed and outbound package installation was unavailable.
