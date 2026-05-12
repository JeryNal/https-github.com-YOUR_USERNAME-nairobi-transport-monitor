from app import create_app


def make_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.sqlite3"),
            "JWT_SECRET_KEY": "test-jwt-secret-with-at-least-32-bytes",
            "SIMULATION_ENABLED": False,
        }
    )


def login(client, username="admin", password="admin123"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.get_json()["access_token"]


def test_login_returns_jwt(tmp_path):
    app = make_app(tmp_path)
    with app.test_client() as client:
        token = login(client)
    assert token.count(".") == 2


def test_protected_routes_require_jwt(tmp_path):
    app = make_app(tmp_path)
    with app.test_client() as client:
        response = client.get("/api/vehicles")
    assert response.status_code == 401


def test_passenger_cannot_monitor_vehicles(tmp_path):
    app = make_app(tmp_path)
    with app.test_client() as client:
        token = login(client, "passenger", "passenger123")
        response = client.get("/api/vehicles", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_dashboard_api_returns_seeded_data(tmp_path):
    app = make_app(tmp_path)
    with app.test_client() as client:
        token = login(client)
        headers = {"Authorization": f"Bearer {token}"}
        vehicles = client.get("/api/vehicles", headers=headers)
        routes = client.get("/api/routes", headers=headers)
        analytics = client.get("/api/analytics", headers=headers)

    assert vehicles.status_code == 200
    assert routes.status_code == 200
    assert analytics.status_code == 200
    assert len(vehicles.get_json()) == 6
    assert len(routes.get_json()) == 3
    assert analytics.get_json()["summary"]["total_vehicles"] == 6


def test_passenger_can_read_traffic_updates(tmp_path):
    app = make_app(tmp_path)
    with app.test_client() as client:
        token = login(client, "passenger", "passenger123")
        response = client.get("/api/traffic", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert len(response.get_json()) == 3


def test_health_endpoint(tmp_path):
    app = make_app(tmp_path)
    with app.test_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
