/**
 * The only HTTP layer in the app. Pages never call fetch directly.
 *
 * There is deliberately no mock fallback: if the backend is unreachable the
 * pages render ErrorState. A dashboard that silently shows fixtures is worse
 * than one that says it cannot reach the API.
 */

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8010").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message, status, path) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
  }
}

async function request(path, { signal, method, body } = {}) {
  const url = `${API_URL}${path}`;
  const headers = { Accept: "application/json" };
  const init = { signal, headers };
  if (method) init.method = method;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(url, init);
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(
      `Cannot reach the API at ${API_URL}. Is the backend running?`,
      0,
      path,
    );
  }

  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? "");
    } catch {
      detail = await response.text().catch(() => "");
    }
    throw new ApiError(
      detail ? `${response.status}: ${detail}` : `Request failed (${response.status})`,
      response.status,
      path,
    );
  }

  if (response.status === 204) return null;
  return response.json();
}

const query = (params) => {
  const search = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "" || value === "All brands" || value === "All sources" || value === "All categories") return;
    search.set(key, value);
  });
  const text = search.toString();
  return text ? `?${text}` : "";
};

/* ------------------------------------------------------------------ */
/* Market overview                                                     */
/* ------------------------------------------------------------------ */

export const getMarketOverview = (filters = {}) =>
  request(`/api/analytics/overview${query({ brand: filters.brand })}`);

/* ------------------------------------------------------------------ */
/* Products                                                            */
/* ------------------------------------------------------------------ */

export const getProducts = (filters = {}) =>
  request(`/api/products${query({
    search: filters.query?.trim(),
    brand: filters.brand,
  })}`);

export const getProductComparison = (ids = []) => {
  const numeric = ids.map((id) => Number(id)).filter((id) => Number.isFinite(id));
  if (numeric.length < 2) return Promise.resolve([]);
  return request(`/api/products/compare?ids=${numeric.join(",")}`);
};

export const getProductDetail = (id) => {
  if (id === null || id === undefined) return Promise.resolve(null);
  return request(`/api/products/${Number(id)}`);
};

export const createProduct = (payload) =>
  request("/api/products/", { method: "POST", body: payload });

export const updateProduct = (id, payload) =>
  request(`/api/products/${Number(id)}`, { method: "PUT", body: payload });

export const deleteProduct = (id) =>
  request(`/api/products/${Number(id)}`, { method: "DELETE" });

export const importProductFromEmag = (searchTerm, category) =>
  request(`/api/products/import-from-emag${query({ query: searchTerm, category })}`, { method: "POST" });

/* ------------------------------------------------------------------ */
/* Brands                                                              */
/* ------------------------------------------------------------------ */

export const getBrandStats = (filters = {}) =>
  request(`/api/analytics/brands${query({ brand: filters.brand })}`);

/* ------------------------------------------------------------------ */
/* Sentiment                                                           */
/* ------------------------------------------------------------------ */

export const getSentiment = (filters = {}) =>
  request(`/api/analytics/sentiment${query({
    brand: filters.brand,
    source: filters.source,
  })}`);

/* ------------------------------------------------------------------ */
/* Consumer segments                                                   */
/* ------------------------------------------------------------------ */

export const getConsumerSegments = () => request("/api/analytics/consumer-segments");

/* ------------------------------------------------------------------ */
/* Marketing                                                           */
/* ------------------------------------------------------------------ */

export const getMarketingTrends = () => request("/api/marketing/trends");

/* ------------------------------------------------------------------ */
/* Competitors                                                         */
/* ------------------------------------------------------------------ */

export const getCompetitors = () => request("/api/analytics/competitors");

/* ------------------------------------------------------------------ */
/* Recommendations                                                     */
/* ------------------------------------------------------------------ */

export const getRecommendations = (filters = {}) =>
  request(`/api/analytics/recommendations${query({ category: filters.category === "All" ? "" : filters.category })}`);

/* ------------------------------------------------------------------ */
/* Diagnostics                                                         */
/* ------------------------------------------------------------------ */

export const getHealth = () => request("/health");

export const apiBaseUrl = API_URL;

/* ------------------------------------------------------------------ */
/* AI assistant (backend/server.py, optional)                          */
/* ------------------------------------------------------------------ */

const AI_API_URL = (import.meta.env.VITE_AI_API_URL || "").replace(/\/+$/, "");

// In-app assistant (backend/assistant.py). Streams Markdown; onText receives the full text so far.
export async function streamAssistantChat(payload, onText, signal) {
  if (!AI_API_URL) throw new Error("Set VITE_AI_API_URL in .env.local and start the backend to use the assistant.");
  let response;
  try {
    response = await fetch(`${AI_API_URL}/ai/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload), signal });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error(`Cannot reach the AI backend at ${AI_API_URL}. Start it with: uvicorn server:app --port 8000 (in backend/).`);
  }
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || `Request failed (${response.status})`);
  const meta = { intent: response.headers.get("X-Intent"), model: response.headers.get("X-Model") };
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let text = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    text += decoder.decode(value, { stream: true });
    onText(text, meta);
  }
  return { text, ...meta };
}

export async function askMarketingAdvisor(question, brand, history = []) {
  if (!AI_API_URL) throw new Error("Set VITE_AI_API_URL to use the marketing advisor");
  const response = await fetch(`${AI_API_URL}/ai/advice`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, brand: brand === "All brands" ? null : brand, history }),
  });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || `Request failed (${response.status})`);
  return response.json();
}
