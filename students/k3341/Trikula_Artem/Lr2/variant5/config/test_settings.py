"""Isolated PostgreSQL test configuration.

Uppercase imports are re-exported for Django's settings loader.
"""

# ruff: noqa: F401
from copy import deepcopy

from .settings import (
    ALLOWED_HOSTS,
    ASGI_APPLICATION,
    AUTH_PASSWORD_VALIDATORS,
    AUTH_USER_MODEL,
    BASE_DIR,
    CSRF_COOKIE_NAME,
    DATABASES,
    DEBUG,
    DEFAULT_AUTO_FIELD,
    INSTALLED_APPS,
    LANGUAGE_CODE,
    LOGIN_REDIRECT_URL,
    LOGIN_URL,
    LOGOUT_REDIRECT_URL,
    MIDDLEWARE,
    ROOT_URLCONF,
    SECRET_KEY,
    SESSION_COOKIE_NAME,
    STATIC_URL,
    TEMPLATES,
    TIME_ZONE,
    USE_I18N,
    USE_TZ,
    WSGI_APPLICATION,
    required,
)

DATABASES = deepcopy(DATABASES)
DATABASES["default"]["USER"] = required("POSTGRES_TEST_USER")
DATABASES["default"]["PASSWORD"] = required("POSTGRES_TEST_PASSWORD")
DATABASES["default"]["TEST"] = {"NAME": "test_" + DATABASES["default"]["NAME"]}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
