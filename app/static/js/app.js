const state = {
  token: localStorage.getItem("transport_token"),
  map: null,
  markers: new Map(),
  routeLayers: [],
  vehicles: [],
};

const els = {
  loginPanel: document.querySelector("#loginPanel"),
  dashboard: document.querySelector("#dashboard"),
  loginForm: document.querySelector("#loginForm"),
  loginError: document.querySelector("#loginError"),
  username: document.querySelector("#username"),
  password: document.querySelector("#password"),
  connectionStatus: document.querySelector("#connectionStatus"),
  vehicleList: document.querySelector("#vehicleList"),
  totalVehicles: document.querySelector("#totalVehicles"),
  activeVehicles: document.querySelector("#activeVehicles"),
  avgSpeed: document.querySelector("#avgSpeed"),
  avgOccupancy: document.querySelector("#avgOccupancy"),
};

function authHeaders() {
  return { Authorization: `Bearer ${state.token}` };
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

function showDashboard() {
  els.loginPanel.classList.add("d-none");
  els.dashboard.classList.remove("d-none");
  if (!state.map) {
    initMap();
  }
}

function initMap() {
  state.map = L.map("map").setView([-1.2864, 36.8172], 11);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(state.map);
}

function renderRoutes(routes) {
  state.routeLayers.forEach((layer) => layer.remove());
  state.routeLayers = routes.map((route) =>
    L.polyline(route.path, {
      color: route.color,
      weight: 5,
      opacity: 0.75,
    })
      .bindPopup(`${route.name}: ${route.origin} to ${route.destination}`)
      .addTo(state.map)
  );
}

function renderVehicles(vehicles) {
  state.vehicles = vehicles;
  vehicles.forEach((vehicle) => {
    const latLng = [vehicle.latitude, vehicle.longitude];
    const popup = `
      <strong>${vehicle.plate_number}</strong><br>
      ${vehicle.sacco}<br>
      ${vehicle.route_name}<br>
      ${vehicle.speed_kph} kph, ${vehicle.occupancy} passengers
    `;

    if (!state.markers.has(vehicle.id)) {
      const marker = L.circleMarker(latLng, {
        radius: 9,
        color: vehicle.color,
        fillColor: vehicle.color,
        fillOpacity: 0.85,
      }).addTo(state.map);
      state.markers.set(vehicle.id, marker);
    }

    state.markers.get(vehicle.id).setLatLng(latLng).bindPopup(popup);
  });

  els.vehicleList.innerHTML = vehicles
    .map(
      (vehicle) => `
        <div class="vehicle-item" data-id="${vehicle.id}">
          <div class="d-flex justify-content-between">
            <strong>${vehicle.plate_number}</strong>
            <span>${vehicle.speed_kph} kph</span>
          </div>
          <div class="vehicle-meta">${vehicle.route_name} · ${vehicle.occupancy} passengers</div>
        </div>
      `
    )
    .join("");
}

function renderAnalytics(data) {
  els.totalVehicles.textContent = data.summary.total_vehicles ?? 0;
  els.activeVehicles.textContent = data.summary.active_vehicles ?? 0;
  els.avgSpeed.textContent = `${data.summary.average_speed ?? 0}`;
  els.avgOccupancy.textContent = `${data.summary.average_occupancy ?? 0}`;
}

async function loadDashboard() {
  showDashboard();
  const [routes, vehicles, analytics] = await Promise.all([
    api("/api/routes", { headers: authHeaders() }),
    api("/api/vehicles", { headers: authHeaders() }),
    api("/api/analytics", { headers: authHeaders() }),
  ]);
  renderRoutes(routes);
  renderVehicles(vehicles);
  renderAnalytics(analytics);
}

function initSocket() {
  const socket = io();
  socket.on("connect", () => {
    els.connectionStatus.textContent = "Live";
    els.connectionStatus.className = "badge text-bg-success";
  });
  socket.on("disconnect", () => {
    els.connectionStatus.textContent = "Offline";
    els.connectionStatus.className = "badge text-bg-secondary";
  });
  socket.on("vehicle_updates", (vehicles) => {
    if (!state.token || els.dashboard.classList.contains("d-none")) {
      return;
    }
    renderVehicles(vehicles);
    api("/api/analytics", { headers: authHeaders() }).then(renderAnalytics).catch(() => {});
  });
}

els.loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  els.loginError.textContent = "";
  try {
    const payload = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username: els.username.value,
        password: els.password.value,
      }),
    });
    state.token = payload.access_token;
    localStorage.setItem("transport_token", state.token);
    await loadDashboard();
  } catch (error) {
    els.loginError.textContent = error.message;
  }
});

els.vehicleList.addEventListener("click", (event) => {
  const item = event.target.closest(".vehicle-item");
  if (!item) return;
  const marker = state.markers.get(Number(item.dataset.id));
  if (marker) {
    state.map.setView(marker.getLatLng(), 13);
    marker.openPopup();
  }
});

initSocket();
if (state.token) {
  loadDashboard().catch(() => {
    localStorage.removeItem("transport_token");
    state.token = null;
    els.dashboard.classList.add("d-none");
    els.loginPanel.classList.remove("d-none");
  });
}
