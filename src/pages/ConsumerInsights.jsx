import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { ArrowRight, ChevronRight, Users } from "lucide-react";
import { getConsumerSegments, getSentiment } from "../services/api.js";
import { useFetch } from "../hooks/useFetch.js";
import { useFilters } from "../context/AppContext.jsx";
import { ChartCard, EmptyState, ErrorState, PageHeading, PageLoading } from "../components/common.jsx";
import { ChartTooltip, ResponsiveChart, axisProps, chartMargin, gridProps } from "../components/charts.jsx";

const DRIVER_COLORS = ["#a6e06c", "#f3bb6a", "#a39af9", "#73baf5", "#f08399", "#84cfc2", "#d4a5f0", "#f0c674"];

export default function ConsumerInsights() {
  const { filters } = useFilters();
  const segmentsState = useFetch(() => getConsumerSegments(filters), [filters.brand]);
  const sentimentState = useFetch(() => getSentiment(filters), [filters.brand]);
  const [activeSegment, setActiveSegment] = useState(null);

  if (segmentsState.loading || sentimentState.loading) return <PageLoading />;
  if (segmentsState.error || sentimentState.error) return <ErrorState error={segmentsState.error || sentimentState.error} />;
  if (!segmentsState.data?.length) return <EmptyState title="No consumer segments yet" description="Collect reviews for at least one product." />;

  const segments = segmentsState.data;
  const active = segments.find((item) => item.id === activeSegment) || segments[0];
  const totalUsers = segments.reduce((sum, item) => sum + item.usersValue, 0);

  // Purchase drivers are the aspect scores from the same reviews, which is the
  // only evidence the platform actually has. No survey numbers are invented.
  const drivers = (sentimentState.data?.aspects || []).slice(0, 6).map((item, index) => ({
    name: item.aspect,
    score: item.score,
    mentions: item.mentions,
    color: DRIVER_COLORS[index % DRIVER_COLORS.length],
  }));

  return (
    <div className="page">
      <PageHeading
        eyebrow="AUDIENCE INTELLIGENCE"
        title="Meet the people behind the purchase."
        description="Segments derived from what reviewers actually discuss."
        action={<span className="freshness-pill"><Users size={14} />{totalUsers} reviewed mentions modelled</span>}
      />

      <div className="segment-card-grid">
        {segments.map((segment) => (
          <button
            className={`panel segment-card ${segment.id === active.id ? "active" : ""}`}
            key={segment.id}
            onClick={() => setActiveSegment(segment.id)}
            style={{ "--segment-color": segment.color }}
          >
            <div className="segment-card-top">
              <span className="segment-mark"><Users size={17} /></span>
              <span className="segment-growth"><ArrowRight size={12} /></span>
            </div>
            <strong className="segment-title">{segment.name}</strong>
            <div className="segment-size-row"><strong>{segment.size}</strong><span>of audience</span></div>
            <div className="segment-card-stats">
              <span><small>Avg. spend</small><strong>{segment.spend}</strong></span>
              <span><small>Audience</small><strong>{segment.users}</strong></span>
            </div>
            <div className="segment-progress"><i style={{ width: `${segment.sizeValue}%` }} /></div>
          </button>
        ))}
      </div>

      <div className="consumer-chart-grid">
        <ChartCard title="Purchase drivers" subtitle="Sentiment for each aspect across the reviews behind these segments" data={drivers}>
          {drivers.length ? (
            <>
              <ResponsiveChart height={264}>
                <BarChart data={drivers} layout="vertical" margin={{ ...chartMargin, left: 10, right: 16 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis type="number" domain={[0, 100]} {...axisProps} />
                  <YAxis type="category" dataKey="name" width={152} {...axisProps} />
                  <Tooltip content={<ChartTooltip formatter={(value) => `${value}/100`} />} />
                  <Bar dataKey="score" name="Sentiment score" radius={[0, 5, 5, 0]} barSize={15}>
                    {drivers.map((driver) => <Cell fill={driver.color} key={driver.name} />)}
                  </Bar>
                </BarChart>
              </ResponsiveChart>
              <div className="chart-footnote">
                <span>0 = negative, 100 = positive</span>
                <span>Based on {sentimentState.data.total_reviews} reviews</span>
              </div>
            </>
          ) : <EmptyState title="No aspect data yet" />}
        </ChartCard>

        <ChartCard title="Audience landscape" subtitle="Price sensitivity vs. brand loyalty" data={segments} className="consumer-scatter-card">
          <ResponsiveChart height={264}>
            <ScatterChart margin={{ top: 10, right: 14, bottom: 4, left: 0 }}>
              <CartesianGrid {...gridProps} />
              <XAxis type="number" dataKey="sensitivity" name="Price sensitivity" domain={[0, 100]} {...axisProps} label={{ value: "Price sensitivity →", position: "insideBottom", offset: -3, fill: "var(--text-muted)", fontSize: 10 }} />
              <YAxis type="number" dataKey="loyalty" name="Brand loyalty" domain={[0, 100]} {...axisProps} />
              <ZAxis type="number" dataKey="sizeValue" range={[90, 460]} />
              <Tooltip content={({ active: show, payload }) => (show && payload?.length ? (
                <div className="chart-tooltip">
                  <strong>{payload[0].payload.name}</strong>
                  <div className="tooltip-row">Price sensitivity <b>{payload[0].payload.sensitivity}</b></div>
                  <div className="tooltip-row">Brand loyalty <b>{payload[0].payload.loyalty}</b></div>
                  <div className="tooltip-row">Share <b>{payload[0].payload.size}</b></div>
                </div>
              ) : null)} />
              <Scatter name="Consumer segments" data={segments}>
                {segments.map((item) => <Cell key={item.id} fill={item.color} fillOpacity={0.86} />)}
              </Scatter>
            </ScatterChart>
          </ResponsiveChart>
          <div className="scatter-axis-hints"><span>Low sensitivity</span><span>High sensitivity</span></div>
        </ChartCard>
      </div>

      <div className="preference-panel panel">
        <div className="preference-heading">
          <div>
            <div className="eyebrow">SEGMENT SPOTLIGHT</div>
            <h2>{active.name}</h2>
            <p>What matters most to this audience</p>
          </div>
          <span className="preference-size" style={{ color: active.color }}>{active.size}<small> of audience</small></span>
        </div>
        <div className="preference-details">
          <div className="preference-tags">
            {active.preferences.map((preference, index) => (
              <span key={preference}><i style={{ background: active.color }} />{preference}<small>0{index + 1}</small></span>
            ))}
          </div>
          <div className="preference-metrics">
            <span><small>Avg. spend</small><strong>{active.spend}</strong></span>
            <span><small>Brand loyalty</small><strong>{active.loyalty.toFixed(0)}<small>/100</small></strong></span>
            <span><small>Price sensitivity</small><strong>{active.sensitivity.toFixed(0)}<small>/100</small></strong></span>
            <button className="button button-quiet" onClick={() => setActiveSegment(segments[(segments.indexOf(active) + 1) % segments.length].id)}>
              Next segment <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
