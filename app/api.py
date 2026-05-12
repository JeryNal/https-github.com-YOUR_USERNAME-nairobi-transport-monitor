import json

from flask import Blueprint, jsonify, request

from app.auth import create_access_token, jwt_required, role_required, verify_credentials
from app.database import get_db


api_bp = Blueprint("api", __name__, url_prefix="/api")


def row_to_dict(row):
    return dict(row) if row is not None else None


def route_payload(row):
    route = row_to_dict(row)
    route["path"] = json.loads(route.pop("path_json"))
    return route


def vehicle_payload(row):
    vehicle = row_to_dict(row)
    if "path_json" in vehicle:
        vehicle["route_path"] = json.loads(vehicle.pop("path_json"))
    return vehicle


@api_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = verify_credentials(username, password)
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    return jsonify(
        {
            "access_token": create_access_token(user),
            "user": {"id": user["id"], "username": user["username"], "role": user["role"]},
        }
    )


@api_bp.get("/routes")
@role_required("admin", "manager", "driver", "passenger")
def get_routes():
    rows = get_db().execute("SELECT * FROM routes ORDER BY name").fetchall()
    return jsonify([route_payload(row) for row in rows])


@api_bp.get("/vehicles")
@role_required("admin", "manager", "driver")
def get_vehicles():
    rows = get_db().execute(
        """
        SELECT vehicles.*, routes.name AS route_name, routes.color, routes.path_json
        FROM vehicles
        JOIN routes ON routes.id = vehicles.route_id
        ORDER BY vehicles.plate_number
        """
    ).fetchall()
    return jsonify([vehicle_payload(row) for row in rows])


@api_bp.get("/vehicles/<int:vehicle_id>")
@role_required("admin", "manager", "driver")
def get_vehicle(vehicle_id):
    row = get_db().execute(
        """
        SELECT vehicles.*, routes.name AS route_name, routes.color, routes.path_json
        FROM vehicles
        JOIN routes ON routes.id = vehicles.route_id
        WHERE vehicles.id = ?
        """,
        (vehicle_id,),
    ).fetchone()
    if row is None:
        return jsonify({"error": "Vehicle not found"}), 404
    return jsonify(vehicle_payload(row))


@api_bp.get("/analytics")
@role_required("admin", "manager", "driver")
def get_analytics():
    db = get_db()
    summary = db.execute(
        """
        SELECT
            COUNT(*) AS total_vehicles,
            ROUND(AVG(speed_kph), 1) AS average_speed,
            ROUND(AVG(occupancy), 1) AS average_occupancy,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_vehicles
        FROM vehicles
        """
    ).fetchone()
    by_route = db.execute(
        """
        SELECT routes.name, COUNT(vehicles.id) AS vehicles, ROUND(AVG(vehicles.occupancy), 1) AS occupancy
        FROM routes
        LEFT JOIN vehicles ON vehicles.route_id = routes.id
        GROUP BY routes.id
        ORDER BY routes.name
        """
    ).fetchall()
    return jsonify({"summary": row_to_dict(summary), "routes": [row_to_dict(row) for row in by_route]})


@api_bp.get("/traffic")
@role_required("admin", "manager", "driver", "passenger")
def get_traffic_updates():
    rows = get_db().execute(
        """
        SELECT
            routes.id AS route_id,
            routes.name,
            routes.origin,
            routes.destination,
            routes.color,
            traffic_updates.severity,
            traffic_updates.message,
            traffic_updates.updated_at,
            ROUND(AVG(vehicles.speed_kph), 1) AS average_speed,
            ROUND(AVG(vehicles.occupancy), 1) AS average_occupancy,
            COUNT(vehicles.id) AS vehicles
        FROM routes
        LEFT JOIN vehicles ON vehicles.route_id = routes.id
        LEFT JOIN traffic_updates ON traffic_updates.route_id = routes.id
        GROUP BY routes.id
        ORDER BY
            CASE traffic_updates.severity
                WHEN 'Busy' THEN 1
                WHEN 'Moderate' THEN 2
                ELSE 3
            END,
            routes.name
        """
    ).fetchall()
    return jsonify([row_to_dict(row) for row in rows])
