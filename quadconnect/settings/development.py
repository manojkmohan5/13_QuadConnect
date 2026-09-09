"""
Development settings.

Used by manage.py by default. Never deploy with these.
"""

from .base import *  # noqa: F401,F403
from .base import env

# Verbose errors and the debug toolbar-friendly behaviour belong here only.
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "testserver"]

# Console backend so account emails are visible while developing.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow an override for teammates running on a LAN address or Codespaces.
_extra = env("DJANGO_ALLOWED_HOSTS", default="")
if _extra:
    ALLOWED_HOSTS += [h.strip() for h in _extra.split(",") if h.strip()]
