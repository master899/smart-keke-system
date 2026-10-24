# Smart Keke Transport Management System

A Django web application for campus Keke ride booking and management. Students can register and book rides; drivers can manage availability and assigned rides; administrators can manage users, rides, payments, and reports.

## Requirements

- Python 3.10 or newer
- pip

SQLite is configured by default. Pillow is required for profile and vehicle image uploads. The ride map uses Leaflet and online map tiles, so map tiles require an internet connection; no Google Maps API key is needed.

## Run locally on Windows

Open PowerShell in the folder containing `manage.py`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Generate a local Django secret key and set it in `.env` as `DJANGO_SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Then initialize the database and create an administrator account:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The Django admin is at <http://127.0.0.1:8000/admin/>.

## Configuration

The project reads configuration from environment variables and, when present, a local `.env` file. See `.env.example` for the available variables:

- `DJANGO_DEBUG`: use `True` for local development; set to `False` for deployment.
- `DJANGO_SECRET_KEY`: a private, randomly generated Django key. Production startup fails if it is missing.
- `DJANGO_ALLOWED_HOSTS`: comma-separated hostnames accepted by Django. Set this to your deployed domain(s).
- `DJANGO_CSRF_TRUSTED_ORIGINS`: comma-separated full origins, including `https://`, when required by the deployment host.
- `DJANGO_SECURE_SSL_REDIRECT`: defaults to enabled when `DJANGO_DEBUG=False`. Disable only when HTTPS redirection is correctly handled by a trusted reverse proxy.
- `DJANGO_SECURE_HSTS_SECONDS`: defaults to one year in production; use a smaller value during initial HTTPS deployment if needed.
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` and `DJANGO_SECURE_HSTS_PRELOAD`: leave disabled unless every relevant subdomain is HTTPS-only and you understand the browser preload implications. Django's deployment check warns until these are explicitly enabled.

Never commit `.env`, real credentials, the local SQLite database/export, or uploaded user media. The provided `.gitignore` excludes these local files.

## Database and static files

Migrations are committed and should be applied on a fresh clone with `python manage.py migrate`. The repository intentionally does not include the local database or its SQL export. Create a new administrator with `python manage.py createsuperuser`.

For a production deployment, configure the hosting platform to serve collected static assets and uploaded media appropriately. Collect static assets with:

```powershell
python manage.py collectstatic --noinput
```

The default SQLite database is suitable for local development and small demonstrations. Choose and configure a managed database and persistent media storage before deploying for production use.

## Checks and tests

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

For a deployment configuration check, set production environment values first, then run:

```powershell
python manage.py check --deploy
```
