import { Scatter, ScatterChart, CartesianGrid, XAxis, YAxis, ZAxis, Tooltip, Bar, BarChart, Cell } from "recharts";
import { ArrowDownRight, ArrowUpRight, ChevronRight, Minus, Plus, Swords } from "lucide-react";
import { getCompetitors, getProducts } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { ChartData } from "../context/ChatContext.jsx";
import { BRANDS, products } from "../mocks/marketData.js";
import { BrandTag, ChartCard, EmptyState, ErrorState, PageHeading, PageLoading } from "../components/common.jsx";
import { ChartTooltip, ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";

const features = ["Camera quality", "AI features", "Battery life", "Display", "Value", "Ecosystem"];
const matrix = [
  { brand: "Apple", values: [92, 82, 77, 89, 61, 96] },
  { brand: "NVIDIA", values: [null, 96, 84, 79, 63, 75] },
  { brand: "Microsoft", values: [77, 88, 91, 85, 82, 73] },
  { brand: "Samsung", values: [88, 86, 74, 95, 70, 79] },
  { brand: "Sony", values: [79, 69, 84, 82, 77, 71] },
];
const activity = [
  { date: "Feb 21", brand: "NVIDIA", title: "RTX 50-series laptop GPUs teased", detail: "New laptop range generates early performance discussion", type: "Product launch" },
  { date: "Feb 19", brand: "Samsung", title: "One UI 7 rollout expanded", detail: "AI update announcement drives positive product chatter", type: "Software update" },
  { date: "Feb 16", brand: "Apple", title: "Apple Intelligence regional expansion", detail: "New language support sparks renewed search interest", type: "Announcement" },
  { date: "Feb 12", brand: "Microsoft", title: "Surface event registration opens", detail: "Upcoming hardware event creates early anticipation", type: "Event" },
];

export default function CompetitorAnalysis() {
  const { filters } = useFilters();
  const competitorState = useFetch(() => getCompetitors(filters), [filters.brand, filters.range]);
  const productsState = useFetch(() => getProducts({ ...filters, query: "" }), [filters.brand, filters.range]);
  if (competitorState.loading || productsState.loading) return <PageLoading />;
  if (competitorState.error || productsState.error) return <ErrorState error={competitorState.error || productsState.error} />;
  if (!competitorState.data) return <EmptyState />;
  const visibleBrands = competitorState.data.brands;
  const positioning = visibleBrands.map((brand) => {
    const ownProducts = productsState.data.filter((product) => product.brand === brand.name);
    const avgPrice = ownProducts.length ? ownProducts.reduce((sum, item) => sum + item.price, 0) / ownProducts.length : 1000;
    return { name: brand.name, price: avgPrice, quality: brand.health, share: brand.share, size: brand.share * 8, color: brand.color };
  });
  const priceRows = competitorState.data.priceDifferences.filter((item) => filters.brand === "All brands" || item.brand === filters.brand);
  return (
    <div className="page">
      <ChartData title="Feature perception matrix" subtitle="Consumer-perceived performance by brand (0-100, null = n/a)" data={matrix.filter((row) => visibleBrands.some((brand) => brand.name === row.brand)).map((row) => ({ brand: row.brand, ...Object.fromEntries(features.map((feature, index) => [feature, row.values[index]])) }))} />
      <PageHeading eyebrow="COMPETITIVE INTELLIGENCE" title="See the market from every angle." description="Map positioning, compare product advantages, and stay ahead of the next move." action={<span className="freshness-pill"><Swords size={14} /> 5 brands tracked</span>} />
      <div className="competitor-primary-grid">
        <ChartCard title="Competitive positioning" subtitle="Average product price vs. perceived quality (brand health)" data={positioning.map(({ name, price, quality, share }) => ({ name, avgPrice: Math.round(price), quality, sharePct: share }))} className="positioning-card"><ResponsiveChart height={305}><ScatterChart margin={{ top: 10, right: 16, bottom: 10, left: 0 }}><CartesianGrid {...gridProps} /><XAxis type="number" dataKey="price" name="Avg. price" domain={[0, 2200]} {...axisProps} tickFormatter={(value) => `$${value}`} label={{ value: "Average product price", position: "insideBottom", offset: -3, fill: "var(--text-muted)", fontSize: 10 }} /><YAxis type="number" dataKey="quality" name="Perceived quality" domain={[60, 100]} {...axisProps} label={{ value: "Perceived quality", angle: -90, position: "insideLeft", fill: "var(--text-muted)", fontSize: 10 }} /><ZAxis type="number" dataKey="size" range={[140, 950]} name="Market share" /><Tooltip content={({ active, payload }) => active && payload?.length ? <div className="chart-tooltip"><strong>{payload[0].payload.name}</strong><div className="tooltip-row">Avg. price <b>${Math.round(payload[0].payload.price).toLocaleString()}</b></div><div className="tooltip-row">Perceived quality <b>{payload[0].payload.quality}/100</b></div><div className="tooltip-row">Market share <b>{payload[0].payload.share}%</b></div></div> : null} /><Scatter name="Brands" data={positioning}>{positioning.map((item) => <Cell key={item.name} fill={item.color} fillOpacity={0.8} stroke={item.color} strokeWidth={2} />)}</Scatter></ScatterChart></ResponsiveChart><div className="brand-legend">{visibleBrands.map((item) => <BrandTag key={item.name} brand={item.name} compact />)}</div><div className="positioning-insight"><span className="callout-icon"><ArrowUpRight size={15} /></span><span><strong>NVIDIA leads perceived quality</strong> with the highest brand health score, while Microsoft is the strongest value position.</span></div></ChartCard>
        <ChartCard title="Price difference" subtitle="Price vs. the market median ($999)" data={priceRows} className="price-difference-card"><ResponsiveChart height={286}><BarChart data={priceRows} layout="vertical" margin={{ ...chartMargin, left: 10, right: 18 }}><CartesianGrid {...gridProps} /><XAxis type="number" {...axisProps} tickFormatter={(value) => `${value > 0 ? "+" : ""}$${value}`} /><YAxis type="category" dataKey="name" width={142} {...axisProps} /><Tooltip content={<ChartTooltip formatter={(value) => `${value > 0 ? "+" : ""}$${value}`} />} /><Bar dataKey="difference" name="Difference to median" radius={[0, 4, 4, 0]} barSize={17}>{priceRows.map((item) => <Cell key={item.name} fill={item.difference > 0 ? "var(--negative)" : "var(--positive)"} />)}</Bar></BarChart></ResponsiveChart><div className="price-legend"><span><i className="positive-dot" />Below market median</span><span><i className="negative-dot" />Above market median</span></div></ChartCard>
      </div>
      <section className="panel feature-matrix"><div className="panel-heading"><div><h2>Feature comparison</h2><p>Relative customer-perceived performance by brand</p></div><span className="matrix-scale">0 = needs improvement <i /> 100 = category leader</span></div><div className="matrix-scroll"><table className="matrix-table"><thead><tr><th>BRAND</th>{features.map((feature) => <th key={feature}>{feature}</th>)}</tr></thead><tbody>{matrix.filter((row) => visibleBrands.some((brand) => brand.name === row.brand)).map((row) => <tr key={row.brand}><td><BrandTag brand={row.brand} /></td>{row.values.map((value, index) => <td key={features[index]}>{value == null ? <span className="matrix-na">n/a</span> : <span className={`matrix-score ${value >= 88 ? "strong" : value <= 66 ? "weak" : ""}`} style={{ "--score": `${value}%` }}><i style={{ width: `${value}%` }} />{value}</span>}</td>)}</tr>)}</tbody></table></div><div className="matrix-insight"><span className="advantage-icon">↑</span><span>Highlighted values reveal clear competitive advantages and gaps for each brand.</span></div></section>
      <section className="panel activity-panel"><div className="panel-heading"><div><h2>Competitor activity</h2><p>Recent launches, announcements, and market moves</p></div><span className="activity-period">LAST 14 DAYS</span></div><div className="activity-timeline">{activity.filter((item) => visibleBrands.some((brand) => brand.name === item.brand)).map((item, index) => <article className="activity-event" key={item.title}><span className="activity-rail"><i style={{ background: BRANDS.find((brand) => brand.name === item.brand)?.color }} />{index !== activity.length - 1 && <span />}</span><span className="activity-date">{item.date}</span><span className="activity-brand"><BrandTag brand={item.brand} compact /><small>{item.type}</small></span><div className="activity-copy"><strong>{item.title}</strong><p>{item.detail}</p></div><button aria-label={`Read ${item.title}`} className="icon-button"><ChevronRight size={16} /></button></article>)}</div></section>
    </div>
  );
}
