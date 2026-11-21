"""
ARGUS — Flask application factory.
"""

from __future__ import annotations

import os

from flask import Flask
from dotenv import load_dotenv


def create_app() -> Flask:
    """Application factory — creates and configures the Flask app."""
    load_dotenv()

    app = Flask(
        __name__,
        template_folder=os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "templates"
        ),
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

    # Register blueprints
    from .routes import api
    app.register_blueprint(api)

    return app


# Entry point for gunicorn: `gunicorn app.main:app`
app = create_app()
