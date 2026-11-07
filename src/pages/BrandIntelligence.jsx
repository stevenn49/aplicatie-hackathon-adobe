import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDownRight, ArrowUpRight, ChevronDown, Plus, TrendingUp } from "lucide-react";
import { getBrandStats, getMarketOverview } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { BrandTag, ChartCard, EmptyState, ErrorState, PageHeading, PageLoading } from "../components/common.jsx";
import { ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";

export default function BrandIntelligence() {
  const { filters } = useFilters();
  const [selectedBrands, setSelectedBrands] = useState([]);
  const [focusBrand, setFocusBrand] = useState(null);

  const statsState = useFetch(() => getBrandStats(filters), [filters.brand]);
  const overviewState = useFetch(() => getMarketOverview(filters), [filters.brand]);

  const availableStats = statsState.data || [];
  const activeBrand = availableStats.find((item) => item.brand === focusBrand) || availableStats[0];
  const visibleBrands = useMemo(
    () => selectedBrands.filter((brand) => availableStats.some((item) => item.brand === brand)),
    [selectedBrands, availableStats],
  );
  const evolution = overviewState.data?.evolution || [];
  // Only the series actually drawn: the assistant must not reason about a brand
  // the chart does not show. Declared before the early returns so the hook order
  // is stable across loading and loaded renders.
  const evolutionSeries = useMemo(() => {
    const keys = [activeBrand?.brand, ...visibleBrands.filter((brand) => brand !== activeBrand?.brand)].filter(Boolean);
    return evolution.map((row) => ({ month: row.month, ...Object.fromEntries(keys.map((key) => [key, row[key]])) }));
  }, [evolution, activeBrand?.brand, visibleBrands]);

  if (statsState.loading || overviewState.loading) return <PageLoading />;
  if (statsState.error || overviewState.error) return <ErrorState error={statsState.error || overviewState.error} />;
  if (!availableStats.length) return <EmptyState title="No brand data yet" description="Collect reviews for at least one product." />;

  const colorFor = (brand) => availableStats.find((item) => item.brand === brand)?.color || "var(--text-muted)";
  const toggleBrand = (brand) =>
    setSelectedBrands((current) => (current.includes(brand) ? current.filter((value) => value !== brand) : [...current, brand]));

  const leader = [...availableStats]
    .filter((item) => item.sentiment !== null)
    .sort((a, b) => b.sentiment - a.sentiment)[0];

  return (
    <div className="page">
      <PageHeading
        eyebrow="BRAND INTELLIGENCE"
        title="Know where every brand stands."
        description="Track brand health, conversation share, and the themes shaping perception."
        action={
          <label className="select-control">
            <span>Focus brand</span>
            <select value={activeBrand?.brand || ""} onChange={(event) => setFocusBrand(event.target.value)}>
              {availableStats.map((item) => <option key={item.brand}>{item.brand}</option>)}
            </select>
            <ChevronDown size={14} />
          </label>
        }
      />

      <div className="brand-selector-row">
        <span>Compare brands</span>
        <div className="brand-selectors">
          {availableStats.map((brand) => (
            <button
              key={brand.brand}
              onClick={() => toggleBrand(brand.brand)}
              className={`brand-selector ${selectedBrands.includes(brand.brand) ? "selected" : ""}`}
            >
              <span className="selector-check">{selectedBrands.includes(brand.brand) ? "✓" : <Plus size={12} />}</span>
              <BrandTag brand={brand.brand} color={brand.color} compact />
            </button>
          ))}
        </div>
        <span className="selector-hint">Up to {availableStats.length} brands</span>
      </div>

      {activeBrand && (
        <div className="brand-health-banner panel">
          <div className="brand-health-identity">
            <span className="health-logo" style={{ background: `${activeBrand.color}1c`, color: activeBrand.color }}>{activeBrand.brand[0]}</span>
            <div>
              <BrandTag brand={activeBrand.brand} color={activeBrand.color} compact />
              <h2>{activeBrand.brand} brand health</h2>
              <p>Customer perception across stored reviews</p>
            </div>
          </div>
          <div className="health-score">
            <div className="health-score-number">{activeBrand.health === null ? "—" : activeBrand.health.toFixed(0)}<span>/100</span></div>
            <div className="health-gauge"><i style={{ width: `${activeBrand.health ?? 0}%` }} /></div>
            <span className="health-trend muted">60% sentiment + 40% rating</span>
          </div>
          <div className="health-divider" />
          <div className="health-stat"><span>Share of voice</span><strong>{activeBrand.shareOfVoice}%</strong><small className="muted">of all mentions</small></div>
          <div className="health-stat"><span>Mentions</span><strong>{activeBrand.mentions}</strong><small className="muted">stored reviews</small></div>
          <div className="health-stat">
            <span>Net sentiment</span>
            <strong>{activeBrand.sentiment === null ? "—" : activeBrand.sentiment.toFixed(0)}<small>/100</small></strong>
            <small className="muted">across its reviews</small>
          </div>
        </div>
      )}

      <div className="brand-chart-grid">
        <ChartCard
          title="Conversation volume over time"
          subtitle={visibleBrands.length ? `Indexed mentions for ${visibleBrands.join(" and ")}` : `Indexed mentions for ${activeBrand?.brand}`}
          data={evolutionSeries}
          className="brand-sentiment-chart"
        >
          {evolution.length ? (
            <ResponsiveChart height={250}>
              <LineChart data={evolution} margin={chartMargin}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="month" {...axisProps} />
                <YAxis {...axisProps} domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey={activeBrand?.brand} name={activeBrand?.brand} stroke={colorFor(activeBrand?.brand)} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} connectNulls />
                {visibleBrands.filter((brand) => brand !== activeBrand?.brand).map((brand) => (
                  <Line key={brand} type="monotone" dataKey={brand} stroke={colorFor(brand)} strokeWidth={2} dot={false} activeDot={{ r: 4 }} connectNulls />
                ))}
              </LineChart>
            </ResponsiveChart>
          ) : <EmptyState title="No mention history yet" />}
        </ChartCard>

        <ChartCard title="Share of voice" subtitle="Conversation share by brand" data={availableStats.map(({ brand, shareOfVoice }) => ({ brand, shareOfVoice }))}>
          <ResponsiveChart height={250}>
            <BarChart data={availableStats} margin={chartMargin} layout="vertical">
              <CartesianGrid {...gridProps} />
              <XAxis type="number" {...axisProps} tickFormatter={(value) => `${value}%`} />
              <YAxis type="category" dataKey="brand" {...axisProps} width={75} />
              <Tooltip formatter={(value) => `${value}%`} />
              <Bar dataKey="shareOfVoice" name="Share of voice" radius={[0, 5, 5, 0]} barSize={20}>
                {availableStats.map((item) => <Cell key={item.brand} fill={item.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveChart>
          <div className="chart-footnote">
            <span><span className="live-dot" /> {activeBrand?.mentions} mentions</span>
            <span>Across {availableStats.reduce((sum, item) => sum + item.mentions, 0)} stored reviews</span>
          </div>
        </ChartCard>
      </div>

      {activeBrand && (activeBrand.topics.length > 0 || activeBrand.concerns.length > 0) && (
        <ChartCard
          title="What people are saying"
          subtitle={`Top conversation themes for ${activeBrand.brand}`}
          data={[{ brand: activeBrand.brand, praised: activeBrand.topics.join("; "), needsAttention: activeBrand.concerns.join("; ") }]}
          className="topics-card"
        >
          <div className="topic-columns">
            <div className="topic-column praised">
              <div className="topic-heading">
                <span className="topic-icon">↑</span>
                <div><strong>Top praised</strong><small>Driving positive perception</small></div>
              </div>
              {activeBrand.topics.length
                ? activeBrand.topics.map((topic, index) => (
                  <div className="topic-row" key={topic}>
                    <span className="topic-rank">0{index + 1}</span>
                    <strong>{topic}</strong>
                    <span className="topic-momentum positive"><ArrowUpRight size={13} />praised</span>
                    <div className="topic-bar"><i style={{ width: `${92 - index * 15}%` }} /></div>
                  </div>
                ))
                : <p className="muted">No consistently praised aspect detected.</p>}
            </div>
            <div className="topic-column criticized">
              <div className="topic-heading">
                <span className="topic-icon">↓</span>
                <div><strong>Needs attention</strong><small>Emerging friction points</small></div>
              </div>
              {activeBrand.concerns.length
                ? activeBrand.concerns.map((topic, index) => (
                  <div className="topic-row" key={topic}>
                    <span className="topic-rank">0{index + 1}</span>
                    <strong>{topic}</strong>
                    <span className="topic-momentum negative"><ArrowDownRight size={13} />criticised</span>
                    <div className="topic-bar"><i style={{ width: `${71 - index * 12}%` }} /></div>
                  </div>
                ))
                : <p className="muted">No consistently criticised aspect detected.</p>}
            </div>
          </div>
        </ChartCard>
      )}

      {leader && (
        <div className="brand-insight-callout">
          <span className="callout-icon"><TrendingUp size={16} /></span>
          <span>
            <strong>{leader.brand} leads on sentiment.</strong> {leader.sentiment.toFixed(0)}/100 across {leader.mentions} mentions
            {leader.topics.length ? `, driven by ${leader.topics[0].toLowerCase()}` : ""}.
          </span>
          {leader.brand !== activeBrand?.brand && (
            <button className="button button-quiet" onClick={() => setFocusBrand(leader.brand)}>
              Explore insight <ArrowUpRight size={14} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
