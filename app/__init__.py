from flask import Flask
from flask_socketio import SocketIO

from app.database import close_db, init_db
import os


def _env_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


socketio = SocketIO(async_mode="threading")


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me-please-update"),
        JWT_SECRET_KEY=os.environ.get(
            "JWT_SECRET_KEY",
            "dev-jwt-secret-change-me-32-bytes-minimum",
        ),
        DATABASE=os.environ.get("DATABASE", app.instance_path + "/transport.sqlite3"),
        SIMULATION_ENABLED=_env_bool("SIMULATION_ENABLED", True),
        SOCKETIO_CORS_ORIGINS=os.environ.get("SOCKETIO_CORS_ORIGINS", "*"),
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    init_db(app)
    app.teardown_appcontext(close_db)

    from app.api import api_bp
    from app.views import views_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)

    socketio.init_app(app, cors_allowed_origins=app.config["SOCKETIO_CORS_ORIGINS"])

    if app.config.get("SIMULATION_ENABLED"):
        from app.simulation import start_simulation

        start_simulation(app, socketio)

    return app
