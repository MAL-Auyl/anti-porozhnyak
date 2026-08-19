const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: "include", // send the session cookie (auth.py binding)
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(body.detail || `HTTP ${res.status}`);
    err.status = res.status;
    err.body = body;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (name, role) => request("/auth/login", { method: "POST", body: JSON.stringify({ name, role }) }),

  parseLoad: (text) => request("/loads/parse", { method: "POST", body: JSON.stringify({ text }) }),
  createLoad: (payload) => request("/loads", { method: "POST", body: JSON.stringify(payload) }),
  listLoads: (status) => request(`/loads${status ? `?status=${status}` : ""}`),
  markDelivered: (loadId) => request(`/loads/${loadId}/deliver`, { method: "POST" }),

  createVehicle: (payload) => request("/vehicles", { method: "POST", body: JSON.stringify(payload) }),
  listVehicles: () => request("/vehicles"),

  vehicleMatches: (vehicleId) => request(`/vehicles/${vehicleId}/matches`),
  explainMatch: (matchId) => request(`/matches/${matchId}/explain`),
  acceptMatch: (matchId) => request(`/matches/${matchId}/accept`, { method: "POST" }),
  allMatches: () => request("/matches"),
};

export { BASE_URL };
