# Production Deployment

This project is ready for deployment on a Python web host such as Render.

## Recommended Render Setup

1. Push this project to GitHub.
2. In Render, create a new Web Service from the GitHub repository.
3. Use these settings:

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: gunicorn --worker-class gthread --threads 100 --workers 1 --bind 0.0.0.0:$PORT wsgi:app
Health Check Path: /health
```

If Render logs show:

```text
Running 'gunicorn app:app'
```

edit the service settings and replace the Start Command with the `wsgi:app` command above. The project does not use `app:app` as its production entrypoint.

4. Add environment variables:

```text
SECRET_KEY=<long random secret>
JWT_SECRET_KEY=<different long random secret, at least 32 bytes>
SIMULATION_ENABLED=true
SOCKETIO_CORS_ORIGINS=*
```

The included `render.yaml` can also be used as a Render Blueprint.

## Why One Worker?

The app includes an in-process vehicle simulator. Running one Gunicorn worker prevents multiple simulator copies from updating the same SQLite data at the same time. For a larger production system, move the simulator to a separate background worker and use PostgreSQL/PostGIS.

## Production Notes

- This demo uses SQLite. It is fine for a school demo and prototype.
- For a real transport deployment, use PostgreSQL/PostGIS and persistent storage.
- Set real secrets in the hosting dashboard. Do not use development secrets online.
- The frontend currently loads Leaflet, Socket.IO client, and Bootstrap from CDNs, so the deployed app needs internet access.

## Local Production-Style Smoke Test

Windows cannot run Gunicorn directly, but these checks confirm the Flask app is production importable:

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m compileall app tests wsgi.py run.py
.\.venv\Scripts\python -m pip check
```
