import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, Cell, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDownRight, ArrowUpRight, Check, ChevronDown, Minus, Plus, Search, X } from "lucide-react";
import { getProductComparison, getProductDetail, getProducts } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { ChartData } from "../context/ChatContext.jsx";
import { BrandTag, ChartCard, DataTable, EmptyState, ErrorState, PageHeading, PageLoading, SentimentBadge } from "../components/common.jsx";
import { ChartTooltip, ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";
import { formatMoney, formatNumber } from "../constants/brands.js";

export default function ProductAnalysis() {
  const { filters } = useFilters();
  const [sortKey, setSortKey] = useState("sentiment");
  const [sortDirection, setSortDirection] = useState("desc");
  const [category, setCategory] = useState("All categories");
  const [selectedId, setSelectedId] = useState(null);
  const [compareIds, setCompareIds] = useState([]);
  const [tableQuery, setTableQuery] = useState("");

  const listState = useFetch(
    () => getProducts({ ...filters, query: `${filters.query} ${tableQuery}`.trim() }),
    [filters.brand, filters.query, tableQuery],
  );
  const detailState = useFetch(() => (selectedId ? getProductDetail(selectedId) : Promise.resolve(null)), [selectedId]);
  const compareState = useFetch(() => getProductComparison(compareIds), [compareIds.join(",")]);

  // Seed the comparison with the first two products once the list arrives.
  useEffect(() => {
    if (compareIds.length === 0 && listState.data?.length >= 2) {
      setCompareIds(listState.data.slice(0, 2).map((item) => item.id));
    }
  }, [listState.data, compareIds.length]);

  const categories = useMemo(
    () => ["All categories", ...new Set((listState.data || []).map((item) => item.category))],
    [listState.data],
  );

  const rows = useMemo(
    () => (listState.data || [])
      .filter((item) => category === "All categories" || item.category === category)
      .sort((a, b) => {
        const first = a[sortKey];
        const second = b[sortKey];
        if (first === null || first === undefined) return 1;
        if (second === null || second === undefined) return -1;
        return (first > second ? 1 : first < second ? -1 : 0) * (sortDirection === "asc" ? 1 : -1);
      }),
    [listState.data, category, sortKey, sortDirection],
  );

  if (listState.loading) return <PageLoading />;
  if (listState.error) return <ErrorState error={listState.error} />;
  if (!listState.data) return <EmptyState />;

  const sortBy = (key) => {
    setSortDirection(sortKey === key && sortDirection === "desc" ? "asc" : "desc");
    setSortKey(key);
  };
  const toggleCompare = (id) =>
    setCompareIds((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : current.length < 4 ? [...current, id] : current,
    );

  const columns = [
    {
      key: "product",
      label: "PRODUCT",
      render: (item) => (
        <div className="table-product">
          <span className="product-initial" style={{ color: item.color, background: `${item.color}18` }}>{item.brand.slice(0, 1)}</span>
          <span><strong>{item.name}</strong><small><BrandTag brand={item.brand} color={item.color} compact /></small></span>
        </div>
      ),
    },
    { key: "category", label: "CATEGORY" },
    { key: "price", label: "PRICE", render: (item) => <strong className="metric">{formatMoney(item.price, item.currency)}</strong> },
    { key: "rating", label: "RATING", render: (item) => <span className="rating-cell">★ <strong>{formatNumber(item.rating, 1)}</strong></span> },
    {
      key: "sentiment",
      label: "SENTIMENT",
      render: (item) => item.sentiment === null
        ? <span className="sentiment-number neutral">—</span>
        : (
          <div className="sentiment-cell">
            <span className={`sentiment-number ${item.sentiment >= 70 ? "positive" : "neutral"}`}>{item.sentiment.toFixed(0)}</span>
            <span className="sentiment-mini-track"><i style={{ width: `${item.sentiment}%` }} /></span>
          </div>
        ),
    },
    {
      key: "change",
      label: "PRICE TREND",
      render: (item) => item.change === null
        ? <span className="table-trend">—</span>
        : <span className={`table-trend ${item.change >= 0 ? "positive" : "negative"}`}>{item.change >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{Math.abs(item.change).toFixed(1)}%</span>,
    },
    {
      key: "compare",
      label: "",
      render: (item) => (
        <button
          className={`compare-toggle ${compareIds.includes(item.id) ? "selected" : ""}`}
          onClick={(event) => { event.stopPropagation(); toggleCompare(item.id); }}
          aria-label={`${compareIds.includes(item.id) ? "Remove" : "Add"} ${item.name} ${compareIds.includes(item.id) ? "from" : "to"} comparison`}
        >
          {compareIds.includes(item.id) ? <Check size={14} /> : <Plus size={14} />}
        </button>
      ),
    },
  ];

  const detail = detailState.data;
  const comparison = compareState.data || [];

  // The selected pills come from the product list, not from the comparison
  // response: with a single id the backend returns [] (a comparison needs two),
  // which used to make the last remaining pill vanish from the UI.
  const selectedProducts = compareIds
    .map((id) => listState.data.find((item) => item.id === id))
    .filter(Boolean);

  const specKeys = [...new Set(comparison.flatMap((item) => Object.keys(item.specs || {})))];

  return (
    <div className="page">
      <PageHeading
        eyebrow="PRODUCT INTELLIGENCE"
        title="Product analysis"
        description="Find the signal in every spec, review, and price move."
        action={<span className="count-pill">{listState.data.length} products tracked</span>}
      />

      <section className="panel product-table-panel">
        <div className="table-toolbar">
          <div className="table-search">
            <Search size={15} />
            <input placeholder="Search products…" aria-label="Search products" value={tableQuery} onChange={(event) => setTableQuery(event.target.value)} />
          </div>
          <label className="table-filter">
            <select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by category">
              {categories.map((item) => <option key={item}>{item}</option>)}
            </select>
            <ChevronDown size={14} />
          </label>
          <div className="sort-controls">
            <span>Sort by</span>
            {[["sentiment", "Sentiment"], ["price", "Price"], ["change", "Trend"]].map(([key, label]) => (
              <button key={key} className={sortKey === key ? "active" : ""} onClick={() => sortBy(key)}>
                {label}{sortKey === key && (sortDirection === "asc" ? " ↑" : " ↓")}
              </button>
            ))}
          </div>
        </div>
        <ChartData title="Product catalogue" subtitle="Every tracked product with price, rating, sentiment and price trend" data={rows.map(({ name, brand, category, price, currency, rating, sentiment, change, review_count }) => ({ name, brand, category, price, currency, rating, sentiment, change, review_count }))} />
        <DataTable columns={columns} rows={rows} onRowClick={(item) => setSelectedId(item.id)} />
        <div className="table-footer">
          <span>Showing <strong>{rows.length}</strong> of <strong>{listState.data.length}</strong> products</span>
          <span>Sentiment from stored reviews <i className="mini-online" /> live</span>
        </div>
      </section>

      <div className="comparison-panel panel">
        <div className="comparison-header">
          <div>
            <div className="eyebrow">PRODUCT WORKSPACE</div>
            <h2>Compare products <span>{compareIds.length}/4</span></h2>
            <p>Select two to four products from the table to compare side by side.</p>
          </div>
          <div className="comparison-selected">
            {selectedProducts.map((item) => (
              <button className="selected-product-pill" key={item.id} onClick={() => toggleCompare(item.id)}>
                <BrandTag brand={item.brand} color={item.color} compact />{item.name}<X size={13} />
              </button>
            ))}
          </div>
        </div>

        {compareIds.length < 2
          ? <EmptyState title="Choose one more product" description="Select at least two products above to start a comparison." />
          : compareState.loading
            ? <div className="comparison-loading">Preparing product comparison…</div>
            : compareState.error
              ? <ErrorState error={compareState.error} />
              : comparison.length
                ? (
                  <div className="comparison-content">
                    <div className="spec-comparison">
                      <div className="spec-row spec-header">
                        <span>PRODUCT</span>
                        {comparison.map((item) => <span key={item.id}><BrandTag brand={item.brand} color={item.color} compact />{item.name}</span>)}
                      </div>
                      {["category", "price", "rating", "sentiment", "change", ...specKeys].map((key) => (
                        <div className="spec-row" key={key}>
                          <span>{key === "change" ? "Price trend" : key.charAt(0).toUpperCase() + key.slice(1)}</span>
                          {comparison.map((item) => (
                            <span key={item.id} className={key === "sentiment" && item.sentiment > 85 ? "advantage" : ""}>
                              {key === "price"
                                ? formatMoney(item.price, item.currency)
                                : key === "rating"
                                  ? `★ ${formatNumber(item.rating, 1)}`
                                  : key === "sentiment"
                                    ? (item.sentiment === null ? "—" : `${item.sentiment.toFixed(0)}/100`)
                                    : key === "change"
                                      ? (item.change === null ? "—" : `${item.change > 0 ? "+" : ""}${item.change.toFixed(1)}%`)
                                      : item.specs?.[key] || item[key] || "—"}
                            </span>
                          ))}
                        </div>
                      ))}
                    </div>
                    <ChartData title="Product comparison" subtitle="Products selected for side-by-side comparison" data={comparison.map(({ name, brand, price, currency, rating, sentiment, change }) => ({ name, brand, price, currency, rating, sentiment, change }))} />
                    <div className="comparison-radar">
                      <h3>At a glance</h3>
                      <ResponsiveChart height={230}>
                        <RadarChart data={[
                          { spec: "Sentiment", ...Object.fromEntries(comparison.map((item) => [item.name, item.sentiment ?? 0])) },
                          { spec: "Rating", ...Object.fromEntries(comparison.map((item) => [item.name, (item.rating ?? 0) * 20])) },
                          { spec: "Value", ...Object.fromEntries(comparison.map((item) => [item.name, Math.max(20, 100 - item.price / 25)])) },
                          { spec: "Momentum", ...Object.fromEntries(comparison.map((item) => [item.name, Math.min(100, Math.abs(item.change ?? 0) * 4 + 30)])) },
                          { spec: "Reviews", ...Object.fromEntries(comparison.map((item) => [item.name, Math.min(100, item.review_count * 4)])) },
                        ]}>
                          <PolarGrid stroke="var(--border-subtle)" />
                          <PolarAngleAxis dataKey="spec" tick={{ fill: "var(--text-muted)", fontSize: 10 }} />
                          <PolarRadiusAxis tick={false} axisLine={false} domain={[0, 100]} />
                          <Tooltip content={<ChartTooltip />} />
                          {comparison.map((item, index) => (
                            <Radar key={item.id} name={item.name} dataKey={item.name} stroke={item.color} fill={item.color} fillOpacity={index ? 0.06 : 0.15} strokeWidth={2} />
                          ))}
                        </RadarChart>
                      </ResponsiveChart>
                    </div>
                  </div>
                )
                : null}
      </div>

      {selectedId && (
        <div className="drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedId(null); }}>
          <aside className="product-drawer" role="dialog" aria-modal="true" aria-label="Product details">
            <div className="drawer-header">
              <div>
                <span className="eyebrow">PRODUCT INTELLIGENCE</span>
                <button aria-label="Close product details" className="drawer-close icon-button" onClick={() => setSelectedId(null)}><X size={19} /></button>
              </div>

              {detailState.loading ? <div className="drawer-skeleton" />
                : detailState.error ? <ErrorState error={detailState.error} />
                  : detail ? (
                    <>
                      <div className="drawer-title">
                        <span className="product-initial large" style={{ color: detail.product.color, background: `${detail.product.color}18` }}>{detail.product.brand[0]}</span>
                        <div>
                          <BrandTag brand={detail.product.brand} color={detail.product.color} compact />
                          <h2>{detail.product.name}</h2>
                          <small>{detail.product.category}{detail.product.launch ? ` · Released ${detail.product.launch}` : ""}</small>
                        </div>
                      </div>

                      <div className="drawer-price">
                        <strong className="metric">{formatMoney(detail.product.price, detail.product.currency)}</strong>
                        {detail.product.change !== null && (
                          <span className={detail.product.change < 0 ? "negative" : "positive"}>
                            {detail.product.change > 0 ? "+" : ""}{detail.product.change.toFixed(1)}% price movement
                          </span>
                        )}
                      </div>

                      <ChartCard
                        title="Price history"
                        subtitle={detail.forecast.length ? "Recorded points and a linear 30-day projection" : "Recorded points"}
                        data={[...detail.price_history.map((point) => ({ date: point.date, actual: point.price })), ...detail.forecast.map((point) => ({ date: point.date, forecast: point.price }))]}
                        note={`Product: ${detail.product.name}`}
                      >
                        {detail.price_history.length ? (
                          <>
                            <ResponsiveChart height={200}>
                              <AreaChart data={[...detail.price_history.map((point) => ({ date: point.date, actual: point.price })), ...detail.forecast.map((point) => ({ date: point.date, forecast: point.price }))]} margin={chartMargin}>
                                <CartesianGrid {...gridProps} />
                                <XAxis dataKey="date" {...axisProps} />
                                <YAxis {...axisProps} domain={["dataMin - 50", "dataMax + 50"]} tickFormatter={(value) => `${Math.round(value)}`} />
                                <Tooltip content={<ChartTooltip formatter={(value) => formatMoney(value, detail.product.currency)} />} />
                                <Area dataKey="actual" stroke="var(--accent)" fill="var(--accent-soft)" strokeWidth={2.2} connectNulls={false} />
                                <Area dataKey="forecast" stroke="var(--accent)" fill="transparent" strokeWidth={2} strokeDasharray="5 5" connectNulls={false} />
                              </AreaChart>
                            </ResponsiveChart>
                            <div className="forecast-legend">
                              <span><i className="actual-line" /> Recorded price</span>
                              {detail.forecast.length > 0 && <span><i className="forecast-line" /> Linear projection</span>}
                            </div>
                          </>
                        ) : <EmptyState title="No price history" description="Sync the price to start recording points." />}
                      </ChartCard>

                      {Object.keys(detail.product.specs || {}).length > 0 && (
                        <div className="drawer-specs">
                          <h3>Product specifications</h3>
                          {Object.entries(detail.product.specs).map(([key, value]) => (
                            <div key={key}><span>{key}</span><strong>{value}</strong></div>
                          ))}
                        </div>
                      )}

                      {(detail.product.pros.length > 0 || detail.product.cons.length > 0) && (
                        <div className="pros-cons">
                          <div>
                            <h3><span className="pro-dot" /> What customers love</h3>
                            {detail.product.pros.map((item) => <p key={item}><Check size={13} />{item}</p>)}
                            {detail.product.pros.length === 0 && <p className="muted">No positive aspect detected yet.</p>}
                          </div>
                          <div>
                            <h3><span className="con-dot" /> Room to improve</h3>
                            {detail.product.cons.map((item) => <p key={item}><Minus size={13} />{item}</p>)}
                            {detail.product.cons.length === 0 && <p className="muted">No negative aspect detected yet.</p>}
                          </div>
                        </div>
                      )}

                      <div className="review-summary">
                        <h3>Review summary</h3>
                        {detail.review_summary ? (
                          <p>{detail.review_summary}</p>
                        ) : (
                          <p className="muted">
                            {detail.review_summary_source === "pending"
                              ? `${detail.reviews.length} reviews analysed. The written summary is generating; reopen this product in a moment.`
                              : detail.reviews.length
                                ? `${detail.reviews.length} reviews analysed. Configure an OpenRouter model to generate a written summary; the numbers below come from the stored reviews.`
                                : "No reviews collected for this product yet."}
                          </p>
                        )}
                        <div>
                          <SentimentBadge sentiment={detail.product.sentiment >= 70 ? "positive" : detail.product.sentiment >= 45 ? "neutral" : "negative"} />
                          <strong>{detail.product.sentiment === null ? "—" : `${detail.product.sentiment.toFixed(0)}/100`}</strong> average sentiment
                        </div>
                      </div>

                      <button
                        className="button button-primary drawer-compare"
                        onClick={() => { toggleCompare(detail.product.id); setSelectedId(null); }}
                      >
                        {compareIds.includes(detail.product.id) ? "Remove from comparison" : "Add to comparison"}
                      </button>
                    </>
                  ) : null}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
