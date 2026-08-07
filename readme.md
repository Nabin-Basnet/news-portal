# News Portal API Project

This repository contains a Django REST API for a news portal with user authentication, editorial workflows, comments/reactions/bookmarks, and advertisement management.

## API documentation

A complete frontend-friendly API reference is available in [docs/api-docs.md](docs/api-docs.md).

## Live hosted backend
- Hosted Swagger UI: https://news-portal-hvgs.onrender.com/api/docs/
- Hosted OpenAPI schema: https://news-portal-hvgs.onrender.com/api/schema/
- Hosted ReDoc: https://news-portal-hvgs.onrender.com/api/redoc/

## Quick links
- Swagger UI (local): http://localhost:8000/api/docs/
- ReDoc (local): http://localhost:8000/api/redoc/
- Base API URLs:
  - Authentication and users: /api/
  - Articles: /articles/
  - Ads: /api/ads/

## Local development
Run the project with:

```bash
python manage.py runserver
```

### Local HTTP and HTTPS

One network port can serve either HTTP or HTTPS, not both. To run both locally,
install dependencies, create a local-only certificate, then start the paired
servers:

```bash
pip install -r requirements.txt
python manage.py generate_dev_cert
python manage.py runserver_dual
```

- HTTP Swagger UI: `http://127.0.0.1:8000/api/docs/`
- HTTPS Swagger UI: `https://127.0.0.1:8443/api/docs/`

The generated certificate is self-signed, so the browser will show a local
certificate warning until you trust it. The `.certs/` directory is gitignored.
