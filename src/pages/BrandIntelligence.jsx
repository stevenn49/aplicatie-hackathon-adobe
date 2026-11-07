import { useMemo, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDownRight, ArrowUpRight, ChevronDown, Plus, TrendingUp } from "lucide-react";
import { getBrandStats, getMarketOverview } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { BRANDS, brandStats } from "../mocks/marketData.js";
import { BrandTag, ChartCard, EmptyState, ErrorState, PageHeading, PageLoading } from "../components/common.jsx";
import { ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";

export default function BrandIntelligence() {
  const { filters } = useFilters();
  const [selectedBrands, setSelectedBrands] = useState(["Apple", "NVIDIA"]);
  const [focusBrand, setFocusBrand] = useState("Apple");
  const statsState = useFetch(() => getBrandStats(filters), [filters.brand, filters.range]);
  const overviewState = useFetch(() => getMarketOverview(filters), [filters.brand, filters.range]);
  const availableStats = statsState.data || [];
  const activeBrand = availableStats.find((item) => item.brand === focusBrand) || availableStats[0];
  const visibleBrands = useMemo(() => selectedBrands.filter((brand) => availableStats.some((item) => item.brand === brand)), [selectedBrands, availableStats]);
  if (statsState.loading || overviewState.loading) return <PageLoading />;
  if (statsState.error || overviewState.error) return <ErrorState error={statsState.error || overviewState.error} />;
  if (!availableStats.length) return <EmptyState />;
  const evolution = overviewState.data.evolution;
  const toggleBrand = (brand) => setSelectedBrands((current) => current.includes(brand) ? current.filter((value) => value !== brand) : [...current, brand]);

  return (
    <div className="page">
      <PageHeading eyebrow="BRAND INTELLIGENCE" title="Know where every brand stands." description="Track brand health, conversation share, and the themes shaping perception." action={<label className="select-control"><span>Focus brand</span><select value={activeBrand?.brand || ""} onChange={(event) => setFocusBrand(event.target.value)}>{availableStats.map((item) => <option key={item.brand}>{item.brand}</option>)}</select><ChevronDown size={14} /></label>} />
      <div className="brand-selector-row"><span>Compare brands</span><div className="brand-selectors">{BRANDS.map((brand) => <button key={brand.name} onClick={() => toggleBrand(brand.name)} className={`brand-selector ${selectedBrands.includes(brand.name) ? "selected" : ""}`}><span className="selector-check">{selectedBrands.includes(brand.name) ? "✓" : <Plus size={12} />}</span><BrandTag brand={brand.name} compact /></button>)}</div><span className="selector-hint">Up to 5 brands</span></div>
      {activeBrand && <div className="brand-health-banner panel"><div className="brand-health-identity"><span className="health-logo" style={{ background: `${BRANDS.find((brand) => brand.name === activeBrand.brand)?.color}1c`, color: BRANDS.find((brand) => brand.name === activeBrand.brand)?.color }}>{activeBrand.brand[0]}</span><div><BrandTag brand={activeBrand.brand} compact /><h2>{activeBrand.brand} brand health</h2><p>Customer perception across reviews, social, and search</p></div></div><div className="health-score"><div className="health-score-number">{activeBrand.health || activeBrand.sentiment}<span>/100</span></div><div className="health-gauge"><i style={{ width: `${activeBrand.health || activeBrand.sentiment}%` }} /></div><span className="health-trend"><ArrowUpRight size={14} /> +3.2 pts this month</span></div><div className="health-divider" /><div className="health-stat"><span>Share of voice</span><strong>{activeBrand.shareOfVoice}%</strong><small><ArrowUpRight size={13} /> 2.4 pts</small></div><div className="health-stat"><span>Mentions</span><strong>{activeBrand.mentions}</strong><small><ArrowUpRight size={13} /> 12.8% this month</small></div><div className="health-stat"><span>Net sentiment</span><strong>{activeBrand.sentiment}<small>/100</small></strong><small><ArrowUpRight size={13} /> 3.2 pts</small></div></div>}
      <div className="brand-chart-grid">
        <ChartCard title="Brand sentiment over time" subtitle={`Net sentiment for ${visibleBrands.length ? visibleBrands.join(" and ") : activeBrand?.brand}`} data={evolution.map((row) => Object.fromEntries(Object.entries(row).filter(([key]) => key === "month" || key === activeBrand?.brand || visibleBrands.includes(key))))} className="brand-sentiment-chart">
          <ResponsiveChart height={250}><LineChart data={evolution} margin={chartMargin}><CartesianGrid {...gridProps} /><XAxis dataKey="month" {...axisProps} /><YAxis {...axisProps} domain={[0, 100]} /><Tooltip /><Line type="monotone" dataKey={activeBrand?.brand} name={activeBrand?.brand} stroke={BRANDS.find((brand) => brand.name === activeBrand?.brand)?.color} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />{visibleBrands.filter((brand) => brand !== activeBrand?.brand).map((brand) => <Line key={brand} type="monotone" dataKey={brand} stroke={BRANDS.find((item) => item.name === brand)?.color} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />)}</LineChart></ResponsiveChart>
        </ChartCard>
        <ChartCard title="Share of voice" subtitle="Conversation share by brand (%)" data={availableStats.map(({ brand, shareOfVoice, mentions, sentiment }) => ({ brand, shareOfVoice, mentions, sentiment }))}>
          <ResponsiveChart height={250}><BarChart data={availableStats} margin={chartMargin} layout="vertical"><CartesianGrid {...gridProps} /><XAxis type="number" {...axisProps} tickFormatter={(value) => `${value}%`} /><YAxis type="category" dataKey="brand" {...axisProps} width={75} /><Tooltip formatter={(value) => `${value}%`} /><Bar dataKey="shareOfVoice" name="Share of voice" radius={[0, 5, 5, 0]} barSize={20}>{availableStats.map((item) => <Cell key={item.brand} fill={BRANDS.find((brand) => brand.name === item.brand)?.color} />)}</Bar></BarChart></ResponsiveChart>
          <div className="chart-footnote"><span><span className="live-dot" /> {activeBrand?.mentions} mentions</span><span>Across {filters.range} conversation</span></div>
        </ChartCard>
      </div>
      {activeBrand && <ChartCard title="What people are saying" subtitle={`Top conversation themes for ${activeBrand.brand}`} data={[...activeBrand.topics.map((theme, index) => ({ theme, type: "praised", momentum: 18 - index * 3 })), ...activeBrand.concerns.map((theme, index) => ({ theme, type: "needs attention", momentum: 12 - index * 2 }))]} note="momentum = % growth of the theme in conversations" className="topics-card">
        <div className="topic-columns"><div className="topic-column praised"><div className="topic-heading"><span className="topic-icon">↑</span><div><strong>Top praised</strong><small>Driving positive perception</small></div></div>{activeBrand.topics.map((topic, index) => <div className="topic-row" key={topic}><span className="topic-rank">0{index + 1}</span><strong>{topic}</strong><span className="topic-momentum positive"><ArrowUpRight size={13} />{18 - index * 3}%</span><div className="topic-bar"><i style={{ width: `${92 - index * 15}%` }} /></div></div>)}</div><div className="topic-column criticized"><div className="topic-heading"><span className="topic-icon">↓</span><div><strong>Needs attention</strong><small>Emerging friction points</small></div></div>{activeBrand.concerns.map((topic, index) => <div className="topic-row" key={topic}><span className="topic-rank">0{index + 1}</span><strong>{topic}</strong><span className="topic-momentum negative"><ArrowUpRight size={13} />{12 - index * 2}%</span><div className="topic-bar"><i style={{ width: `${71 - index * 12}%` }} /></div></div>)}</div></div>
      </ChartCard>}
      <div className="brand-insight-callout"><span className="callout-icon"><TrendingUp size={16} /></span><span><strong>{activeBrand?.brand} is gaining ground.</strong> Positive sentiment is up 3.2 points, driven by strong momentum in performance and product quality.</span><button className="button button-quiet" onClick={() => setFocusBrand("NVIDIA")}>Explore insight <ArrowUpRight size={14} /></button></div>
    </div>
  );
}
