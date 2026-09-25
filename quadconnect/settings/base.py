"""
Shared Django settings for QuadConnect.

Everything true of *every* environment lives here. Environment-specific
overrides live in `development.py` and `production.py`, both of which
`from .base import *`.

Secrets are read from a `.env` file at the repository root, which is
gitignored. `.env.example` documents the required keys.

Select an environment with DJANGO_SETTINGS_MODULE, e.g.
    quadconnect.settings.development   (manage.py default)
    quadconnect.settings.production    (wsgi.py / asgi.py default)
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# settings/base.py -> settings/ -> quadconnect/ -> repository root.
# Three levels, not two: the settings package added a directory. Getting this
# wrong silently points db.sqlite3 and the templates at the wrong tree.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


def env(key, default=None, required=False):
    """Read an environment variable, failing loudly when one is mandatory."""
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(
            f"Missing required environment variable {key!r}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


# --- Security -------------------------------------------------------------
# Never hard-coded. Generate one with:
#   python -c "from django.core.management.utils import get_random_secret_key
#              as k; print(k())"
SECRET_KEY = env("DJANGO_SECRET_KEY", required=True)

# Overridden per environment.
DEBUG = False
ALLOWED_HOSTS = []


# --- Third-party keys -----------------------------------------------------
# Placeholder for the Screen 8 campus map. Not a real key.
MAPS_API_KEY = env("MAPS_API_KEY", default="")


# --- Applications ---------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Must sit above staticfiles: stops runserver serving /static/ itself,
    # so development serves static files through WhiteNoise exactly as
    # production does (same MIME types, same headers).
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",

    # QuadConnect domain app: the verified connection lifecycle.
    "connect",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves static files in every environment, straight after
    # SecurityMiddleware as WhiteNoise requires. With DEBUG=True it reads
    # from the finders; with DEBUG=False it serves collected files.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "quadconnect.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "quadconnect.wsgi.application"
ASGI_APPLICATION = "quadconnect.asgi.application"


# --- Database -------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# --- Password validation --------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation."
             "UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation."
             "MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation."
             "CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation."
             "NumericPasswordValidator"},
]


# --- Internationalisation -------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True


# --- Static files ---------------------------------------------------------
STATIC_URL = "static/"

# Site-wide assets live in one project-level static/ directory, because the
# site-wide base template is their only consumer:
#   static/css/    quadconnect.css
#   static/fonts/  self-hosted Inter (SIL OFL)
#   static/img/    logo and favicon
# App-specific assets would go in <app>/static/<app>/ once a second app
# exists; the <app>/ namespace stops two apps' files colliding.
STATICFILES_DIRS = [BASE_DIR / "static"]

# collectstatic target, gitignored. Production serves from here.
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
