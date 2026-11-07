import { useState } from "react";
import { Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowUpRight, CalendarDays, Lightbulb, Megaphone, Radio, Target } from "lucide-react";
import { getMarketingTrends } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { ChartCard, EmptyState, ErrorState, KpiCard, PageHeading, PageLoading } from "../components/common.jsx";
import { ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";
import { formatNumber } from "../constants/brands.js";

const SOURCE_COLORS = ["var(--accent)", "#8b8cf7", "var(--positive)", "var(--neutral)", "#73baf5"];

export default function MarketingAnalytics() {
  const { filters } = useFilters();
  const state = useFetch(() => getMarketingTrends(filters), [filters.brand]);
  const [activeMetric, setActiveMetric] = useState("Brand interest");

  if (state.loading) return <PageLoading />;
  if (state.error) return <ErrorState error={state.error} />;
  if (!state.data) return <EmptyState />;

  const { trends, opportunities, opportunities_source: opportunitySource, kpis, source_volume: sourceVolume } = state.data;

  const brand = filters.brand === "All brands" ? null : filters.brand;
  const trendKeys = trends.length ? Object.keys(trends[0]).filter((key) => !["date", "event", "Reddit", "X", "eMAG", "TechCommunity"].includes(key)) : [];
  const focusBrand = brand || trendKeys[0];
  const focusColor = { Apple: "#8b8cf7", NVIDIA: "#9bd94e", Microsoft: "#59a9f5", Samsung: "#f0a35e", Sony: "#e8788c" }[focusBrand] || "var(--accent)";
  const events = trends.filter((point) => point.event);

  return (
    <div className="page">
      <PageHeading
        eyebrow="CAMPAIGN & DEMAND SIGNALS"
        title="Marketing analytics"
        description="Spot growing demand, measure campaign lift, find your next story."
        action={<span className="freshness-pill"><span className="live-dot" /> Computed from stored reviews</span>}
      />

      <div className="marketing-kpi-row">
        {kpis.map((kpi, index) => {
          const icons = [Radio, Megaphone, Target, CalendarDays];
          const Icon = icons[index % icons.length];
          return (
            <div className="marketing-kpi panel" key={kpi.label}>
              <span className="kpi-icon"><Icon size={16} /></span>
              <span className="marketing-kpi-label">{kpi.label}</span>
              <strong>{kpi.value}{kpi.suffix && <small> {kpi.suffix}</small>}</strong>
              <span className="delta neutral">{kpi.note}</span>
            </div>
          );
        })}
      </div>

      <div className="marketing-chart-grid">
        <ChartCard
          title="Mention volume over time"
          subtitle="Weekly mentions per brand and source, indexed to 100"
          data={trends}
          className="marketing-interest-chart"
          action={
            <div className="metric-switch">
              {["Brand interest", "Product interest"].map((item) => (
                <button key={item} className={activeMetric === item ? "active" : ""} onClick={() => setActiveMetric(item)}>{item}</button>
              ))}
            </div>
          }
        >
          {trends.length ? (
            <>
              <div className="campaign-legend">
                <span><i style={{ background: focusColor }} />{focusBrand} mentions</span>
                <span><i className="legend-dashed" />Reddit</span>
                <span><i style={{ background: "#8b8cf7" }} />X</span>
              </div>
              <ResponsiveChart height={280}>
                <ComposedChart data={trends} margin={chartMargin}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="date" {...axisProps} />
                  <YAxis {...axisProps} domain={[0, 100]} />
                  <Tooltip />
                  <Area type="monotone" dataKey={focusBrand} name={`${focusBrand} mentions`} stroke={focusColor} fill={focusColor} fillOpacity={0.10} strokeWidth={2.2} connectNulls />
                  <Line type="monotone" dataKey="Reddit" name="Reddit mentions" stroke="var(--text-muted)" strokeDasharray="5 5" strokeWidth={1.7} dot={false} connectNulls />
                  <Line type="monotone" dataKey="X" name="X mentions" stroke="#8b8cf7" strokeDasharray="2 4" strokeWidth={1.7} dot={false} connectNulls />
                </ComposedChart>
              </ResponsiveChart>
            </>
          ) : <EmptyState title="No mention history yet" />}
        </ChartCard>

        <ChartCard title="Where the conversation lives" subtitle="Mention volume by source" data={sourceVolume}>
          {sourceVolume.length ? (
            <>
              <ResponsiveChart height={244}>
                <BarChart data={sourceVolume} margin={chartMargin}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="source" {...axisProps} />
                  <YAxis {...axisProps} tickFormatter={(value) => `${value}`} />
                  <Tooltip formatter={(value) => `${value} mentions`} />
                  <Bar dataKey="mentions" name="Mentions" radius={[5, 5, 0, 0]} barSize={30}>
                    {sourceVolume.map((item, index) => <Cell fill={SOURCE_COLORS[index % SOURCE_COLORS.length]} key={item.source} />)}
                  </Bar>
                </BarChart>
              </ResponsiveChart>
              <div className="source-summary">
                <span><i className="source-indicator reddit" />{sourceVolume[0].source} leads conversation share</span>
                <strong>{((sourceVolume[0].mentions / sourceVolume.reduce((sum, item) => sum + item.mentions, 0)) * 100).toFixed(1)}%</strong>
              </div>
            </>
          ) : <EmptyState title="No sources yet" />}
        </ChartCard>
      </div>

      <div className="campaign-timeline panel">
        <div className="panel-heading">
          <div><h2>Campaign reaction timeline</h2><p>Events that moved the conversation</p></div>
          <span className="timeline-range">Last 12 weeks <CalendarDays size={13} /></span>
        </div>
        {trends.length ? (
          <>
            <div className="timeline-chart-wrap">
              <ResponsiveChart height={175}>
                <ComposedChart data={trends} margin={{ ...chartMargin, top: 15 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="date" {...axisProps} />
                  <YAxis {...axisProps} hide />
                  <Tooltip />
                  <Area type="monotone" dataKey={focusBrand} name="Mention index" fill="var(--accent)" fillOpacity={0.1} stroke="var(--accent)" strokeWidth={2} connectNulls />
                  {events.map((item) => (
                    <ReferenceLine key={item.event} x={item.date} stroke="var(--neutral)" strokeDasharray="3 4" label={{ value: item.event, position: "insideTopRight", fill: "var(--text-secondary)", fontSize: 10 }} />
                  ))}
                </ComposedChart>
              </ResponsiveChart>
            </div>
            {events.length ? (
              <div className="timeline-events">
                {events.map((item) => (
                  <div className="timeline-event" key={item.event}>
                    <span className="timeline-event-dot" />
                    <span className="timeline-date">{item.date}</span>
                    <strong>{item.event}</strong>
                    <span className="timeline-impact"><ArrowUpRight size={12} />Mention spike</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted timeline-empty">No campaign events recorded. Events appear here when a collection run detects a mention spike.</p>
            )}
          </>
        ) : <EmptyState title="No timeline data yet" />}
      </div>

      <section className="opportunity-section">
        <div className="section-title">
          <div><div className="eyebrow">THE NEXT MOVE</div><h2>Opportunities worth acting on</h2></div>
          <span className="ai-identified">
            <Lightbulb size={14} />{" "}
            {opportunitySource === "llm"
              ? "AI identified"
              : opportunitySource === "pending"
                ? "Derived now; the AI version is generating"
                : "Derived from stored data"}
          </span>
        </div>
        <div className="opportunity-grid">
          {opportunities.map((item, index) => (
            <article className="panel opportunity-card" key={item.title}>
              <div className="opportunity-top">
                <span className="opportunity-icon" style={{ color: item.color }}><Lightbulb size={16} /></span>
                <span>{item.type}</span>
                <span className="opportunity-index">0{index + 1}</span>
              </div>
              <h3>{item.title}</h3>
              <p>{item.detail}</p>
              <div className="opportunity-bottom">
                <span style={{ color: item.color }}><i style={{ background: item.color }} />{item.impact}</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
