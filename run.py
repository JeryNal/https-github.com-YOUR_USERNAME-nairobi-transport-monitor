import os

from app import create_app, socketio


app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=debug,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
