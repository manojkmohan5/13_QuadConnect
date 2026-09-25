"""
Production settings.

Used by wsgi.py and asgi.py. DEBUG is off and hosts must be declared
explicitly, so an unset DJANGO_ALLOWED_HOSTS fails fast rather than
silently serving to any Host header.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

ALLOWED_HOSTS = [
    h.strip()
    for h in env("DJANGO_ALLOWED_HOSTS", required=True).split(",")
    if h.strip()
]

# --- Security hardening ---------------------------------------------------
# Django's deployment checklist. SSL redirect and HSTS are enabled only when
# the deployment actually terminates TLS, so a plain-HTTP demo still works.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # the CSRF token must be readable by JS forms

_ssl = env("DJANGO_SECURE_SSL", default="0") == "1"
SECURE_SSL_REDIRECT = _ssl
SESSION_COOKIE_SECURE = _ssl
CSRF_COOKIE_SECURE = _ssl
if _ssl:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Static files: cache busting ------------------------------------------
# collectstatic writes each file a second time under a content-hashed name
# (quadconnect.css -> quadconnect.3f2a9c1b.css) plus a manifest, and
# {% static %} looks names up in that manifest. A changed file gets a new
# URL, so browsers can cache static files forever yet never serve a stale
# stylesheet. WhiteNoise sends the far-future cache headers and a gzip copy.
# Development keeps the default storage, so no collectstatic is needed there.
# Deploy step: python manage.py collectstatic --noinput
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Surface errors in the log rather than swallowing them behind DEBUG=False.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
