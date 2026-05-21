import html
import json
import re
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request

from app.auth import create_access_token, jwt_required, role_required, verify_credentials
from app.database import get_db


api_bp = Blueprint("api", __name__, url_prefix="/api")

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
MATATU_IMAGE_CACHE_TTL_SECONDS = 60 * 60 * 6
_matatu_image_cache = {"expires_at": 0, "images": []}


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


def traffic_action(severity):
    if severity == "Busy":
        return "Dispatch support, warn passengers, and monitor this corridor closely."
    if severity == "Moderate":
        return "Keep this route on watch and advise passengers to allow extra travel time."
    return "No immediate action needed. Keep normal monitoring active."


def plain_text(value):
    if not value:
        return ""
    return html.unescape(re.sub(r"<[^>]*>", "", str(value))).strip()


def fetch_matatu_images_from_commons(limit=6):
    params = urlencode(
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": "Nairobi matatu road",
            "gsrnamespace": 6,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 900,
            "origin": "*",
        }
    )
    request = Request(
        f"{COMMONS_API_URL}?{params}",
        headers={"User-Agent": "NairobiTransportMonitor/1.0"},
    )
    with urlopen(request, timeout=6) as response:
        payload = json.loads(response.read().decode("utf-8"))

    pages = payload.get("query", {}).get("pages", {})
    images = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        image_url = info.get("thumburl") or info.get("url")
        source_url = info.get("descriptionurl")
        if not image_url or not image_url.startswith("https://"):
            continue
        metadata = info.get("extmetadata") or {}
        images.append(
            {
                "title": page.get("title", "Nairobi matatu on the road").replace("File:", ""),
                "image_url": image_url,
                "source_url": source_url if source_url and source_url.startswith("https://") else "",
                "credit": plain_text((metadata.get("Artist") or {}).get("value")),
                "license": plain_text((metadata.get("LicenseShortName") or {}).get("value")),
            }
        )

    return images[:limit]


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


@api_bp.get("/matatu-images")
def get_matatu_images():
    limit = max(1, min(request.args.get("limit", default=6, type=int), 9))
    now = time.time()
    if _matatu_image_cache["expires_at"] > now and _matatu_image_cache["images"]:
        return jsonify(_matatu_image_cache["images"][:limit])

    try:
        images = fetch_matatu_images_from_commons(limit)
    except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return jsonify(_matatu_image_cache["images"][:limit])

    if images:
        _matatu_image_cache.update(
            {
                "expires_at": now + MATATU_IMAGE_CACHE_TTL_SECONDS,
                "images": images,
            }
        )
    return jsonify(images)


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
    route_id = request.args.get("route_id", type=int)
    search = (request.args.get("q") or "").strip()
    filters = []
    params = []
    if route_id:
        filters.append("routes.id = ?")
        params.append(route_id)
    if search:
        filters.append("(routes.name LIKE ? OR routes.origin LIKE ? OR routes.destination LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = get_db().execute(
        f"""
        WITH route_stats AS (
            SELECT
                routes.id AS route_id,
                routes.name,
                routes.origin,
                routes.destination,
                routes.color,
                traffic_updates.message AS saved_message,
                traffic_updates.updated_at,
                ROUND(AVG(vehicles.speed_kph), 1) AS average_speed,
                ROUND(AVG(vehicles.occupancy), 1) AS average_occupancy,
                COUNT(DISTINCT vehicles.id) AS vehicles
            FROM routes
            LEFT JOIN vehicles ON vehicles.route_id = routes.id
            LEFT JOIN traffic_updates ON traffic_updates.route_id = routes.id
            {where_clause}
            GROUP BY routes.id
        )
        SELECT
            route_id,
            name,
            origin,
            destination,
            color,
            CASE
                WHEN COALESCE(average_speed, 0) <= 25 OR COALESCE(average_occupancy, 0) >= 31 THEN 'Busy'
                WHEN COALESCE(average_speed, 0) <= 42 OR COALESCE(average_occupancy, 0) >= 26 THEN 'Moderate'
                ELSE 'Clear'
            END AS severity,
            CASE
                WHEN COALESCE(average_speed, 0) <= 25 OR COALESCE(average_occupancy, 0) >= 31
                    THEN 'Live data shows heavy route pressure. Expect delays before travelling.'
                WHEN COALESCE(average_speed, 0) <= 42 OR COALESCE(average_occupancy, 0) >= 26
                    THEN 'Live data shows moderate traffic. Plan with some extra travel time.'
                ELSE 'Live data shows normal movement on this route.'
            END AS message,
            saved_message,
            updated_at,
            average_speed,
            average_occupancy,
            vehicles,
            ROUND(
                (100 - MIN(COALESCE(average_speed, 0), 70) / 70.0 * 100) * 0.55
                + (MIN(COALESCE(average_occupancy, 0), 33) / 33.0 * 100) * 0.45,
                1
            ) AS pressure_score
        FROM route_stats
        ORDER BY
            CASE severity
                WHEN 'Busy' THEN 1
                WHEN 'Moderate' THEN 2
                ELSE 3
            END,
            name
        """,
        params,
    ).fetchall()
    payload = []
    for row in rows:
        update = row_to_dict(row)
        update["next_action"] = traffic_action(update["severity"])
        payload.append(update)
    return jsonify(payload)
