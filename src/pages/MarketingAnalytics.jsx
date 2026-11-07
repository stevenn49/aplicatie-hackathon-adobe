import { useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, LineChart, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDownRight, ArrowUpRight, ArrowUpRight as UpRight, CalendarDays, Lightbulb, Megaphone, Radio, Target } from "lucide-react";
import { getMarketingTrends } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { ChartCard, EmptyState, ErrorState, PageHeading, PageLoading, SourceTag } from "../components/common.jsx";
import { ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";

const opportunities = [
  { title: "Turn performance buzz into proof", type: "CONTENT OPPORTUNITY", detail: "NVIDIA's strongest conversation topic is performance, but creator benchmarks are still underserved.", impact: "High potential", color: "var(--positive)" },
  { title: "Meet shoppers at the value moment", type: "AUDIENCE OPPORTUNITY", detail: "Searches for last-generation flagship comparisons are up 22% among value-conscious shoppers.", impact: "Growing demand", color: "var(--accent)" },
  { title: "Clarify the next-gen AI story", type: "NARRATIVE OPPORTUNITY", detail: "AI feature mentions are growing quickly, but conversations reveal a gap between promise and everyday utility.", impact: "Emerging signal", color: "var(--neutral)" },
];

const sourceMentions = [{ source: "Reddit", mentions: 18600, tone: "var(--accent)" }, { source: "X", mentions: 14200, tone: "#8b8cf7" }, { source: "eMAG", mentions: 7800, tone: "var(--positive)" }, { source: "Google", mentions: 5100, tone: "var(--neutral)" }];

export default function MarketingAnalytics() {
  const { filters } = useFilters();
  const state = useFetch(() => getMarketingTrends(filters), [filters.range, filters.brand]);
  const [activeMetric, setActiveMetric] = useState("Brand interest");
  if (state.loading) return <PageLoading />;
  if (state.error) return <ErrorState error={state.error} />;
  if (!state.data) return <EmptyState />;
  const trendData = state.data.map((item) => ({ ...item, [filters.brand === "All brands" ? "Apple" : filters.brand]: item[filters.brand === "All brands" ? "Apple" : filters.brand] }));
  const brand = filters.brand === "All brands" ? "Apple" : filters.brand;
  const colors = { Apple: "#8b8cf7", NVIDIA: "#9bd94e", Microsoft: "#59a9f5", Samsung: "#f0a35e", Sony: "#e8788c" };
  return (
    <div className="page">
      <PageHeading eyebrow="CAMPAIGN & DEMAND SIGNALS" title="Marketing analytics" description="Spot growing demand, measure campaign lift, find your next story." action={<span className="freshness-pill"><span className="live-dot" /> Trends refreshed 4h ago</span>} />
      <div className="marketing-kpi-row"><div className="marketing-kpi panel"><span className="kpi-icon"><Radio size={16} /></span><span className="marketing-kpi-label">Search interest</span><strong>78.4 <small>/ 100</small></strong><span className="delta positive"><ArrowUpRight size={13} />+12.6% vs prior period</span></div><div className="marketing-kpi panel"><span className="kpi-icon"><Megaphone size={16} /></span><span className="marketing-kpi-label">Social mentions</span><strong>42.8k</strong><span className="delta positive"><ArrowUpRight size={13} />+18.2% vs prior period</span></div><div className="marketing-kpi panel"><span className="kpi-icon"><Target size={16} /></span><span className="marketing-kpi-label">Campaign sentiment</span><strong>86<small>/ 100</small></strong><span className="delta positive"><ArrowUpRight size={13} />+4.3 pts this month</span></div><div className="marketing-kpi panel"><span className="kpi-icon"><CalendarDays size={16} /></span><span className="marketing-kpi-label">Share of voice</span><strong>28.4<small>%</small></strong><span className="delta neutral"><ArrowUpRight size={13} />+2.1 pts vs prior period</span></div></div>
      <div className="marketing-chart-grid">
        <ChartCard title="Market interest over time" subtitle={`Normalized search and social interest · metric: ${activeMetric}`} data={trendData} className="marketing-interest-chart" action={<div className="metric-switch">{["Brand interest", "Product interest"].map((item) => <button key={item} className={activeMetric === item ? "active" : ""} onClick={() => setActiveMetric(item)}>{item}</button>)}</div>}>
          <div className="campaign-legend"><span><i style={{ background: colors[brand] }} />{brand} interest</span><span><i className="legend-dashed" />Social mentions</span></div>
          <ResponsiveChart height={280}><ComposedChart data={trendData} margin={chartMargin}><CartesianGrid {...gridProps} /><XAxis dataKey="date" {...axisProps} /><YAxis {...axisProps} domain={[0, 100]} /><Tooltip /><Area type="monotone" dataKey={brand} name={`${brand} interest`} stroke={colors[brand]} fill={colors[brand]} fillOpacity={0.10} strokeWidth={2.2} /><Line type="monotone" dataKey="Reddit" name="Reddit mentions" stroke="var(--text-muted)" strokeDasharray="5 5" strokeWidth={1.7} dot={false} /><Line type="monotone" dataKey="X" name="X mentions" stroke="var(--accent)" strokeDasharray="2 4" strokeWidth={1.7} dot={false} /></ComposedChart></ResponsiveChart>
        </ChartCard>
        <ChartCard title="Where the conversation lives" subtitle="Mention volume by source" data={sourceMentions}>
          <ResponsiveChart height={244}><BarChart data={sourceMentions} margin={chartMargin}><CartesianGrid {...gridProps} /><XAxis dataKey="source" {...axisProps} /><YAxis {...axisProps} tickFormatter={(value) => `${value / 1000}k`} /><Tooltip formatter={(value) => `${(value / 1000).toFixed(1)}k mentions`} /><Bar dataKey="mentions" name="Mentions" radius={[5, 5, 0, 0]} barSize={30}>{[0, 1, 2, 3].map((index) => <Cell fill={["var(--accent)", "#8b8cf7", "var(--positive)", "var(--neutral)"][index]} key={index} />)}</Bar></BarChart></ResponsiveChart>
          <div className="source-summary"><span><i className="source-indicator reddit" />Reddit leads conversation share</span><strong>43.5%</strong></div>
        </ChartCard>
      </div>
      <div className="campaign-timeline panel"><div className="panel-heading"><div><h2>Campaign reaction timeline</h2><p>Events that moved the conversation</p></div><span className="timeline-range">Last 90 days <CalendarDays size={13} /></span></div><div className="timeline-chart-wrap"><ResponsiveChart height={175}><ComposedChart data={trendData} margin={{ ...chartMargin, top: 15 }}><CartesianGrid {...gridProps} /><XAxis dataKey="date" {...axisProps} /><YAxis {...axisProps} hide /><Tooltip /><Area type="monotone" dataKey={brand} name="Search interest" fill="var(--accent)" fillOpacity={0.1} stroke="var(--accent)" strokeWidth={2} />{trendData.map((item, index) => item.event && <ReferenceLine key={item.event} x={item.date} stroke="var(--neutral)" strokeDasharray="3 4" label={{ value: item.event, position: "insideTopRight", fill: "var(--text-secondary)", fontSize: 10 }} />)}</ComposedChart></ResponsiveChart></div><div className="timeline-events">{trendData.filter((item) => item.event).map((item) => <div className="timeline-event" key={item.event}><span className="timeline-event-dot" /><span className="timeline-date">{item.date}</span><strong>{item.event}</strong><span className="timeline-impact"><ArrowUpRight size={12} />Interest +{item.event.includes("RTX") ? "32" : "18"}%</span></div>)}</div></div>
      <section className="opportunity-section"><div className="section-title"><div><div className="eyebrow">THE NEXT MOVE</div><h2>Opportunities worth acting on</h2></div><span className="ai-identified"><Lightbulb size={14} /> AI identified</span></div><div className="opportunity-grid">{opportunities.map((item, index) => <article className="panel opportunity-card" key={item.title}><div className="opportunity-top"><span className="opportunity-icon" style={{ color: item.color }}><Lightbulb size={16} /></span><span>{item.type}</span><span className="opportunity-index">0{index + 1}</span></div><h3>{item.title}</h3><p>{item.detail}</p><div className="opportunity-bottom"><span style={{ color: item.color }}><i style={{ background: item.color }} />{item.impact}</span><button aria-label={`View ${item.title}`}><UpRight size={15} /></button></div></article>)}</div></section>
    </div>
  );
}
