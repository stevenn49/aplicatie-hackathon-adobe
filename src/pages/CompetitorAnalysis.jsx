import { Scatter, ScatterChart, CartesianGrid, XAxis, YAxis, ZAxis, Tooltip, Bar, BarChart, Cell } from "recharts";
import { ArrowUpRight, ChevronRight, Swords } from "lucide-react";
import { getCompetitors, getProducts } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { BrandTag, ChartCard, EmptyState, ErrorState, PageHeading, PageLoading } from "../components/common.jsx";
import { ChartTooltip, ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";
import { formatMoney } from "../constants/brands.js";

export default function CompetitorAnalysis() {
  const { filters } = useFilters();
  const competitorState = useFetch(() => getCompetitors(filters), [filters.brand]);
  const productsState = useFetch(() => getProducts({ ...filters, query: "" }), [filters.brand]);

  if (competitorState.loading || productsState.loading) return <PageLoading />;
  if (competitorState.error || productsState.error) return <ErrorState error={competitorState.error || productsState.error} />;
  if (!competitorState.data) return <EmptyState />;

  const data = competitorState.data;
  const products = productsState.data || [];
  const visibleBrands = data.brands;

  const positioning = visibleBrands.map((brand) => {
    const ownProducts = products.filter((product) => product.brand === brand.name);
    const avgPrice = ownProducts.length ? ownProducts.reduce((sum, item) => sum + item.price, 0) / ownProducts.length : null;
    return {
      name: brand.name,
      price: avgPrice,
      quality: brand.health,
      share: brand.share,
      size: Math.max(120, brand.share * 8),
      color: brand.color,
    };
  }).filter((item) => item.price !== null && item.quality !== null);

  const priceRows = data.priceDifferences.filter((item) => filters.brand === "All brands" || item.brand === filters.brand);
  const leader = [...visibleBrands].filter((brand) => brand.health !== null).sort((a, b) => b.health - a.health)[0];
  const bestValue = [...positioning].sort((a, b) => a.price - b.price)[0];

  return (
    <div className="page">
      <PageHeading
        eyebrow="COMPETITIVE INTELLIGENCE"
        title="See the market from every angle."
        description="Map positioning, compare product advantages, and stay ahead of the next move."
        action={<span className="freshness-pill"><Swords size={14} /> {visibleBrands.length} brands tracked</span>}
      />

      <div className="competitor-primary-grid">
        <ChartCard title="Competitive positioning" subtitle="Average product price vs. perceived quality" data={positioning} className="positioning-card">
          {positioning.length ? (
            <>
              <ResponsiveChart height={305}>
                <ScatterChart margin={{ top: 10, right: 16, bottom: 10, left: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis type="number" dataKey="price" name="Avg. price" {...axisProps} tickFormatter={(value) => `${Math.round(value)}`} label={{ value: "Average product price (lei)", position: "insideBottom", offset: -3, fill: "var(--text-muted)", fontSize: 10 }} />
                  <YAxis type="number" dataKey="quality" name="Perceived quality" domain={[0, 100]} {...axisProps} label={{ value: "Perceived quality", angle: -90, position: "insideLeft", fill: "var(--text-muted)", fontSize: 10 }} />
                  <ZAxis type="number" dataKey="size" range={[140, 950]} name="Market share" />
                  <Tooltip content={({ active, payload }) => (active && payload?.length ? (
                    <div className="chart-tooltip">
                      <strong>{payload[0].payload.name}</strong>
                      <div className="tooltip-row">Avg. price <b>{formatMoney(payload[0].payload.price)}</b></div>
                      <div className="tooltip-row">Perceived quality <b>{payload[0].payload.quality.toFixed(0)}/100</b></div>
                      <div className="tooltip-row">Market share <b>{payload[0].payload.share}%</b></div>
                    </div>
                  ) : null)} />
                  <Scatter name="Brands" data={positioning}>
                    {positioning.map((item) => <Cell key={item.name} fill={item.color} fillOpacity={0.8} stroke={item.color} strokeWidth={2} />)}
                  </Scatter>
                </ScatterChart>
              </ResponsiveChart>
              <div className="brand-legend">{visibleBrands.map((item) => <BrandTag key={item.name} brand={item.name} color={item.color} compact />)}</div>
              {leader && (
                <div className="positioning-insight">
                  <span className="callout-icon"><ArrowUpRight size={15} /></span>
                  <span>
                    <strong>{leader.name} leads perceived quality</strong> at {leader.health.toFixed(0)}/100
                    {bestValue ? `, while ${bestValue.name} has the lowest average price at ${formatMoney(bestValue.price)}.` : "."}
                  </span>
                </div>
              )}
            </>
          ) : <EmptyState title="Not enough data for positioning" description="Each brand needs at least one product with reviews." />}
        </ChartCard>

        <ChartCard title="Price difference" subtitle="Price vs. the category median" data={priceRows} className="price-difference-card">
          {priceRows.length ? (
            <>
              <ResponsiveChart height={286}>
                <BarChart data={priceRows} layout="vertical" margin={{ ...chartMargin, left: 10, right: 18 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis type="number" {...axisProps} tickFormatter={(value) => `${value > 0 ? "+" : ""}${Math.round(value)}`} />
                  <YAxis type="category" dataKey="name" width={142} {...axisProps} />
                  <Tooltip content={<ChartTooltip formatter={(value) => formatMoney(value)} />} />
                  <Bar dataKey="difference" name="Difference to median" radius={[0, 4, 4, 0]} barSize={17}>
                    {priceRows.map((item) => <Cell key={item.name} fill={item.difference > 0 ? "var(--negative)" : "var(--positive)"} />)}
                  </Bar>
                </BarChart>
              </ResponsiveChart>
              <div className="price-legend">
                <span><i className="positive-dot" />Below category median</span>
                <span><i className="negative-dot" />Above category median</span>
              </div>
            </>
          ) : <EmptyState title="No price data" />}
        </ChartCard>
      </div>

      <section className="panel feature-matrix">
        <div className="panel-heading">
          <div><h2>Feature comparison</h2><p>Customer-perceived performance by brand, from aspect sentiment</p></div>
          <span className="matrix-scale">0 = needs improvement <i /> 100 = category leader</span>
        </div>
        {data.matrix.length ? (
          <div className="matrix-scroll">
            <table className="matrix-table">
              <thead>
                <tr>
                  <th>BRAND</th>
                  {data.features.map((feature) => <th key={feature}>{feature}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.matrix.filter((row) => visibleBrands.some((brand) => brand.name === row.brand)).map((row) => (
                  <tr key={row.brand}>
                    <td><BrandTag brand={row.brand} color={visibleBrands.find((b) => b.name === row.brand)?.color} /></td>
                    {row.values.map((value, index) => (
                      <td key={data.features[index]}>
                        {value === null || value === undefined
                          ? <span className="matrix-na">n/a</span>
                          : <span className={`matrix-score ${value >= 88 ? "strong" : value <= 66 ? "weak" : ""}`} style={{ "--score": `${value}%` }}><i style={{ width: `${value}%` }} />{value.toFixed(0)}</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState title="No aspect data yet" />}
        <div className="matrix-insight">
          <span className="advantage-icon">↑</span>
          <span>Highlighted values reveal clear competitive advantages and gaps for each brand.</span>
        </div>
      </section>

      <section className="panel activity-panel">
        <div className="panel-heading">
          <div><h2>Competitor activity</h2><p>Recent market signals from stored reviews</p></div>
          <span className="activity-period">LATEST MENTIONS</span>
        </div>
        {data.activity.length ? (
          <div className="activity-timeline">
            {data.activity.filter((item) => visibleBrands.some((brand) => brand.name === item.brand)).map((item, index, list) => (
              <article className="activity-event" key={`${item.brand}-${item.date}-${index}`}>
                <span className="activity-rail">
                  <i style={{ background: visibleBrands.find((brand) => brand.name === item.brand)?.color }} />
                  {index !== list.length - 1 && <span />}
                </span>
                <span className="activity-date">{item.date}</span>
                <span className="activity-brand"><BrandTag brand={item.brand} color={visibleBrands.find((b) => b.name === item.brand)?.color} compact /><small>{item.type}</small></span>
                <div className="activity-copy"><strong>{item.title}</strong><p>{item.detail}</p></div>
                <button aria-label={`Read ${item.title}`} className="icon-button"><ChevronRight size={16} /></button>
              </article>
            ))}
          </div>
        ) : <EmptyState title="No recent activity" />}
      </section>
    </div>
  );
}
