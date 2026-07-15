import type { ReactNode } from "react";

function clamp(value: number, min = 0, max = 100): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

export function HorizontalMetricBar({
  value,
  max = 100,
  label,
  className = "h-2 w-full",
  trackClassName = "fill-slate-200",
  indicatorClassName = "fill-cyan-600",
}: {
  value: number;
  max?: number;
  label: string;
  className?: string;
  trackClassName?: string;
  indicatorClassName?: string;
}) {
  const safeMax = max > 0 && Number.isFinite(max) ? max : 100;
  const safeValue = clamp(value, 0, safeMax);
  const percentage = (safeValue / safeMax) * 100;

  return (
    <svg
      viewBox="0 0 100 8"
      preserveAspectRatio="none"
      className={`block ${className}`}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={safeMax}
      aria-valuenow={safeValue}
    >
      <title>{label}</title>
      <rect x={0} y={0} width={100} height={8} rx={4} className={trackClassName} />
      <rect
        x={0}
        y={0}
        width={percentage}
        height={8}
        rx={4}
        className={indicatorClassName}
      />
    </svg>
  );
}

export type MetricSegment = {
  label: string;
  value: number;
  className: string;
};

export function SegmentedMetricBar({
  segments,
  max,
  label,
  className = "h-3 w-full",
  trackClassName = "fill-slate-100",
}: {
  segments: MetricSegment[];
  max?: number;
  label: string;
  className?: string;
  trackClassName?: string;
}) {
  const sum = segments.reduce((total, segment) => total + Math.max(0, segment.value), 0);
  const safeMax = Math.max(max ?? 0, sum, 1);
  const widths = segments.map(
    (segment) => (clamp(segment.value, 0, safeMax) / safeMax) * 100,
  );
  const normalized = segments.map((segment, index) => ({
    ...segment,
    x: widths.slice(0, index).reduce((total, width) => total + width, 0),
    width: widths[index],
  }));

  return (
    <svg
      viewBox="0 0 100 8"
      preserveAspectRatio="none"
      className={`block ${className}`}
      role="img"
      aria-label={label}
    >
      <title>{label}</title>
      <rect x={0} y={0} width={100} height={8} rx={4} className={trackClassName} />
      {normalized.map((segment) => (
        <rect
          key={segment.label}
          x={segment.x}
          y={0}
          width={segment.width}
          height={8}
          className={segment.className}
        >
          <title>{`${segment.label}: ${segment.value}`}</title>
        </rect>
      ))}
    </svg>
  );
}

export function VerticalMetricBar({
  value,
  label,
  className = "h-full w-full",
  trackClassName = "fill-transparent",
  indicatorClassName = "fill-slate-700",
}: {
  value: number;
  label: string;
  className?: string;
  trackClassName?: string;
  indicatorClassName?: string;
}) {
  const percentage = clamp(value);
  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className={`block ${className}`}
      role="img"
      aria-label={label}
    >
      <title>{label}</title>
      <rect x={0} y={0} width={100} height={100} className={trackClassName} />
      <rect
        x={0}
        y={100 - percentage}
        width={100}
        height={percentage}
        rx={4}
        className={indicatorClassName}
      />
    </svg>
  );
}

export function MetricRing({
  value,
  label,
  children,
  className = "h-28 w-28",
  trackClassName = "stroke-slate-200",
  indicatorClassName = "stroke-cyan-600",
}: {
  value: number;
  label: string;
  children?: ReactNode;
  className?: string;
  trackClassName?: string;
  indicatorClassName?: string;
}) {
  const percentage = clamp(value);
  return (
    <div
      className={`relative shrink-0 ${className}`}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percentage}
    >
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full" aria-hidden>
        <circle
          cx={50}
          cy={50}
          r={42}
          fill="none"
          strokeWidth={8}
          className={trackClassName}
        />
        <circle
          cx={50}
          cy={50}
          r={42}
          fill="none"
          strokeWidth={8}
          strokeLinecap="round"
          pathLength={100}
          strokeDasharray={100}
          strokeDashoffset={100 - percentage}
          transform="rotate(-90 50 50)"
          className={indicatorClassName}
        />
      </svg>
      <div className="absolute inset-3 flex items-center justify-center rounded-full bg-white shadow-inner">
        {children}
      </div>
    </div>
  );
}
