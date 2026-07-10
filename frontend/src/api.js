const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8001/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "API request failed");
  }

  return response.json();
}

export const api = {
  getHcps: () => request("/hcps"),
  getInteractions: () => request("/interactions"),
  logInteraction: (payload) =>
    request("/interactions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  chat: (payload) =>
    request("/agent/chat", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  toolsDemo: () => request("/agent/tools/demo"),
};
