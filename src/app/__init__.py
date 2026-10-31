"""Application factory for the learn-flask companion project."""

from __future__ import annotations

import logging

from flask import Flask

from .config import CONFIGS, DEV_SECRET_KEY
from .extensions import db


def create_app(config_name: str = "development", **overrides) -> Flask:
    """Build and return a fully wired Flask application.

    Nothing is created at import time, so tests and CLI tools can build as
    many isolated apps as they need, each with its own configuration.
    """
    app = Flask(__name__, instance_relative_config=True)

    # 1. Configuration: class defaults, then the optional git-ignored
    #    instance/settings.py, then FLASK_* environment variables, then
    #    explicit overrides passed by tests or scripts.
    app.config.from_object(CONFIGS[config_name])
    app.config.from_pyfile("settings.py", silent=True)
    app.config.from_prefixed_env()
    app.config.update(overrides)

    # Fail fast instead of signing production cookies with a public key.
    if config_name == "production" and app.config.get("SECRET_KEY") in (None, "", DEV_SECRET_KEY):
        raise RuntimeError("SECRET_KEY must be set to a random value in production")

    # 2. Extensions are bound to this app instance only.
    db.init_app(app)

    # 3. Blueprints carry the routes.
    from .api import api_bp
    from .web import web_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    # 4. CLI commands: `flask --app wsgi init-db`
    @app.cli.command("init-db")
    def init_db() -> None:
        """Create all database tables."""
        db.create_all()
        print("Database tables created.")

    if not app.debug and not app.testing:
        logging.basicConfig(level=logging.INFO)

    return app
