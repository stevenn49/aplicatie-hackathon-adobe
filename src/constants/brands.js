/**
 * Product scope, not data.
 *
 * The five brands the dashboard is positioned around. The backend is the source
 * of truth for everything else (shares, sentiment, colours on the payload); this
 * list only drives the global filter, which must render before any request
 * completes. Colours here are a fallback for components that receive a brand
 * name without a payload colour.
 */
export const BRAND_NAMES = ["Apple", "NVIDIA", "Microsoft", "Samsung", "Sony"];

export const BRAND_COLORS = {
  Apple: "#8b8cf7",
  NVIDIA: "#9bd94e",
  Microsoft: "#59a9f5",
  Samsung: "#f0a35e",
  Sony: "#e8788c",
};

export const SOURCES = ["eMAG", "Reddit", "X", "Google Trends", "TechCommunity"];

export const RANGES = ["7d", "30d", "90d", "1y"];

export const formatMoney = (value, currency = "RON") => {
  if (value === null || value === undefined) return "—";
  const suffix = currency === "RON" ? "lei" : currency;
  return `${Number(value).toLocaleString("ro-RO", { maximumFractionDigits: 2 })} ${suffix}`;
};

export const formatNumber = (value, digits = 1) =>
  value === null || value === undefined ? "—" : Number(value).toFixed(digits);

export const formatPercent = (value, digits = 1) =>
  value === null || value === undefined ? "—" : `${Number(value).toFixed(digits)}%`;
