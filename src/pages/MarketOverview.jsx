import { useMemo } from "react";
import { Area, AreaChart, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { ArrowDownRight, ArrowUpRight, ExternalLink, MessageSquare, Radio, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { getMarketOverview, getProducts } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { ChartData } from "../context/ChatContext.jsx";
import { BRANDS } from "../mocks/marketData.js";
import { BrandTag, ChartCard, EmptyState, ErrorState, KpiCard, PageHeading, PageLoading, SentimentBadge, SourceTag } from "../components/common.jsx";
import { ChartAxes, ChartTooltip, ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";

export default function MarketOverview() {
  const { filters } = useFilters();
  const overviewState = useFetch(() => getMarketOverview(filters), [filters]);
  const productsState = useFetch(() => getProducts({ ...filters, query: "" }), [filters.brand, filters.range]);
  const data = overviewState.data;
  const topMover = useMemo(() => data?.topMovers?.[0], [data]);
  if (overviewState.loading || productsState.loading) return <PageLoading />;
  if (overviewState.error || productsState.error) return <ErrorState error={overviewState.error || productsState.error} />;
  if (!data) return <EmptyState />;

  const share = (filters.brand === "All brands" ? BRANDS : BRANDS.filter((brand) => brand.name === filters.brand)).map((item) => ({ name: item.name, value: item.share, color: item.color }));
  return (
    <div className="page">
      <PageHeading eyebrow="MONDAY, FEBRUARY 24, 2025" title="Market overview" description="A clear view of what's moving across the tech landscape." action={<span className="freshness-pill"><span className="live-dot" /> Live market pulse</span>} />
      <ChartData title="KPI summary" subtitle="Headline KPIs at the top of the overview" data={data.kpis} />
      <div className="kpi-grid">
        {data.kpis.map((kpi) => <KpiCard key={kpi.label} {...kpi} />)}
        <article className="kpi-card trending-kpi"><div className="kpi-top"><span>Trending brand</span><span className="kpi-icon"><TrendingUp size={16} /></span></div><div className="trending-brand"><span className="trend-mark" style={{ color: "#9bd94e" }}>N</span><div><strong>NVIDIA</strong><small>GeForce RTX 5090</small></div></div><div className="kpi-bottom"><span className="delta positive"><ArrowUpRight size={14} />+34.2%</span><span className="kpi-note">interest this week</span></div><div className="trend-spark"><span /></div></article>
      </div>
      <div className="overview-primary">
        <ChartCard title="Market interest over time" subtitle="Search and social activity, indexed to 100" data={data.evolution} action={<div className="chart-period-label"><span className="live-dot" /> Updating live</div>} className="evolution-card">
          <ResponsiveChart height={286}><LineChart data={data.evolution} margin={chartMargin}><ChartAxes xKey="month" /><Line type="monotone" dataKey="Apple" stroke="#8b8cf7" strokeWidth={2.2} dot={false} activeDot={{ r: 4 }} /><Line type="monotone" dataKey="NVIDIA" stroke="#9bd94e" strokeWidth={2.2} dot={false} activeDot={{ r: 4 }} /><Line type="monotone" dataKey="Microsoft" stroke="#59a9f5" strokeWidth={2} dot={false} activeDot={{ r: 4 }} /><Line type="monotone" dataKey="Samsung" stroke="#f0a35e" strokeWidth={2} dot={false} activeDot={{ r: 4 }} /><Line type="monotone" dataKey="Sony" stroke="#e8788c" strokeWidth={2} dot={false} activeDot={{ r: 4 }} /></LineChart></ResponsiveChart>
          <div className="brand-legend">{BRANDS.map((brand) => <BrandTag key={brand.name} brand={brand.name} compact />)}</div>
        </ChartCard>
        <ChartCard title="Share of voice" subtitle="Brand conversation volume (%)" data={share}>
          <div className="share-chart-wrap"><ResponsiveContainer width="100%" height={194}><PieChart><Pie data={share} dataKey="value" nameKey="name" innerRadius={62} outerRadius={83} paddingAngle={4} stroke="none">{share.map((item) => <Cell key={item.name} fill={item.color} />)}</Pie><Tooltip content={<ChartTooltip formatter={(value) => `${value}%`} />} /></PieChart></ResponsiveContainer><div className="donut-center"><strong>{filters.brand === "All brands" ? "100%" : `${share[0]?.value || 0}%`}</strong><span>voice share</span></div></div>
          <div className="share-list">{share.map((item) => <div className="share-row" key={item.name}><span className="share-name"><i style={{ background: item.color }} />{item.name}</span><strong>{item.value}%</strong><div className="share-track"><i style={{ width: `${item.value * 2.4}%`, background: item.color }} /></div></div>)}</div>
        </ChartCard>
      </div>
      <div className="overview-secondary">
        <ChartCard title="Top movers" subtitle="Biggest week-over-week interest shifts (%)" data={data.topMovers?.map(({ name, brand, category, change, price, sentiment }) => ({ name, brand, category, change, price, sentiment }))} action={<Link className="text-link" to="/products">All products <ExternalLink size={13} /></Link>} className="movers-card">
          <div className="mover-list">{data.topMovers?.map((product, index) => <div className="mover-row" key={product.id}><span className="mover-rank">0{index + 1}</span><span className="product-initial" style={{ color: product.color, background: `${product.color}18` }}>{product.brand.slice(0, 1)}</span><div className="mover-product"><strong>{product.name}</strong><small>{product.brand} <span>·</span> {product.category}</small></div><div className={`mover-delta ${product.change < 0 ? "negative" : "positive"}`}>{product.change < 0 ? <ArrowDownRight size={15} /> : <ArrowUpRight size={15} />}{Math.abs(product.change)}%</div></div>)}</div>
          {topMover && <div className="mover-callout"><span className="callout-icon"><TrendingUp size={15} /></span><span><strong>{topMover.name}</strong> is the fastest-rising product this week.</span></div>}
        </ChartCard>
        <ChartCard title="Notable mentions" subtitle="High-signal conversations across your sources" data={data.mentions.map(({ brand, text, sentiment, source, engagement, time }) => ({ brand, text, sentiment, source, engagement, time }))} action={<span className="live-status"><span className="live-dot" /> LIVE</span>} className="mentions-card">
          <div className="mention-list">{data.mentions.map((mention) => <article className="mention-row" key={mention.id}><span className={`mention-avatar mention-${mention.brand.toLowerCase()}`}>{mention.initials}</span><div className="mention-main"><div className="mention-meta"><BrandTag brand={mention.brand} compact /><span className="mention-time">{mention.time}</span></div><p>{mention.text}</p><div className="mention-footer"><SentimentBadge sentiment={mention.sentiment} /> <SourceTag source={mention.source} /><span className="mention-engagement"><MessageSquare size={12} />{mention.engagement}</span></div></div></article>)}</div>
        </ChartCard>
      </div>
      <div className="overview-footer-strip"><span><Radio size={14} /> Monitoring <strong>{productsState.data.length} products</strong> across 5 leading tech brands</span><Link to="/recommendations">See what to do next <ArrowUpRight size={14} /></Link></div>
    </div>
  );
}
