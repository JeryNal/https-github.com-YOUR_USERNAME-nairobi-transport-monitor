from flask import Blueprint, render_template


views_bp = Blueprint("views", __name__)


@views_bp.get("/")
def dashboard():
    return render_template("index.html")


@views_bp.get("/health")
def health():
    return {"status": "ok"}
