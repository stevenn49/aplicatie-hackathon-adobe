import { useMemo, useState } from "react";
import { ArrowUpRight, Check, ChevronDown, Filter, Lightbulb, Sparkles, Target } from "lucide-react";
import { apiBaseUrl, getRecommendations } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { InsightCard, EmptyState, ErrorState, PageHeading, PageLoading } from "../components/common.jsx";

const categories = ["All", "Product", "Consumer", "Marketing", "Competitive"];

export default function AIRecommendations() {
  const { filters } = useFilters();
  const [category, setCategory] = useState("All");
  const state = useFetch(() => getRecommendations({ category }), [category]);

  const recommendations = useMemo(
    () => (state.data?.items || []).filter(
      (item) => filters.brand === "All brands" || item.related.startsWith(filters.brand),
    ),
    [state.data, filters.brand],
  );

  if (state.loading) return <PageLoading />;
  if (state.error) return <ErrorState error={state.error} />;
  if (!state.data) return <EmptyState />;

  const { summary, items } = state.data;
  const highPriority = recommendations.filter((item) => item.priority === "High").length;

  return (
    <div className="page">
      <PageHeading
        eyebrow="YOUR AI STRATEGY PARTNER"
        title="The signal, and what to do next."
        description="Evidence-backed recommendations, prioritized by impact and confidence."
        action={
          <span className="ai-status-pill">
            <span className="ai-pulse"><Sparkles size={13} /></span>
            {summary.source === "llm" ? "OpenRouter model" : summary.source === "pending" ? "Generating…" : "Derived engine"}
            <span className="mini-online" />
          </span>
        }
      />

      <section className="executive-summary panel">
        <div className="summary-icon"><Sparkles size={20} /></div>
        <div className="summary-content">
          <div className="summary-topline">
            <span className="eyebrow">EXECUTIVE SUMMARY</span>
            <span className="summary-generated">
              {summary.source === "llm"
                ? "Written by the configured model"
                : summary.source === "pending"
                  ? "Derived now; the written summary is generating"
                  : "Derived from stored data"}
              <span className="live-dot" />
            </span>
          </div>
          <h2>{summary.headline}</h2>
          <p>{summary.body}</p>
          <div className="summary-evidence">
            <span><Target size={13} /> {items.length} recommendations</span>
            <span><Lightbulb size={13} /> {highPriority} high-priority actions</span>
            {summary.avg_confidence !== null && <span><Check size={13} /> {summary.avg_confidence.toFixed(1)}% avg. confidence</span>}
          </div>
        </div>
        {summary.readiness !== null && (
          <div className="summary-score">
            <span>Market readiness</span>
            <strong>{summary.readiness.toFixed(0)}<span>/100</span></strong>
            <div className="health-gauge"><i style={{ width: `${summary.readiness}%` }} /></div>
            <small className="muted">70% sentiment + 30% pressure</small>
          </div>
        )}
      </section>

      <div className="recommendation-toolbar">
        <div className="recommendation-tabs" role="group" aria-label="Filter recommendations">
          {categories.map((item) => (
            <button key={item} className={category === item ? "active" : ""} onClick={() => setCategory(item)}>
              {item}{item === "All" && <span>{state.data.items.length}</span>}
            </button>
          ))}
        </div>
        <span className="recommendation-sort"><Filter size={14} /> Sorted by impact <ChevronDown size={14} /></span>
      </div>

      {recommendations.length ? (
        <>
          <div className="recommendation-list">
            {recommendations.map((item, index) => (
              <div className="recommendation-item" key={item.id}>
                <span className="recommendation-number">0{index + 1}</span>
                <InsightCard item={item} />
              </div>
            ))}
          </div>
          <div className="recommendation-footer">
            <span><Sparkles size={14} /> Recommendations are generated from live product, consumer, and market signals.</span>
            <button className="button button-quiet" onClick={() => window.open(`${apiBaseUrl}/docs`, "_blank", "noopener")}>
              How we calculate this <ArrowUpRight size={14} />
            </button>
          </div>
        </>
      ) : <EmptyState title="No recommendations for this view" description="Try another category or clear the global brand filter." />}
    </div>
  );
}
