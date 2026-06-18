import type { ReactNode } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const AXIS = 'var(--c-subtle)';
const GRID = 'var(--c-border)';

const SERIES_COLORS = [
  'var(--c-accent)',
  'var(--c-success)',
  'var(--c-warning)',
  'var(--c-info)',
  'var(--c-danger)',
];

interface SeriesDef {
  key: string;
  label: string;
  color?: string;
}

const tooltipStyle = {
  background: 'var(--c-surface-raised)',
  border: '1px solid var(--c-border)',
  borderRadius: 8,
  color: 'var(--c-fg)',
  fontSize: 12,
};

const axisProps = {
  stroke: AXIS,
  tick: { fill: AXIS, fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: GRID },
} as const;

interface ChartFrameProps {
  height?: number;
  children: ReactNode;
}

function Frame({ height = 240, children }: ChartFrameProps) {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children as React.ReactElement}
      </ResponsiveContainer>
    </div>
  );
}

interface StackedAreaProps {
  data: Array<Record<string, number | string>>;
  xKey: string;
  series: SeriesDef[];
  stacked?: boolean;
  height?: number;
}

export function AreaTrend({ data, xKey, series, stacked = false, height }: StackedAreaProps) {
  return (
    <Frame height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <defs>
          {series.map((s, index) => {
            const color = s.color ?? SERIES_COLORS[index % SERIES_COLORS.length];
            return (
              <linearGradient key={s.key} id={`area-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.28} />
                <stop offset="100%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            );
          })}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey={xKey} {...axisProps} />
        <YAxis {...axisProps} width={40} />
        <Tooltip contentStyle={tooltipStyle} />
        {series.length > 1 ? <Legend wrapperStyle={{ fontSize: 12, color: 'var(--c-muted)' }} /> : null}
        {series.map((s, index) => {
          const color = s.color ?? SERIES_COLORS[index % SERIES_COLORS.length];
          return (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stackId={stacked ? 'stack' : undefined}
              stroke={color}
              strokeWidth={2}
              fill={`url(#area-${s.key})`}
            />
          );
        })}
      </AreaChart>
    </Frame>
  );
}

export function LineTrend({ data, xKey, series, height }: Omit<StackedAreaProps, 'stacked'>) {
  return (
    <Frame height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey={xKey} {...axisProps} />
        <YAxis {...axisProps} width={40} />
        <Tooltip contentStyle={tooltipStyle} />
        {series.length > 1 ? <Legend wrapperStyle={{ fontSize: 12, color: 'var(--c-muted)' }} /> : null}
        {series.map((s, index) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.label}
            stroke={s.color ?? SERIES_COLORS[index % SERIES_COLORS.length]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </Frame>
  );
}

interface BarSeriesProps {
  data: Array<Record<string, number | string>>;
  xKey: string;
  series: SeriesDef[];
  height?: number;
  layout?: 'horizontal' | 'vertical';
}

export function BarSeries({ data, xKey, series, height, layout = 'horizontal' }: BarSeriesProps) {
  const vertical = layout === 'vertical';
  return (
    <Frame height={height}>
      <BarChart
        data={data}
        layout={layout}
        margin={{ top: 8, right: 8, bottom: 0, left: vertical ? 8 : -12 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={vertical} horizontal={!vertical} />
        {vertical ? (
          <>
            <XAxis type="number" {...axisProps} />
            <YAxis type="category" dataKey={xKey} {...axisProps} width={120} />
          </>
        ) : (
          <>
            <XAxis dataKey={xKey} {...axisProps} />
            <YAxis {...axisProps} width={40} />
          </>
        )}
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'var(--c-surface-sunken)' }} />
        {series.length > 1 ? <Legend wrapperStyle={{ fontSize: 12, color: 'var(--c-muted)' }} /> : null}
        {series.map((s, index) => (
          <Bar
            key={s.key}
            dataKey={s.key}
            name={s.label}
            fill={s.color ?? SERIES_COLORS[index % SERIES_COLORS.length]}
            radius={vertical ? [0, 4, 4, 0] : [4, 4, 0, 0]}
            maxBarSize={36}
          />
        ))}
      </BarChart>
    </Frame>
  );
}

interface FunnelStep {
  label: string;
  value: number;
}

/** Horizontal funnel rendered with proportional bars (avoids extra deps). */
export function FunnelBars({ steps }: { steps: FunnelStep[] }) {
  const max = Math.max(...steps.map((step) => step.value), 1);
  return (
    <div className="flex flex-col gap-3">
      {steps.map((step, index) => {
        const pct = Math.round((step.value / max) * 100);
        const conversion = index === 0 ? 100 : Math.round((step.value / (steps[0].value || 1)) * 100);
        return (
          <div key={step.label}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="font-medium text-fg">{step.label}</span>
              <span className="tabular-nums text-muted">
                {step.value.toLocaleString()} <span className="text-subtle">({conversion}%)</span>
              </span>
            </div>
            <div className="h-7 w-full overflow-hidden rounded-md bg-surface-sunken">
              <div
                className="flex h-full items-center rounded-md bg-accent/85 px-2 text-xs font-medium text-accent-fg transition-all"
                style={{ width: `${Math.max(pct, 3)}%`, backgroundColor: SERIES_COLORS[index % SERIES_COLORS.length] }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export { Cell };
