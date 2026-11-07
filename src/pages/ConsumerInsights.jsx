import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { ArrowRight, ChevronRight, Users } from "lucide-react";
import { getConsumerSegments } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { segments as segmentMock } from "../mocks/marketData.js";
import { ChartCard, EmptyState, ErrorState, PageHeading, PageLoading } from "../components/common.jsx";
import { ChartTooltip, ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";

const drivers = [{ name: "Performance & reliability", score: 82, color: "#a6e06c" }, { name: "Price & value", score: 74, color: "#f3bb6a" }, { name: "Brand trust", score: 61, color: "#a39af9" }, { name: "Product design", score: 56, color: "#73baf5" }, { name: "Reviews & ratings", score: 47, color: "#f08399" }, { name: "Ecosystem compatibility", score: 42, color: "#84cfc2" }];

export default function ConsumerInsights() {
  const { filters } = useFilters();
  const state = useFetch(() => getConsumerSegments(filters), [filters.range, filters.brand]);
  const [activeSegment, setActiveSegment] = useState("s1");
  if (state.loading) return <PageLoading />;
  if (state.error) return <ErrorState error={state.error} />;
  if (!state.data) return <EmptyState />;
  const active = state.data.find((item) => item.id === activeSegment) || state.data[0];
  return (
    <div className="page">
      <PageHeading eyebrow="AUDIENCE INTELLIGENCE" title="Meet the people behind the purchase." description="Five distinct audiences. Five different reasons to choose a brand." action={<span className="freshness-pill"><Users size={14} />84.2k consumers modeled</span>} />
      <div className="segment-card-grid">{state.data.map((segment) => <button className={`panel segment-card ${segment.id === active.id ? "active" : ""}`} key={segment.id} onClick={() => setActiveSegment(segment.id)} style={{ "--segment-color": segment.color }}><div className="segment-card-top"><span className="segment-mark"><Users size={17} /></span><span className="segment-growth">+{segment.id === "s1" ? "8.4" : segment.id === "s2" ? "4.1" : "6.2"}% <ArrowRight size={12} /></span></div><strong className="segment-title">{segment.name}</strong><div className="segment-size-row"><strong>{segment.size}</strong><span>of audience</span></div><div className="segment-card-stats"><span><small>Avg. spend</small><strong>{segment.spend}</strong></span><span><small>Audience</small><strong>{segment.users}</strong></span></div><div className="segment-progress"><i style={{ width: segment.size }} /></div></button>)}</div>
      <div className="consumer-chart-grid">
        <ChartCard title="Purchase drivers" subtitle="What most influences a buying decision (score 0-100)" data={drivers}><ResponsiveChart height={264}><BarChart data={drivers} layout="vertical" margin={{ ...chartMargin, left: 10, right: 16 }}><CartesianGrid {...gridProps} /><XAxis type="number" domain={[0, 100]} {...axisProps} /><YAxis type="category" dataKey="name" width={152} {...axisProps} /><Tooltip content={<ChartTooltip formatter={(value) => `${value}%`} />} /><Bar dataKey="score" name="Influence score" radius={[0, 5, 5, 0]} barSize={15}>{drivers.map((driver) => <Cell fill={driver.color} key={driver.name} />)}</Bar></BarChart></ResponsiveChart><div className="chart-footnote"><span>Share of consumers who cite each factor</span><span>Based on 12.4k survey responses</span></div></ChartCard>
        <ChartCard title="Audience landscape" subtitle="Price sensitivity vs. brand loyalty per consumer segment" data={state.data.map(({ name, size, users, spend, loyalty, sensitivity }) => ({ name, sizeShare: size, users, spend, loyalty, priceSensitivity: sensitivity }))} className="consumer-scatter-card"><ResponsiveChart height={264}><ScatterChart margin={{ top: 10, right: 14, bottom: 4, left: 0 }}><CartesianGrid {...gridProps} /><XAxis type="number" dataKey="sensitivity" name="Price sensitivity" domain={[0, 100]} {...axisProps} tickFormatter={(v) => `${v}`} label={{ value: "Price sensitivity →", position: "insideBottom", offset: -3, fill: "var(--text-muted)", fontSize: 10 }} /><YAxis type="number" dataKey="loyalty" name="Brand loyalty" domain={[0, 100]} {...axisProps} tickFormatter={(v) => `${v}`} /><ZAxis type="number" dataKey="sizeNum" range={[90, 460]} /><Tooltip content={({ active: show, payload }) => show && payload?.length ? <div className="chart-tooltip"><strong>{payload[0].payload.name}</strong><div className="tooltip-row">Price sensitivity <b>{payload[0].payload.sensitivity}</b></div><div className="tooltip-row">Brand loyalty <b>{payload[0].payload.loyalty}</b></div></div> : null} /><Scatter name="Consumer segments" data={state.data.map((item) => ({ ...item, sizeNum: parseInt(item.size, 10) }))}>{state.data.map((item) => <Cell key={item.id} fill={item.color} fillOpacity={0.86} />)}</Scatter></ScatterChart></ResponsiveChart><div className="scatter-axis-hints"><span>Low sensitivity</span><span>High sensitivity</span></div></ChartCard>
      </div>
      <div className="preference-panel panel"><div className="preference-heading"><div><div className="eyebrow">SEGMENT SPOTLIGHT</div><h2>{active.name}</h2><p>What matters most to this audience</p></div><span className="preference-size" style={{ color: active.color }}>{active.size}<small> of audience</small></span></div><div className="preference-details"><div className="preference-tags">{active.preferences.map((preference, index) => <span key={preference}><i style={{ background: active.color }} />{preference}<small>0{index + 1}</small></span>)}</div><div className="preference-metrics"><span><small>Avg. spend</small><strong>{active.spend}</strong></span><span><small>Brand loyalty</small><strong>{active.loyalty}<small>/100</small></strong></span><span><small>Price sensitivity</small><strong>{active.sensitivity}<small>/100</small></strong></span><button className="button button-quiet">Explore segment <ChevronRight size={14} /></button></div></div></div>
    </div>
  );
}
