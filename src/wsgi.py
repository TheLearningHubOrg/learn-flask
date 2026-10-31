"""WSGI entry point: `gunicorn --chdir src wsgi:app`."""

import os

from app import create_app

app = create_app(os.environ.get("APP_ENV", "production"))
