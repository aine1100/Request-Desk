# Dataset Request Desk

Internal tool for a robotics data team. Clients order a number of **episodes** (metadata for clips that already exist). Operators import those records from a CSV export, assign them to a request, and move the request through delivery. Clients accept or reject.

This app does not upload or play video.

## Run everything

From this directory:

```bash
docker compose up --build
```

- App: http://localhost:3000
- API: http://localhost:8000
- Health: http://localhost:8000/health

The API container runs migrations and creates the seed users. Episodes are not loaded automatically. Sign in as an operator and import `seed/episodes.csv` from the Import page, or:

```bash
docker compose exec api python manage.py import_episodes /seed/episodes.csv
```

## Tests

```bash
docker compose run --rm api python manage.py test
```

SQLite is used when `DATABASE_URL` is unset, so this also works from `backend/` after `pip install -r requirements.txt`:

```bash
python manage.py test
```

## Seed accounts

Passwords are hashed in the database. `seed_users` resets these accounts on startup.

| Email | Password | Role |
|---|---|---|
| admin@example.com | admin123 | admin |
| ops1@example.com | ops123 | operator |
| ops2@example.com | ops123 | operator |
| client-a@example.com | client123 | client |
| client-b@example.com | client123 | client |

## Local development without Docker

Backend (SQLite):

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_users
.venv\Scripts\python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Set `DATABASE_URL=postgres://desk:desk@localhost:5432/desk` to point the API at Postgres. Production should use Postgres. SQLite is only for local tests and a quick start: it has no row locking (`SELECT FOR UPDATE`), so the assignment unique constraint is the race backstop. Postgres takes the row lock as well.

## Analytics

`GET /api/analytics/?start=YYYY-MM-DD&end=YYYY-MM-DD` (operator or admin):

- episodes recorded per day, per robot, where `recorded_at` falls in the range (Kigali dates)
- requests whose first `submitted` event falls in the range, counted by **current** status
- median seconds from that submitted event to the first later `delivered` event
- top 5 task names by number of `good` episodes recorded in the range

The aggregations run in SQL. At about 5 million episodes the daily and top-task queries are index range scans on `(recorded_at, robot_id)` and `(quality, task_name)`, not a Python loop over rows. The median only touches status events, so it stays small even when the episode table is large. A very wide date range still reads a large slice of the episode index; the next step would be monthly partitions, not loading rows into the app. Imports of that size should use `import_episodes` rather than the HTTP upload (the endpoint caps files at 50MB and uses `bulk_create` in batches of 1000).

## Status flow

```
submitted → in_progress → delivered → accepted
                                    ↘ rejected → in_progress
```

Operators and admins move a request into progress, assign episodes, deliver, and resume rejected work. The owning client accepts or rejects. Delivery is refused until assigned episodes are at least `episodes_requested`. An episode can sit on one request at a time, and only `good` or `usable` episodes can be assigned. Assignment is allowed only while the request is `in_progress`.
