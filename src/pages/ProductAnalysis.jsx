import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, Cell, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDownRight, ArrowUpRight, Check, ChevronDown, Download, Minus, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import {
  createProduct,
  deleteProduct,
  getProductComparison,
  getProductDetail,
  getProducts,
  importProductFromEmag,
  updateProduct,
} from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { ChartData } from "../context/ChatContext.jsx";
import { BrandTag, ChartCard, DataTable, EmptyState, ErrorState, PageHeading, PageLoading, SentimentBadge } from "../components/common.jsx";
import { ChartTooltip, ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";
import { formatMoney, formatNumber } from "../constants/brands.js";

const EMPTY_FORM = {
  name: "", brand: "", category: "Smartphone", price: "", currency: "RON",
  source: "Manual", source_url: "", sku: "", launch: "", specs: "",
};

// Mirrors the backend's ProductBase rules (name 2-150, price > 0) so the user
// sees the problem before the request, and the API stays the final authority.
function validate(form) {
  const errors = {};
  const name = form.name.trim();
  if (name.length < 2 || name.length > 150) errors.name = "Name must be 2 to 150 characters.";
  if (!form.brand.trim()) errors.brand = "Brand is required.";
  if (!form.category.trim()) errors.category = "Category is required.";
  const price = Number(form.price);
  if (!Number.isFinite(price) || price <= 0) errors.price = "Price must be greater than 0.";
  if (form.specs.trim()) {
    try {
      const parsed = JSON.parse(form.specs);
      if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) errors.specs = "Specs must be a JSON object.";
    } catch {
      errors.specs = "Specs must be valid JSON.";
    }
  }
  return errors;
}

function ProductForm({ product, onClose, onSaved }) {
  const [form, setForm] = useState(() => (product ? {
    name: product.name || "", brand: product.brand || "", category: product.category || "",
    price: String(product.price ?? ""), currency: product.currency || "RON",
    source: product.source || "", source_url: product.source_url || "", sku: product.sku || "",
    launch: product.launch || "",
    specs: product.specs && Object.keys(product.specs).length ? JSON.stringify(product.specs, null, 2) : "",
  } : EMPTY_FORM));
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [saving, setSaving] = useState(false);

  const set = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length) return;

    const payload = {
      name: form.name.trim(),
      brand: form.brand.trim(),
      category: form.category.trim(),
      price: Number(form.price),
      currency: form.currency.trim() || "RON",
      source: form.source.trim() || null,
      source_url: form.source_url.trim() || null,
      sku: form.sku.trim() || null,
      launch: form.launch.trim() || null,
      specs: form.specs.trim() ? JSON.parse(form.specs) : null,
    };

    setSaving(true);
    setSubmitError("");
    try {
      if (product) await updateProduct(product.id, payload);
      else await createProduct(payload);
      onSaved();
    } catch (error) {
      setSubmitError(error.message || "The product could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <aside className="product-drawer" role="dialog" aria-modal="true" aria-label={product ? "Edit product" : "Add product"}>
        <div className="drawer-header">
          <div>
            <span className="eyebrow">{product ? "EDIT PRODUCT" : "NEW PRODUCT"}</span>
            <button aria-label="Close form" className="drawer-close icon-button" onClick={onClose}><X size={19} /></button>
          </div>
          <h2>{product ? product.name : "Add a product"}</h2>
        </div>

        <form className="product-form" onSubmit={submit} noValidate>
          <label><span>Name</span>
            <input value={form.name} onChange={set("name")} aria-invalid={!!errors.name} />
            {errors.name && <small className="form-error">{errors.name}</small>}
          </label>
          <div className="form-row">
            <label><span>Brand</span>
              <input value={form.brand} onChange={set("brand")} aria-invalid={!!errors.brand} />
              {errors.brand && <small className="form-error">{errors.brand}</small>}
            </label>
            <label><span>Category</span>
              <input value={form.category} onChange={set("category")} aria-invalid={!!errors.category} />
              {errors.category && <small className="form-error">{errors.category}</small>}
            </label>
          </div>
          <div className="form-row">
            <label><span>Price</span>
              <input type="number" min="0" step="0.01" value={form.price} onChange={set("price")} aria-invalid={!!errors.price} />
              {errors.price && <small className="form-error">{errors.price}</small>}
            </label>
            <label><span>Currency</span>
              <input value={form.currency} onChange={set("currency")} />
            </label>
          </div>
          <div className="form-row">
            <label><span>Source</span>
              <input value={form.source} onChange={set("source")} placeholder="Manual, eMAG…" />
            </label>
            <label><span>SKU</span>
              <input value={form.sku} onChange={set("sku")} placeholder="Optional" />
            </label>
          </div>
          <label><span>Source URL</span>
            <input value={form.source_url} onChange={set("source_url")} placeholder="https://…" />
          </label>
          <label><span>Launch</span>
            <input value={form.launch} onChange={set("launch")} placeholder="e.g. Sep 2024" />
          </label>
          <label><span>Specs (JSON, optional)</span>
            <textarea rows={5} value={form.specs} onChange={set("specs")} placeholder='{"Display": "6.8&quot; AMOLED"}' aria-invalid={!!errors.specs} />
            {errors.specs && <small className="form-error">{errors.specs}</small>}
          </label>

          {submitError && <p className="form-error" role="alert">{submitError}</p>}

          <div className="form-actions">
            <button type="button" className="button button-quiet" onClick={onClose}>Cancel</button>
            <button type="submit" className="button button-primary" disabled={saving}>{saving ? "Saving…" : product ? "Save changes" : "Create product"}</button>
          </div>
        </form>
      </aside>
    </div>
  );
}

export default function ProductAnalysis() {
  const { filters } = useFilters();
  const [sortKey, setSortKey] = useState("sentiment");
  const [sortDirection, setSortDirection] = useState("desc");
  const [category, setCategory] = useState("All categories");
  const [selectedId, setSelectedId] = useState(null);
  const [compareIds, setCompareIds] = useState([]);
  const [tableQuery, setTableQuery] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [importQuery, setImportQuery] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const [importNotice, setImportNotice] = useState("");
  const [deleteError, setDeleteError] = useState("");

  const listState = useFetch(
    () => getProducts({ ...filters, query: `${filters.query} ${tableQuery}`.trim() }),
    [filters.brand, filters.query, tableQuery, reloadKey],
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

  const refreshList = () => setReloadKey((key) => key + 1);
  const openCreate = () => { setEditing(null); setFormOpen(true); };
  const openEdit = (product) => { setEditing(product); setFormOpen(true); };

  const runImport = async (event) => {
    event.preventDefault();
    const term = importQuery.trim();
    if (term.length < 2 || importing) return;
    setImporting(true);
    setImportError("");
    setImportNotice("");
    try {
      const created = await importProductFromEmag(term, null);
      setImportNotice(`Imported "${created.name}" from eMAG.`);
      setImportQuery("");
      refreshList();
    } catch (error) {
      // The backend's 503 detail explains why eMAG could not be reached; show it verbatim.
      setImportError(error.message || "The import failed.");
    } finally {
      setImporting(false);
    }
  };

  const removeProduct = async (product) => {
    if (!window.confirm(`Delete "${product.name}"? Its reviews and price history are removed too.`)) return;
    setDeleteError("");
    try {
      await deleteProduct(product.id);
      setSelectedId(null);
      setCompareIds((current) => current.filter((id) => id !== product.id));
      refreshList();
    } catch (error) {
      setDeleteError(error.message || "The product could not be deleted.");
    }
  };

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
        action={
          <div className="page-heading-actions">
            <span className="count-pill">{listState.data.length} products tracked</span>
            <button className="button button-primary" onClick={openCreate}><Plus size={14} /> Add product</button>
          </div>
        }
      />

      <section className="panel product-table-panel">
        <form className="product-import-bar" onSubmit={runImport}>
          <div className="table-search">
            <Download size={15} />
            <input
              placeholder="Import a product from eMAG…"
              aria-label="Search eMAG to import a product"
              value={importQuery}
              onChange={(event) => setImportQuery(event.target.value)}
            />
          </div>
          <button className="button button-quiet" type="submit" disabled={importing || importQuery.trim().length < 2}>
            {importing ? "Searching eMAG…" : "Import from eMAG"}
          </button>
          {importError && <span className="form-error" role="alert">{importError}</span>}
          {importNotice && <span className="form-notice" role="status">{importNotice}</span>}
        </form>
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

                      {deleteError && <p className="form-error" role="alert">{deleteError}</p>}

                      <div className="drawer-actions">
                        <button
                          className="button button-primary drawer-compare"
                          onClick={() => { toggleCompare(detail.product.id); setSelectedId(null); }}
                        >
                          {compareIds.includes(detail.product.id) ? "Remove from comparison" : "Add to comparison"}
                        </button>
                        <button className="button button-quiet" onClick={() => openEdit(detail.product)}><Pencil size={13} /> Edit</button>
                        <button className="button button-quiet danger" onClick={() => removeProduct(detail.product)}><Trash2 size={13} /> Delete</button>
                      </div>
                    </>
                  ) : null}
            </div>
          </aside>
        </div>
      )}

      {formOpen && (
        <ProductForm
          product={editing}
          onClose={() => { setFormOpen(false); setEditing(null); }}
          onSaved={() => { setFormOpen(false); setEditing(null); refreshList(); }}
        />
      )}
    </div>
  );
}
