import json
import random
import threading
import time

from app.database import utc_now


_started = False


def start_simulation(app, socketio):
    global _started
    if _started:
        return
    _started = True

    thread = threading.Thread(target=_run, args=(app, socketio), daemon=True)
    thread.start()


def _run(app, socketio):
    while True:
        with app.app_context():
            db = __import__("app.database", fromlist=["get_db"]).get_db()
            vehicles = db.execute(
                """
                SELECT vehicles.*, routes.path_json, routes.name AS route_name, routes.color
                FROM vehicles
                JOIN routes ON routes.id = vehicles.route_id
                """
            ).fetchall()

            updated = []
            for vehicle in vehicles:
                path = json.loads(vehicle["path_json"])
                next_index = (vehicle["path_index"] + 1) % len(path)
                lat, lon = path[next_index]
                speed = max(10, min(70, vehicle["speed_kph"] + random.uniform(-6, 6)))
                occupancy = max(0, min(33, vehicle["occupancy"] + random.randint(-3, 4)))
                now = utc_now()

                db.execute(
                    """
                    UPDATE vehicles
                    SET latitude = ?, longitude = ?, speed_kph = ?, occupancy = ?, updated_at = ?, path_index = ?
                    WHERE id = ?
                    """,
                    (lat, lon, round(speed, 1), occupancy, now, next_index, vehicle["id"]),
                )
                db.execute(
                    """
                    INSERT INTO location_history
                        (vehicle_id, latitude, longitude, speed_kph, occupancy, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (vehicle["id"], lat, lon, round(speed, 1), occupancy, now),
                )
                updated.append(
                    {
                        "id": vehicle["id"],
                        "plate_number": vehicle["plate_number"],
                        "sacco": vehicle["sacco"],
                        "route_id": vehicle["route_id"],
                        "route_name": vehicle["route_name"],
                        "color": vehicle["color"],
                        "status": vehicle["status"],
                        "latitude": lat,
                        "longitude": lon,
                        "speed_kph": round(speed, 1),
                        "occupancy": occupancy,
                        "updated_at": now,
                    }
                )

            db.commit()
            socketio.emit("vehicle_updates", updated)

        time.sleep(5)
