# Debugging Checklist

If the browser says `site can't be reached`, the Flask server is not listening yet.

## Start the server

Double-click `start_server.bat`, or run:

```powershell
.\.venv\Scripts\python.exe run.py
```

You should see:

```text
Running on http://127.0.0.1:5000
```

## Check the site

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/
```

Expected status: `200`.

## Check login and JWT

```powershell
$body = @{ username='admin'; password='admin123' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/auth/login -ContentType 'application/json' -Body $body
```

Expected result: JSON containing `access_token`.

## Common issue

The PowerShell message about `profile.ps1` execution policy is not a Flask error. It is a local PowerShell profile warning and can appear even when the app is working.
