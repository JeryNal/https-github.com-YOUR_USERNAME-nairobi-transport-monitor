import sqlite3
from datetime import datetime, timezone

from flask import current_app, g
from werkzeug.security import generate_password_hash


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'operator',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    color TEXT NOT NULL,
    path_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL UNIQUE,
    sacco TEXT NOT NULL,
    route_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    speed_kph REAL NOT NULL DEFAULT 0,
    occupancy INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    path_index INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(route_id) REFERENCES routes(id)
);

CREATE TABLE IF NOT EXISTS location_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    speed_kph REAL NOT NULL,
    occupancy INTEGER NOT NULL,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
);
"""


ROUTES = [
    (
        "Ngong Road Route",
        "Railways",
        "Karen",
        "#0f766e",
        [
            [-1.2921, 36.8219],
            [-1.3004, 36.8072],
            [-1.3032, 36.7894],
            [-1.3190, 36.7584],
            [-1.3282, 36.7091],
        ],
    ),
    (
        "Thika Road Route",
        "CBD",
        "Ruiru",
        "#dc2626",
        [
            [-1.2864, 36.8172],
            [-1.2613, 36.8392],
            [-1.2362, 36.8715],
            [-1.1885, 36.9314],
            [-1.1458, 36.9634],
        ],
    ),
    (
        "Mombasa Road Route",
        "CBD",
        "Athi River",
        "#2563eb",
        [
            [-1.2864, 36.8172],
            [-1.3186, 36.8354],
            [-1.3398, 36.8859],
            [-1.3741, 36.9237],
            [-1.4563, 36.9781],
        ],
    ),
]


VEHICLES = [
    ("KDA 114A", "Super Metro", 1, -1.2921, 36.8219),
    ("KCB 705Q", "Forward Travelers", 1, -1.3032, 36.7894),
    ("KDG 221M", "Metro Trans", 2, -1.2864, 36.8172),
    ("KDJ 902L", "Thika Road SACCO", 2, -1.2362, 36.8715),
    ("KCY 448P", "Embassava", 3, -1.3186, 36.8354),
    ("KDE 331T", "Mombasa Road Shuttle", 3, -1.3741, 36.9237),
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        seed_db(db)
        db.commit()


def seed_db(db):
    db.execute(
        """
        INSERT OR IGNORE INTO users (username, password_hash, role, created_at)
        VALUES (?, ?, ?, ?)
        """,
        ("admin", generate_password_hash("admin123"), "admin", utc_now()),
    )

    for name, origin, destination, color, path in ROUTES:
        db.execute(
            """
            INSERT OR IGNORE INTO routes (name, origin, destination, color, path_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, origin, destination, color, __import__("json").dumps(path)),
        )

    for plate, sacco, route_id, lat, lon in VEHICLES:
        db.execute(
            """
            INSERT OR IGNORE INTO vehicles
                (plate_number, sacco, route_id, latitude, longitude, speed_kph, occupancy, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (plate, sacco, route_id, lat, lon, 35, 20, utc_now()),
        )
