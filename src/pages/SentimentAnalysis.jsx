import { useMemo, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, Tooltip, XAxis, YAxis } from "recharts";
import { ChevronLeft, ChevronRight, MessageSquareText, Star } from "lucide-react";
import { getSentiment } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { ChartCard, EmptyState, ErrorState, PageHeading, PageLoading, SentimentBadge, SourceTag } from "../components/common.jsx";
import { ChartTooltip, ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";

const scoreColor = (score) => (score >= 68 ? "var(--positive)" : score >= 48 ? "var(--neutral)" : "var(--negative)");

export default function SentimentAnalysis() {
  const { filters } = useFilters();
  const [page, setPage] = useState(1);
  const [sentimentFilter, setSentimentFilter] = useState("All feedback");

  const state = useFetch(() => getSentiment(filters), [filters.brand, filters.source]);
  const data = state.data;

  const filteredReviews = useMemo(
    () => (data?.reviews || []).filter(
      (review) => sentimentFilter === "All feedback" || review.sentiment === sentimentFilter.toLowerCase(),
    ),
    [data, sentimentFilter],
  );
  const pageSize = 3;
  const pages = Math.max(1, Math.ceil(filteredReviews.length / pageSize));

  if (state.loading) return <PageLoading />;
  if (state.error) return <ErrorState error={state.error} />;
  if (!data) return <EmptyState />;

  const positive = data.distribution.find((item) => item.name === "Positive")?.value ?? 0;
  const trendDirection = (() => {
    // Compare the first and last week that actually contain reviews. An empty
    // leading bucket has 0 % positive, which used to produce a meaningless
    // "+100 pts" claim.
    const nonEmpty = data.trend.filter((point) => point.positive + point.neutral + point.negative > 0);
    if (nonEmpty.length < 2) return null;
    const first = nonEmpty[0].positive;
    const last = nonEmpty[nonEmpty.length - 1].positive;
    return { delta: last - first, up: last >= first, weeks: nonEmpty.length };
  })();

  return (
    <div className="page">
      <PageHeading
        eyebrow="VOICE OF THE CUSTOMER"
        title="Sentiment analysis"
        description="Understand not just what customers say, but how they feel."
        action={<span className="freshness-pill"><span className="positive-dot" />{data.total_reviews} reviews analyzed</span>}
      />

      <div className="sentiment-summary">
        <div className="panel sentiment-donut-panel">
          <div className="panel-heading">
            <div><h2>Sentiment distribution</h2><p>Share of customer feedback</p></div>
            <span className="model-pill"><span className="mini-online" /> VADER + tech lexicon</span>
          </div>
          {data.total_reviews ? (
            <>
              <div className="sentiment-donut-wrap">
                <ResponsiveChart height={210}>
                  <PieChart>
                    <Pie data={data.distribution} dataKey="value" innerRadius={66} outerRadius={90} paddingAngle={4} stroke="none">
                      {data.distribution.map((item) => <Cell fill={item.color} key={item.name} />)}
                    </Pie>
                    <Tooltip content={<ChartTooltip formatter={(value) => `${value}%`} />} />
                  </PieChart>
                </ResponsiveChart>
                <div className="donut-center"><strong>{positive.toFixed(0)}%</strong><span>positive</span></div>
              </div>
              <div className="sentiment-legend">
                {data.distribution.map((item) => (
                  <span key={item.name}><i style={{ background: item.color }} />{item.name}<strong>{item.value}%</strong></span>
                ))}
              </div>
            </>
          ) : <EmptyState title="No reviews yet" description="Collect reviews to see the sentiment split." />}
        </div>

        <ChartCard title="Sentiment trend" subtitle="Weekly emotion across all reviews" data={data.trend} className="sentiment-trend-panel">
          {data.trend.length ? (
            <>
              <ResponsiveChart height={220}>
                <AreaChart data={data.trend} margin={chartMargin}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="date" {...axisProps} />
                  <YAxis {...axisProps} domain={[0, 100]} />
                  <Tooltip content={<ChartTooltip formatter={(value) => `${value}%`} />} />
                  <Area type="monotone" dataKey="positive" name="Positive" stroke="var(--positive)" fill="var(--positive)" fillOpacity={0.08} strokeWidth={2.2} />
                  <Area type="monotone" dataKey="neutral" name="Neutral" stroke="var(--neutral)" fill="transparent" strokeWidth={2} />
                  <Area type="monotone" dataKey="negative" name="Negative" stroke="var(--negative)" fill="transparent" strokeWidth={2} />
                </AreaChart>
              </ResponsiveChart>
              {trendDirection && (
                <div className="trend-note">
                  {Math.abs(trendDirection.delta) < 0.05 ? (
                    <>
                      <span className="neutral-dot" />
                      Positive share is <strong>stable</strong> across the {trendDirection.weeks} weeks with reviews
                    </>
                  ) : (
                    <>
                      <span className={trendDirection.up ? "positive-dot" : "negative-dot"} />
                      Positive share is {trendDirection.up ? "up" : "down"} <strong>{Math.abs(trendDirection.delta).toFixed(1)} pts</strong> across the {trendDirection.weeks} weeks with reviews
                    </>
                  )}
                </div>
              )}
            </>
          ) : <EmptyState title="No trend data yet" />}
        </ChartCard>
      </div>

      <div className="sentiment-details-grid">
        <ChartCard title="Aspect-based sentiment" subtitle="What customers feel about specific features" data={data.aspects}>
          {data.aspects.length ? (
            <>
              <ResponsiveChart height={278}>
                <BarChart data={data.aspects} layout="vertical" margin={{ ...chartMargin, left: 10, right: 20 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis type="number" domain={[0, 100]} {...axisProps} />
                  <YAxis type="category" dataKey="aspect" width={105} {...axisProps} />
                  <Tooltip content={<ChartTooltip formatter={(value) => `${value}/100`} />} />
                  <Bar dataKey="score" name="Sentiment score" radius={[0, 5, 5, 0]} barSize={13}>
                    {data.aspects.map((item) => <Cell fill={scoreColor(item.score)} key={item.aspect} />)}
                  </Bar>
                </BarChart>
              </ResponsiveChart>
              <div className="chart-footnote"><span>0 = negative</span><span>100 = positive</span></div>
            </>
          ) : <EmptyState title="No aspect data yet" />}
        </ChartCard>

        <section className="panel keyword-panel">
          <div className="panel-heading"><div><h2>What customers talk about</h2><p>Keywords weighted by conversation volume</p></div></div>
          {data.keywords.length ? (
            <>
              <div className="keyword-cloud">
                {data.keywords.map((item) => (
                  <span className={`keyword ${item.tone}`} style={{ fontSize: `${12 + item.score / 18}px` }} key={item.word}>
                    {item.word}<sup>{Math.round(item.score / 10)}</sup>
                  </span>
                ))}
              </div>
              <div className="keyword-footer">
                <span><i className="positive-dot" /> Positive</span>
                <span><i className="neutral-dot" /> Mixed</span>
                <span><i className="negative-dot" /> Negative</span>
              </div>
            </>
          ) : <EmptyState title="No keywords yet" />}
        </section>
      </div>

      <section className="panel review-explorer">
        <div className="panel-heading">
          <div><h2>Review explorer</h2><p>Recent reviews with AI-classified sentiment</p></div>
          <label className="table-filter">
            <select value={sentimentFilter} onChange={(event) => { setSentimentFilter(event.target.value); setPage(1); }} aria-label="Filter reviews by sentiment">
              <option>All feedback</option><option>Positive</option><option>Neutral</option><option>Negative</option>
            </select>
          </label>
        </div>
        {filteredReviews.length ? (
          <>
            <div className="review-list">
              {filteredReviews.slice((page - 1) * pageSize, page * pageSize).map((review) => (
                <article className="review-card" key={review.id}>
                  <div className="review-avatar">{review.author.slice(0, 1).toUpperCase()}</div>
                  <div className="review-body">
                    <div className="review-meta">
                      <strong>@{review.author}</strong><span>·</span><span>{review.date}</span>
                      {review.rating !== null && (
                        <span className="review-rating">
                          {Array.from({ length: 5 }, (_, i) => <Star size={12} key={i} fill={i < review.rating ? "currentColor" : "none"} />)}
                        </span>
                      )}
                    </div>
                    <p>{review.text}</p>
                    <div className="review-tags">
                      <SentimentBadge sentiment={review.sentiment} />
                      <span className="review-product">{review.brand} <span>·</span> {review.product}</span>
                      <SourceTag source={review.source} />
                      {review.helpful !== null && review.helpful !== undefined && (
                        <span className="review-helpful"><MessageSquareText size={12} /> {review.helpful} found helpful</span>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
            <div className="pagination">
              <span>Showing <strong>{Math.min(filteredReviews.length, (page - 1) * pageSize + 1)}–{Math.min(filteredReviews.length, page * pageSize)}</strong> of <strong>{filteredReviews.length}</strong> reviews</span>
              <div>
                <button aria-label="Previous page" disabled={page === 1} onClick={() => setPage((current) => current - 1)}><ChevronLeft size={15} /></button>
                <span>Page <strong>{page}</strong> of {pages}</span>
                <button aria-label="Next page" disabled={page >= pages} onClick={() => setPage((current) => current + 1)}><ChevronRight size={15} /></button>
              </div>
            </div>
          </>
        ) : <EmptyState title="No reviews match this filter" description="Try a different sentiment or data source." />}
      </section>
    </div>
  );
}
