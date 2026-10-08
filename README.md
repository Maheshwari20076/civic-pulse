# CivicPulse 2.0

**Turning citizen reports into actionable city intelligence.**

Cities don't have a shortage of complaints. They have a shortage of actionable
intelligence. CivicPulse takes scattered citizen observations and turns them into
verified, clustered, prioritised and routed civic problems.

```
8 citizen reports  ->  1 civic issue  ->  Priority 90/100  ->  Road Infrastructure  ->  Resolved
```

---

## Problem

A pothole outside a busy bus stand gets reported by eight different people. A
traditional complaint system stores eight tickets, and the city sees eight small
problems instead of one serious one. Nobody can answer the questions that
actually decide what gets fixed first: how bad is it, how many people does it
affect, who owns it, and how long has it been sitting there?

## Solution

Every incoming report runs through a pipeline before an official ever sees it:

1. **Perception** — the report is read, categorised, and scored for severity and
   safety risk.
2. **Clustering** — it is matched against nearby open issues by distance,
   category and text similarity. A match attaches the report to the existing
   issue instead of creating a duplicate.
3. **Priority** — a weighted score is computed by the application (not the AI)
   from severity, safety risk, cluster strength, location impact, recency and
   citizen support.
4. **Routing** — the issue is matched to the department that owns that category.
5. **Follow-up** — issues that sit too long in Assigned or In Progress are
   flagged for escalation.

## Key features

- Citizen reporting with photo upload and browser geolocation
- Automatic duplicate detection and issue clustering
- Explainable priority scoring — every score shows its own breakdown
- Department routing with admin override
- Emerging civic signals: clusters of *related* issues in one area
- Live city map (Leaflet + OpenStreetMap), filterable by priority, category and status
- Full status timeline per issue, with citizen notifications at every change
- Admin analytics (Chart.js) across category, status, priority, workload and time
- Citizen impact score and support ("me too") on existing issues

## AI architecture

The Gemini API handles perception and explanation only:

| AI decides | The application decides |
| --- | --- |
| Category, severity, safety risk, impact level | Final priority score |
| Plain-language summary and reasoning | Whether two reports are the same issue |
| Recommended action | Department assignment and status |
| Signal explanations | Everything written to the database |

Model output is parsed, validated and clamped before use. **If `GEMINI_API_KEY`
is absent or the API fails, a deterministic local engine takes over** —
keyword categorisation, severity and safety heuristics, and the same scoring
maths. The app never breaks because the network did. The interface shows which
engine produced each analysis.

## Tech stack

**Frontend** HTML5, CSS3, JavaScript, Bootstrap 5, custom CSS, Lucide icons,
Leaflet.js + OpenStreetMap, Chart.js
**Backend** Python, Flask (blueprints + service layer)
**Database** MySQL 8 (XAMPP-compatible); SQLite fallback for a no-setup demo
**AI** Google Gemini, with a deterministic local fallback engine

## System architecture

```
routes/      HTTP layer only - auth, citizen, admin, api
services/    the civic intelligence pipeline
   ai_service.py            perception + explanation (Gemini or local engine)
   duplicate_service.py     haversine distance + text similarity clustering
   priority_service.py      weighted, explainable 0-100 score
   routing_service.py       category -> department
   signal_service.py        emerging area-level patterns
   notification_service.py  citizen notifications
   issue_service.py         orchestrates the pipeline, owns writes
utils/       decorators (auth/roles), helpers, validators
db.py        one thin query layer, MySQL and SQLite
```

## Database design

Ten tables with foreign keys: `users`, `departments`, `categories`, `issues`,
`issue_reports`, `issue_images`, `issue_support`, `ai_analysis`,
`issue_status_history`, `notifications`.

The important distinction: **`issues` is one real-world problem; `issue_reports`
is one citizen telling you about it.** The cluster engine decides which of the
two a new submission becomes.

## User roles

**Citizen** — report issues, upload photos, see the AI analysis, track status,
browse nearby issues, support existing issues, receive notifications, build an
impact score.

**Admin** — the City Intelligence Center: priority queue, full issue detail with
AI reasoning, department assignment, status control, notes, emerging signals,
analytics, escalation flags.

## Installation

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

## Environment variables

Copy `.env.example` to `.env` and fill it in:

```
SECRET_KEY=change_this_to_a_long_random_string
DB_DRIVER=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=civicpulse
GEMINI_API_KEY=your_gemini_api_key
```

`GEMINI_API_KEY` is optional — without it the local engine runs. The key is read
from the environment and never appears in source.

## Database setup

**With MySQL / XAMPP** — start MySQL, then either import
`database/schema.sql` and `database/seed.sql` through phpMyAdmin, or run:

```bash
python init_db.py --driver mysql
```

**Without MySQL** — set `DB_DRIVER=sqlite` in `.env` and run:

```bash
python init_db.py
```

This builds `database/civicpulse.sqlite3` from the same two SQL files, so a dead
XAMPP install never costs you a demo slot.

## Running the application

```bash
python app.py
```

Open http://127.0.0.1:5000

If the database isn't reachable, the app doesn't crash — it serves a setup page
at `/setup` telling you exactly what's wrong.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@civicpulse.com | Admin@123 |
| Citizen | priya@example.com | Citizen@123 |

All seeded citizens (`arjun@`, `fatima@`, `rohit@`, `sneha@`, `imran@`,
`kavya@`, `manoj@` `example.com`) share the citizen password.

Seed data covers 15 issues across every status and priority band, with
deliberate clusters: 7 pothole reports at the Central Bus Stand, plus garbage,
streetlight and water clusters. Coordinates are set around Belagavi; change
them in `database/generate_seed.py` and re-run it to reseed for another city.

## Hackathon demo flow

1. Sign in as **priya@example.com**.
2. **Report an issue**: "Large pothole near the bus stop. Vehicles are
   struggling to pass and it could cause accidents." Category **Pothole**,
   attach a photo, and drop the pin near the Central Bus Stand
   (approximately 15.8560, 74.5061).
3. Submit. The result screen shows the analysis — category, severity, safety
   risk — and then the moment that matters: **merged with 7 existing reports,
   8 reports → 1 civic issue**.
4. Read the priority breakdown: **Priority 90/100, Critical**, with every
   component shown and weighted. Routed to **Road Infrastructure**.
5. Sign in as **admin@civicpulse.com**. The issue sits at the top of the
   **Priority Queue**.
6. Open it: eight citizen reports, one problem, AI reasoning, recommended action.
7. **Assign** Road Infrastructure, move status to **In Progress**, add a note.
8. Back as the citizen: the notification and the timeline have both updated.
9. Admin marks it **Resolved** — the dashboard, analytics and resolution rate
   move with it.
10. Finish on **Emerging signals**: three separate water-related issues in
    Tilakwadi surfacing as one possible infrastructure problem.

## Future scope

Multilingual voice reporting, WhatsApp intake, a native mobile app, IoT sensor
feeds, predictive maintenance, direct government department API integration,
computer-vision damage assessment from photos, and satellite imagery for
city-wide predictive models.

## Screenshots

_Add screenshots here: landing page, report form, AI result with the cluster
merge, City Intelligence Center, issue detail, map, analytics, emerging signals._

## Notes on structure

Two small, deliberate departures from the original spec sheet: the AI/API routes
live in `routes/api.py` (they serve `/api/*`), and pipeline orchestration is
split into `services/issue_service.py` so the route handlers stay thin.
