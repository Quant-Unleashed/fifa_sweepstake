# Aman's FIFA Sweepstake

A small FastAPI web app for tracking a four-player FIFA World Cup 2026 sweepstake.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ADMIN_PASSWORD=change-me uvicorn app.main:app --reload
```

Open:

- Dashboard: <http://127.0.0.1:8000>
- Admin: <http://127.0.0.1:8000/admin>

## Render

Create a Render web service from this repository. The included `render.yaml` uses:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set these environment variables:

- `ADMIN_PASSWORD`: required for admin updates.
- `FOOTBALL_PROVIDER`: keep as `manual` for v1, or set to `football-data`.
- `FOOTBALL_DATA_API_KEY`: optional API key for football-data.org.

## Storage

The app stores editable data in JSON files under `data/`. The admin page includes export/import backup controls. JSON is intentionally simple for the first sharable version.

## Rules

- Stake: £1 per team.
- Group stage or Round of 32 exit: £0.
- Round of 16 exit: £1.
- Quarterfinal exit: £2.
- Semifinal exit: £4.
- Runner-up: £8.
- Winner: £16.
