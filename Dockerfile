# clude's web app on Cloud Run (docs/web.md, "Deploying").
#
# Built by Cloud Build from `gcloud run deploy --source .`; Orbit has no
# Docker. What goes into the build context is decided by .gcloudignore
# (the upload) and .dockerignore (the COPY), which list the same things:
# no key file, no .env, no data/. The service reaches the bucket as its
# own identity (clude-run), so no credential is ever in the image.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements-web.txt .
RUN pip install -r requirements-web.txt

COPY . .
RUN useradd --create-home --uid 10001 clude
USER clude

# One worker, so the in-memory Watch games and the login rate limit are
# simply correct (and the service runs at most one instance); threads so
# a long "play to the end" does not block every other request outright.
# 300 s matches the service's request timeout.
CMD exec gunicorn --bind ":${PORT:-8080}" --workers 1 --threads 8 --timeout 300 \
    --access-logfile - "clude_web:create_app()"
