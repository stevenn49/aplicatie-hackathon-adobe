import { BRANDS, brandStats, marketingTrend, overview, priceHistory, products, recommendations, segments, sentiment } from "../mocks/marketData.js";

const API_URL = import.meta.env.VITE_API_URL || "";
const delay = (data, ms = 360) => new Promise((resolve) => setTimeout(() => resolve(structuredClone(data)), ms));
const rangePoints = (range) => ({ "7d": 2, "30d": 5, "90d": 12, "1y": 12 }[range] || 12);

function filterProducts(filters = {}) {
  return products.filter((product) => {
    const matchesBrand = !filters.brand || filters.brand === "All brands" || product.brand === filters.brand;
    const query = filters.query?.trim().toLowerCase();
    const matchesQuery = !query || `${product.name} ${product.brand} ${product.category}`.toLowerCase().includes(query);
    return matchesBrand && matchesQuery;
  });
}

async function request(path, fallback) {
  if (!API_URL) return delay(fallback);
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) throw new Error(`Request failed (${response.status}) for ${path}`);
  return response.json();
}

export const getMarketOverview = (filters = {}) => request("/analytics/overview", {
  ...overview,
  evolution: overview.evolution.slice(-rangePoints(filters.range)),
  mentions: overview.mentions.filter((mention) =>
    (!filters.brand || filters.brand === "All brands" || mention.brand === filters.brand) &&
    (!filters.source || filters.source === "All sources" || mention.source === filters.source)),
  topMovers: [...filterProducts(filters)].sort((a, b) => b.change - a.change).slice(0, 4),
});
export const getProducts = (filters = {}) => request("/products", filterProducts(filters));
export const getProductComparison = (ids = ["p1", "p2"]) =>
  request(`/products/compare?ids=${ids.join(",")}`, products.filter((product) => ids.includes(product.id)));
export const getProductDetail = (id) => request(`/products/${id}`, products.find((product) => product.id === id) || null);
export const getBrandStats = (filters = {}) => request("/analytics/brands", filters.brand && filters.brand !== "All brands" ? brandStats.filter((item) => item.brand === filters.brand) : brandStats);
export const getSentiment = (filters = {}) => request("/analytics/sentiment", {
  ...sentiment,
  trend: sentiment.trend.slice(-rangePoints(filters.range)),
  reviews: sentiment.reviews.filter((review) =>
    (!filters.source || filters.source === "All sources" || review.source === filters.source) &&
    (!filters.brand || filters.brand === "All brands" || review.brand === filters.brand)),
});
export const getConsumerSegments = () => request("/analytics/consumer-segments", segments);
export const getMarketingTrends = (filters = {}) => request("/marketing/trends", marketingTrend.slice(-rangePoints(filters.range)));
export const getCompetitors = () => request("/analytics/competitors", {
  brands: BRANDS,
  priceDifferences: products.slice(0, 5).map((product) => ({ name: product.name, brand: product.brand, price: product.price, baseline: 999, difference: product.price - 999 })),
});
const AI_API_URL = import.meta.env.VITE_AI_API_URL || "";

// AI recommendations come from the Python AI backend (backend/server.py) when
// VITE_AI_API_URL is set; on any failure the page falls back to the mock recommendations.
export async function getRecommendations(filters = {}) {
  const fallback = filters.category && filters.category !== "All" ? recommendations.filter((item) => item.category === filters.category) : recommendations;
  if (!AI_API_URL) return request("/analytics/recommendations", fallback);
  const params = new URLSearchParams();
  if (filters.category && filters.category !== "All") params.set("category", filters.category);
  try {
    const response = await fetch(`${AI_API_URL}/analytics/recommendations?${params}`);
    if (!response.ok) throw new Error(`AI backend returned ${response.status}`);
    return await response.json();
  } catch (error) {
    console.warn("AI recommendations unavailable, using mock data:", error);
    return structuredClone(fallback);
  }
}

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
