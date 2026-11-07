import { ArrowDownRight, ArrowUpRight, AlertCircle, Boxes, Heart, Layers3, MessageSquareText, Sparkles, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { BRAND_COLORS } from "../constants/brands.js";
import { useChat, useRegisterChart } from "../context/ChatContext.jsx";

export const SENTIMENT_COLORS = { positive: "var(--positive)", neutral: "var(--neutral)", negative: "var(--negative)" };
const kpiIcons = { layers: Layers3, message: MessageSquareText, heart: Heart, trend: TrendingUp };

export function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>
      {action && <div className="page-heading-action">{action}</div>}
    </div>
  );
}

export function KpiCard({ label, value, suffix, change, note, tone = "positive", icon, spark = [] }) {
  const Icon = kpiIcons[icon] || TrendingUp;
  const points = (spark || []).map((point, index) => `${index * 100 / Math.max((spark || []).length - 1, 1)},${35 - point}`).join(" ");
  const hasChange = Boolean(change);
  return (
    <article className="kpi-card">
      <div className="kpi-top"><span>{label}</span><span className="kpi-icon"><Icon size={16} /></span></div>
      <div className="kpi-value-row"><strong className="metric">{value}</strong>{suffix && <span className="kpi-suffix">{suffix}</span>}</div>
      <div className="kpi-bottom">
        {hasChange && <span className={`delta ${tone}`}>{change.startsWith("-") || change.startsWith("↓") ? <ArrowDownRight size={14} /> : <ArrowUpRight size={14} />}{change}</span>}
        {note && <span className="kpi-note">{note}</span>}
      </div>
      {points && <svg className="sparkline" viewBox="0 0 100 36" preserveAspectRatio="none" aria-hidden="true"><polyline points={points} fill="none" stroke={tone === "negative" ? "var(--negative)" : "var(--accent)"} strokeWidth="2" vectorEffect="non-scaling-stroke" /></svg>}
    </article>
  );
}

// Pass `data` (the rows the chart plots) to let the in-app assistant analyse the chart.
export function ChartCard({ title, subtitle, action, className = "", data, note, children }) {
  const { askAssistant } = useChat();
  const id = useRegisterChart(data ? { title, subtitle, data, note } : null);
  const analyse = id && <button type="button" className="chart-ask-ai" onClick={() => askAssistant(`Analyse the "${title}" chart`, id)} title="Analyse this chart with MarketPulse AI"><Sparkles size={13} /><span>Analyse</span></button>;
  return <section className={`panel chart-card ${className}`}><div className="panel-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{(action || analyse) && <div className="panel-action">{action}{analyse}</div>}</div>{children}</section>;
}

export function SentimentBadge({ sentiment, children }) {
  return <span className={`sentiment-badge ${sentiment}`}>{children || sentiment}</span>;
}

export function BrandTag({ brand, color, compact = false }) {
  const resolved = color || BRAND_COLORS[brand] || "var(--text-muted)";
  return <span className={`brand-tag ${compact ? "compact" : ""}`}><span className="brand-dot" style={{ backgroundColor: resolved }} />{brand}</span>;
}

export function SourceTag({ source }) {
  const symbols = { eMAG: "e", Reddit: "r", X: "𝕏", "Google Trends": "G", TechCommunity: "H" };
  return <span className={`source-tag source-${source?.toLowerCase().replace(" ", "-")}`}><span>{symbols[source] || "•"}</span>{source}</span>;
}

export function EmptyState({ title = "No data available", description = "Try adjusting your filters to explore more insights." }) {
  return <div className="empty-state"><span className="empty-icon"><Boxes size={20} /></span><strong>{title}</strong><p>{description}</p></div>;
}

export function ErrorState({ error, onRetry }) {
  return <div className="empty-state error-state"><span className="empty-icon"><AlertCircle size={20} /></span><strong>We couldn’t load this data</strong><p>{error?.message || "Please check your connection and try again."}</p>{onRetry && <button className="button button-quiet" onClick={onRetry}>Try again</button>}</div>;
}

export function Skeleton({ count = 3, className = "" }) {
  return <div className={`skeleton-stack ${className}`} aria-label="Loading content" aria-busy="true">{Array.from({ length: count }, (_, i) => <div className="skeleton-line" key={i} style={{ width: `${88 - i * 11}%` }} />)}</div>;
}

export function PageLoading() {
  return <div className="page-loading" aria-label="Loading dashboard" aria-busy="true"><div className="skeleton-heading"><Skeleton count={2} /></div><div className="skeleton-kpis">{[1, 2, 3, 4].map((item) => <div className="panel skeleton-card" key={item}><Skeleton count={3} /></div>)}</div><div className="panel skeleton-chart"><Skeleton count={5} /></div></div>;
}

export function InsightCard({ item }) {
  return (
    <article className="panel insight-card">
      <div className="insight-top"><span className={`priority-dot ${item.priority.toLowerCase()}`} /><span className={`priority-label ${item.priority.toLowerCase()}`}>{item.priority} priority</span><span className="insight-category">{item.category}</span><span className="insight-confidence">{item.confidence}% confidence</span></div>
      <h3>{item.title}</h3><p className="insight-detail">{item.detail}</p>
      <div className="insight-evidence"><Sparkles size={14} /><span>{item.metric}</span><span className="insight-related">{item.related}</span></div>
      <Link to={item.route} className="text-link">View evidence <ArrowUpRight size={14} /></Link>
    </article>
  );
}

export function BrandLegend({ brands = [], colors = {} }) {
  return <div className="brand-legend">{brands.map((brand) => <BrandTag key={brand} brand={brand} color={colors[brand]} compact />)}</div>;
}

export function DataTable({ columns, rows, rowKey = "id", onRowClick, emptyTitle }) {
  if (!rows.length) return <EmptyState title={emptyTitle || "No matching results"} />;
  return <div className="table-scroll"><table className="data-table"><thead><tr>{columns.map((column) => <th key={column.key} className={column.className || ""}>{column.label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={row[rowKey] ?? index} onClick={onRowClick ? () => onRowClick(row) : undefined} className={onRowClick ? "clickable-row" : ""}>{columns.map((column) => <td key={column.key} className={column.className || ""}>{column.render ? column.render(row) : row[column.key]}</td>)}</tr>)}</tbody></table></div>;
}
