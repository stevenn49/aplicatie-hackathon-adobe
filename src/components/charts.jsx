import { CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// `left` was -12, which pulled the Y axis outside the SVG and clipped the first
// digit of every two-digit tick ("32" rendered as "2") on charts whose Y axis is
// narrow. A zero margin keeps the labels inside the viewport.
export const chartMargin = { top: 8, right: 8, bottom: 0, left: 0 };
export const axisProps = {
  tick: { fill: "var(--text-muted)", fontSize: 11 },
  axisLine: false,
  tickLine: false,
  tickMargin: 10,
};
export const gridProps = { stroke: "var(--border-subtle)", strokeDasharray: "3 5", vertical: false };

export function ChartTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><strong>{label}</strong>{payload.map((item) => <div key={item.dataKey} className="tooltip-row"><span className="tooltip-dot" style={{ background: item.color }} />{item.name || item.dataKey}<b>{formatter ? formatter(item.value, item.dataKey) : item.value}</b></div>)}</div>;
}

/**
 * Grid + axes + tooltip for a categorical chart, as an ARRAY of elements.
 *
 * Recharts does not render arbitrary children: `renderByOrder` looks each child
 * up in a registry keyed by display name and silently drops anything it does not
 * recognise. A wrapper component such as `<ChartAxes xKey="month" />` therefore
 * rendered nothing at all — no grid, no axes, no tooltip — while the lines drew
 * fine, which is exactly how the Market Overview chart lost its scale.
 *
 * Returning an array and calling this as a function keeps the elements as direct
 * children of the chart (React.Children flattens arrays), so Recharts sees them.
 * Do not turn this back into a component.
 */
export const chartAxes = (xKey, { yWidth = 34, yFormatter, yDomain } = {}) => [
  <CartesianGrid key="grid" {...gridProps} />,
  <XAxis key="x" dataKey={xKey} {...axisProps} tickLine={false} minTickGap={22} />,
  <YAxis key="y" {...axisProps} width={yWidth} tickFormatter={yFormatter} domain={yDomain} />,
  <Tooltip key="tooltip" content={<ChartTooltip />} cursor={{ stroke: "var(--border)", strokeDasharray: "3 4" }} />,
];

export function ResponsiveChart({ children, height = 270 }) {
  return <div className="chart-canvas" style={{ height }}><ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer></div>;
}
