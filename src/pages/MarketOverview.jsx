import { useMemo } from "react";
import { Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { ArrowDownRight, ArrowUpRight, ExternalLink, MessageSquare, Radio, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { getBrandStats, getMarketOverview, getProducts } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { ChartData } from "../context/ChatContext.jsx";
import { BrandTag, ChartCard, EmptyState, ErrorState, KpiCard, PageHeading, PageLoading, SentimentBadge, SourceTag } from "../components/common.jsx";
import { ChartTooltip, ResponsiveChart, chartAxes, chartMargin } from "../components/charts.jsx";
import { formatMoney } from "../constants/brands.js";

const today = new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
  .format(new Date())
  .toUpperCase();

export default function MarketOverview() {
  const { filters } = useFilters();
  const overviewState = useFetch(() => getMarketOverview(filters), [filters.brand]);
  const productsState = useFetch(() => getProducts({ ...filters, query: "" }), [filters.brand]);
  const brandsState = useFetch(() => getBrandStats(filters), [filters.brand]);

  const data = overviewState.data;
  const topMover = useMemo(() => data?.topMovers?.[0], [data]);

  if (overviewState.loading || productsState.loading || brandsState.loading) return <PageLoading />;
  if (overviewState.error || productsState.error || brandsState.error) {
    return <ErrorState error={overviewState.error || productsState.error || brandsState.error} />;
  }
  if (!data) return <EmptyState />;

  const brandStats = brandsState.data || [];
  const share = brandStats.map((item) => ({ name: item.brand, value: item.shareOfVoice, color: item.color }));
  const totalShare = share.reduce((sum, item) => sum + item.value, 0);
  const evolutionKeys = data.evolution.length
    ? Object.keys(data.evolution[0]).filter((key) => key !== "month")
    : [];
  const colorFor = (brand) => brandStats.find((item) => item.brand === brand)?.color || "var(--text-muted)";

  return (
    <div className="page">
      <PageHeading
        eyebrow={today}
        title="Market overview"
        description="A clear view of what's moving across the tech landscape."
        action={<span className="freshness-pill"><span className="live-dot" /> Live market pulse</span>}
      />
      <ChartData title="KPI summary" subtitle="Headline KPIs at the top of the overview" data={data.kpis} />

      <div className="kpi-grid">
        {data.kpis.map((kpi) => <KpiCard key={kpi.label} {...kpi} />)}
        {topMover && (
          <article className="kpi-card trending-kpi">
            <div className="kpi-top"><span>Biggest price move</span><span className="kpi-icon"><TrendingUp size={16} /></span></div>
            <div className="trending-brand">
              <span className="trend-mark" style={{ color: topMover.color }}>{topMover.brand.slice(0, 1)}</span>
              <div><strong>{topMover.brand}</strong><small>{topMover.name}</small></div>
            </div>
            <div className="kpi-bottom">
              <span className={`delta ${topMover.change >= 0 ? "positive" : "negative"}`}>
                {topMover.change >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                {Math.abs(topMover.change).toFixed(1)}%
              </span>
              <span className="kpi-note">since the first recorded price</span>
            </div>
            <div className="trend-spark"><span /></div>
          </article>
        )}
      </div>

      <div className="overview-primary">
        <ChartCard
          title="Conversation volume over time"
          subtitle="Weekly review mentions per brand, indexed to 100"
          data={data.evolution}
          action={<div className="chart-period-label"><span className="live-dot" /> From stored reviews</div>}
          className="evolution-card"
        >
          {data.evolution.length ? (
            <>
              <ResponsiveChart height={286}>
                <LineChart data={data.evolution} margin={chartMargin}>
                  {chartAxes("month", { yDomain: [0, 100] })}
                  {evolutionKeys.map((brand) => (
                    <Line key={brand} type="linear" dataKey={brand} stroke={colorFor(brand)} strokeWidth={2.2} dot={false} activeDot={{ r: 4 }} connectNulls isAnimationActive={false} />
                  ))}
                </LineChart>
              </ResponsiveChart>
              <div className="brand-legend">{evolutionKeys.map((brand) => <BrandTag key={brand} brand={brand} color={colorFor(brand)} compact />)}</div>
            </>
          ) : <EmptyState title="No review history yet" description="Collect reviews for at least one product and the timeline will appear." />}
        </ChartCard>

        <ChartCard title="Share of voice" subtitle="Brand conversation volume (%)" data={share}>
          {share.length ? (
            <>
              <div className="share-chart-wrap">
                <ResponsiveContainer width="100%" height={194}>
                  <PieChart>
                    <Pie data={share} dataKey="value" nameKey="name" innerRadius={62} outerRadius={83} paddingAngle={4} stroke="none">
                      {share.map((item) => <Cell key={item.name} fill={item.color} />)}
                    </Pie>
                    <Tooltip content={<ChartTooltip formatter={(value) => `${value}%`} />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="donut-center"><strong>{totalShare.toFixed(0)}%</strong><span>voice share</span></div>
              </div>
              <div className="share-list">
                {share.map((item) => (
                  <div className="share-row" key={item.name}>
                    <span className="share-name"><i style={{ background: item.color }} />{item.name}</span>
                    <strong>{item.value}%</strong>
                    <div className="share-track"><i style={{ width: `${Math.min(100, item.value * 2.4)}%`, background: item.color }} /></div>
                  </div>
                ))}
              </div>
            </>
          ) : <EmptyState title="No mentions yet" />}
        </ChartCard>
      </div>

      <div className="overview-secondary">
        <ChartCard
          title="Top movers"
          subtitle="Biggest price shifts since the first recorded point"
          data={data.topMovers?.map(({ name, brand, category, change }) => ({ name, brand, category, change }))}
          action={<Link className="text-link" to="/products">All products <ExternalLink size={13} /></Link>}
          className="movers-card"
        >
          {data.topMovers.length ? (
            <div className="mover-list">
              {data.topMovers.map((product, index) => (
                <div className="mover-row" key={product.id}>
                  <span className="mover-rank">0{index + 1}</span>
                  <span className="product-initial" style={{ color: product.color, background: `${product.color}18` }}>{product.brand.slice(0, 1)}</span>
                  <div className="mover-product"><strong>{product.name}</strong><small>{product.brand} <span>·</span> {product.category}</small></div>
                  <div className={`mover-delta ${product.change < 0 ? "negative" : "positive"}`}>
                    {product.change < 0 ? <ArrowDownRight size={15} /> : <ArrowUpRight size={15} />}
                    {Math.abs(product.change).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          ) : <EmptyState title="No price history yet" />}
          {topMover && (
            <div className="mover-callout">
              <span className="callout-icon"><TrendingUp size={15} /></span>
              <span><strong>{topMover.name}</strong> moved {Math.abs(topMover.change).toFixed(1)}% since the first recorded price.</span>
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Notable mentions"
          subtitle="High-signal conversations across your sources"
          data={data.mentions.map(({ brand, text, sentiment, source, time }) => ({ brand, text, sentiment, source, time }))}
          action={<span className="live-status"><span className="live-dot" /> LIVE</span>}
          className="mentions-card"
        >
          {data.mentions.length ? (
            <div className="mention-list">
              {data.mentions.map((mention) => (
                <article className="mention-row" key={mention.id}>
                  <span className={`mention-avatar mention-${mention.brand.toLowerCase()}`}>{mention.initials}</span>
                  <div className="mention-main">
                    <div className="mention-meta"><BrandTag brand={mention.brand} color={colorFor(mention.brand)} compact /><span className="mention-time">{mention.time}</span></div>
                    <p>{mention.text}</p>
                    <div className="mention-footer">
                      <SentimentBadge sentiment={mention.sentiment} /> <SourceTag source={mention.source} />
                      {mention.engagement !== null && mention.engagement !== undefined && (
                        <span className="mention-engagement"><MessageSquare size={12} />{mention.engagement}</span>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : <EmptyState title="No mentions collected yet" />}
        </ChartCard>
      </div>

      <div className="overview-footer-strip">
        <span><Radio size={14} /> Monitoring <strong>{data.product_count} products</strong> across {data.brand_count} tech brands</span>
        <Link to="/recommendations">See what to do next <ArrowUpRight size={14} /></Link>
      </div>
    </div>
  );
}
