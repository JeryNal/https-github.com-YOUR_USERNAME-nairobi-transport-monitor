# Real-Time Public Transport Monitoring System for Nairobi City

A working Flask project based on the proposal. It provides:

- JWT login and protected API routes
- SQLite storage for users, routes, vehicles, and location history
- Real-time vehicle simulation for Nairobi matatu routes
- Socket.IO updates for live dashboard/map refreshes
- Leaflet/OpenStreetMap web interface
- Basic analytics for operational monitoring

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python run.py
```

Open `http://127.0.0.1:5000`.

Default login:

- Username: `admin`
- Password: `admin123`

## Tests

```powershell
.\.venv\Scripts\python -m pytest
```

## Production

The project includes `wsgi.py`, `Procfile`, `render.yaml`, and `/health` for production hosting. See `DEPLOYMENT.md`.

On Render, make sure the Start Command is:

```text
gunicorn --worker-class gthread --threads 100 --workers 1 --bind 0.0.0.0:$PORT wsgi:app
```

If the logs say `Running 'gunicorn app:app'`, the Render Start Command is still using the wrong default.

## Notes

The simulator uses built-in sample routes for Ngong Road, Thika Road, and Mombasa Road. It can be extended later to ingest real GPS hardware data, NTSA/SACCO feeds, or mobile app telemetry.
