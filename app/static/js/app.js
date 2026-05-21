const STAFF_ROLES = new Set(["admin", "manager", "driver"]);

const state = {
  token: localStorage.getItem("transport_token"),
  user: JSON.parse(localStorage.getItem("transport_user") || "null"),
  map: null,
  markers: new Map(),
  routeLayers: [],
  vehicles: [],
  trafficUpdates: [],
  selectedRouteId: "",
  routeSearch: "",
  operationsAlerts: [],
  matatuImages: [],
};

const els = {
  homePage: document.querySelector("#homePage"),
  dashboard: document.querySelector("#dashboard"),
  passengerPage: document.querySelector("#passengerPage"),
  staffLoginForm: document.querySelector("#staffLoginForm"),
  passengerLoginForm: document.querySelector("#passengerLoginForm"),
  staffLoginError: document.querySelector("#staffLoginError"),
  passengerLoginError: document.querySelector("#passengerLoginError"),
  staffUsername: document.querySelector("#staffUsername"),
  staffPassword: document.querySelector("#staffPassword"),
  passengerUsername: document.querySelector("#passengerUsername"),
  passengerPassword: document.querySelector("#passengerPassword"),
  connectionStatus: document.querySelector("#connectionStatus"),
  roleBadge: document.querySelector("#roleBadge"),
  logoutButton: document.querySelector("#logoutButton"),
  homeButton: document.querySelector("#homeButton"),
  vehicleList: document.querySelector("#vehicleList"),
  operationsAlerts: document.querySelector("#operationsAlerts"),
  matatuPhotoGrid: document.querySelector("#matatuPhotoGrid"),
  trafficList: document.querySelector("#trafficList"),
  routeSelect: document.querySelector("#routeSelect"),
  routeSearch: document.querySelector("#routeSearch"),
  selectedRouteSummary: document.querySelector("#selectedRouteSummary"),
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

function setSession(payload) {
  state.token = payload.access_token;
  state.user = payload.user;
  localStorage.setItem("transport_token", state.token);
  localStorage.setItem("transport_user", JSON.stringify(state.user));
  els.roleBadge.textContent = state.user.role;
  els.logoutButton.classList.remove("d-none");
}

function clearSession() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("transport_token");
  localStorage.removeItem("transport_user");
  els.roleBadge.textContent = "Guest";
  els.logoutButton.classList.add("d-none");
  showHome();
}

function hideScreens() {
  els.homePage.classList.add("d-none");
  els.dashboard.classList.add("d-none");
  els.passengerPage.classList.add("d-none");
}

function showHome() {
  hideScreens();
  els.homePage.classList.remove("d-none");
}

function showDashboard() {
  hideScreens();
  els.dashboard.classList.remove("d-none");
  if (!state.map) {
    initMap();
  }
}

function showPassengerPage() {
  hideScreens();
  els.passengerPage.classList.remove("d-none");
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
  state.routeLayers = routes.map((route) => {
    const layer = L.polyline(route.path, {
      color: route.color,
      weight: 5,
      opacity: 0.75,
    })
      .bindPopup(`${route.name}: ${route.origin} to ${route.destination}`)
      .addTo(state.map);
    layer.routeId = route.id;
    return layer;
  });
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
          <div class="vehicle-meta">${vehicle.route_name} - ${vehicle.occupancy} passengers</div>
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

function severityClass(severity) {
  return (severity || "clear").toLowerCase();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return replacements[character];
  });
}

function renderMatatuImages(images) {
  state.matatuImages = images;
  if (!images.length) {
    els.matatuPhotoGrid.innerHTML = `
      <div class="photo-placeholder">
        Road photos are unavailable right now. Please try again later.
      </div>
    `;
    return;
  }

  els.matatuPhotoGrid.innerHTML = images
    .map(
      (image) => {
        const title = escapeHtml(image.title || "Nairobi matatu on the road");
        const creditLine = [image.credit, image.license].filter(Boolean).map(escapeHtml).join(" | ");
        const sourceUrl = escapeHtml(image.source_url || "");
        return `
        <article class="photo-card">
          <img src="${escapeHtml(image.image_url)}" alt="${title}" loading="lazy">
          <div class="photo-caption">
            <strong>${title}</strong>
            ${creditLine ? `<span>${creditLine}</span>` : ""}
            ${sourceUrl ? `<a href="${sourceUrl}" target="_blank" rel="noopener">Source</a>` : ""}
          </div>
        </article>
      `;
      }
    )
    .join("");
}

async function loadMatatuImages() {
  try {
    const images = await api("/api/matatu-images?limit=6");
    renderMatatuImages(images);
  } catch (error) {
    renderMatatuImages([]);
  }
}

function renderOperationsAlerts(updates) {
  const alerts = updates.filter((update) => severityClass(update.severity) !== "clear");
  state.operationsAlerts = alerts;
  if (!alerts.length) {
    els.operationsAlerts.innerHTML = `
      <div class="alert-item">
        <strong>No route alerts</strong>
        <div class="vehicle-meta">All monitored routes are operating normally.</div>
      </div>
    `;
    return;
  }

  els.operationsAlerts.innerHTML = alerts
    .map((update) => {
      const level = severityClass(update.severity);
      return `
        <button class="alert-item ${level}" type="button" data-route-id="${update.route_id}">
          <span class="traffic-severity ${level}">${update.severity || "Clear"}</span>
          <strong>${update.name}</strong>
          <span class="vehicle-meta">${update.origin} to ${update.destination}</span>
          <span class="pressure-line">Pressure score: ${update.pressure_score ?? 0}</span>
          <span class="vehicle-meta">${update.next_action}</span>
        </button>
      `;
    })
    .join("");
}

function renderTraffic(updates) {
  state.trafficUpdates = updates;
  const filteredUpdates = filterTrafficUpdates(updates);
  renderSelectedRouteSummary(filteredUpdates);
  els.trafficList.innerHTML = filteredUpdates
    .map((update) => {
      const level = severityClass(update.severity);
      return `
        <article class="traffic-card ${level}">
          <span class="traffic-severity ${level}">${update.severity || "Clear"}</span>
          <h2 class="h5 mt-3">${update.name}</h2>
          <p class="text-secondary mb-2">${update.origin} to ${update.destination}</p>
          <p>${update.message}</p>
          ${update.saved_message ? `<p class="small text-secondary">Route note: ${update.saved_message}</p>` : ""}
          <p class="small action-line"><strong>Suggested action:</strong> ${update.next_action}</p>
          <div class="small text-secondary">
            Avg speed: ${update.average_speed ?? 0} kph<br>
            Avg load: ${update.average_occupancy ?? 0} passengers<br>
            Pressure score: ${update.pressure_score ?? 0}<br>
            Vehicles active: ${update.vehicles ?? 0}
          </div>
        </article>
      `;
    })
    .join("") || `<div class="traffic-card"><h2 class="h5">No matching route</h2><p class="text-secondary mb-0">Try searching for Ngong, Thika, Mombasa, CBD, Karen, Ruiru, or Athi River.</p></div>`;
}

function populateRouteSelect(updates) {
  els.routeSelect.innerHTML = `<option value="">All routes</option>${updates
    .map((update) => `<option value="${update.route_id}">${update.name}</option>`)
    .join("")}`;
  els.routeSelect.value = state.selectedRouteId;
}

function filterTrafficUpdates(updates) {
  const query = state.routeSearch.trim().toLowerCase();
  return updates.filter((update) => {
    const matchesSelect = !state.selectedRouteId || String(update.route_id) === state.selectedRouteId;
    const text = `${update.name} ${update.origin} ${update.destination}`.toLowerCase();
    const matchesSearch = !query || text.includes(query);
    return matchesSelect && matchesSearch;
  });
}

function renderSelectedRouteSummary(updates) {
  if (updates.length !== 1) {
    els.selectedRouteSummary.classList.add("d-none");
    els.selectedRouteSummary.innerHTML = "";
    return;
  }

  const update = updates[0];
  els.selectedRouteSummary.classList.remove("d-none");
  els.selectedRouteSummary.innerHTML = `
    <strong>${update.name}</strong> is currently <strong>${update.severity}</strong>.
    Average speed is <strong>${update.average_speed ?? 0} kph</strong>,
    average load is <strong>${update.average_occupancy ?? 0} passengers</strong>,
    with <strong>${update.vehicles ?? 0}</strong> active vehicles.
  `;
}

async function loadDashboard() {
  showDashboard();
  const [routes, vehicles, analytics, traffic] = await Promise.all([
    api("/api/routes", { headers: authHeaders() }),
    api("/api/vehicles", { headers: authHeaders() }),
    api("/api/analytics", { headers: authHeaders() }),
    api("/api/traffic", { headers: authHeaders() }),
  ]);
  renderRoutes(routes);
  renderVehicles(vehicles);
  renderAnalytics(analytics);
  renderOperationsAlerts(traffic);
}

async function loadPassengerUpdates() {
  showPassengerPage();
  const updates = await api("/api/traffic", { headers: authHeaders() });
  populateRouteSelect(updates);
  renderTraffic(updates);
}

async function login(username, password) {
  return api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
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
    if (!state.token || !state.user) {
      return;
    }
    if (!els.dashboard.classList.contains("d-none") && STAFF_ROLES.has(state.user.role)) {
      renderVehicles(vehicles);
      api("/api/analytics", { headers: authHeaders() }).then(renderAnalytics).catch(() => {});
      api("/api/traffic", { headers: authHeaders() }).then(renderOperationsAlerts).catch(() => {});
    }
    if (!els.passengerPage.classList.contains("d-none")) {
      api("/api/traffic", { headers: authHeaders() })
        .then((updates) => {
          populateRouteSelect(updates);
          renderTraffic(updates);
        })
        .catch(() => {});
    }
  });
}

els.staffLoginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  els.staffLoginError.textContent = "";
  try {
    const payload = await login(els.staffUsername.value, els.staffPassword.value);
    if (!STAFF_ROLES.has(payload.user.role)) {
      throw new Error("Only admins, managers, and drivers can open the monitor");
    }
    setSession(payload);
    await loadDashboard();
  } catch (error) {
    els.staffLoginError.textContent = error.message;
  }
});

els.passengerLoginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  els.passengerLoginError.textContent = "";
  try {
    const payload = await login(els.passengerUsername.value, els.passengerPassword.value);
    setSession(payload);
    await loadPassengerUpdates();
  } catch (error) {
    els.passengerLoginError.textContent = error.message;
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

els.operationsAlerts.addEventListener("click", (event) => {
  const item = event.target.closest(".alert-item");
  if (!item || !state.map) return;
  const routeLayer = state.routeLayers.find((layer) => String(layer.routeId) === item.dataset.routeId);
  if (routeLayer) {
    state.map.fitBounds(routeLayer.getBounds(), { padding: [28, 28] });
    routeLayer.openPopup();
  }
});

els.logoutButton.addEventListener("click", clearSession);
els.homeButton.addEventListener("click", showHome);
els.routeSelect.addEventListener("change", () => {
  state.selectedRouteId = els.routeSelect.value;
  renderTraffic(state.trafficUpdates);
});
els.routeSearch.addEventListener("input", () => {
  state.routeSearch = els.routeSearch.value;
  renderTraffic(state.trafficUpdates);
});

initSocket();
loadMatatuImages();
if (state.token && state.user) {
  els.roleBadge.textContent = state.user.role;
  els.logoutButton.classList.remove("d-none");
  if (STAFF_ROLES.has(state.user.role)) {
    loadDashboard().catch(clearSession);
  } else {
    loadPassengerUpdates().catch(clearSession);
  }
}
