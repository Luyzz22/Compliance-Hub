import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  HorizontalMetricBar,
  MetricRing,
  SegmentedMetricBar,
  VerticalMetricBar,
} from "@/components/visualization/StrictCspMetrics";

describe("strict CSP metric visualizations", () => {
  it("encode dynamic geometry as SVG attributes without inline styles", () => {
    const { container } = render(
      <div>
        <HorizontalMetricBar value={64} label="Readiness" />
        <SegmentedMetricBar
          label="Coverage"
          max={100}
          segments={[
            { label: "Covered", value: 60, className: "fill-emerald-500" },
            { label: "Partial", value: 25, className: "fill-amber-400" },
          ]}
        />
        <VerticalMetricBar value={72} label="Incidents" />
        <MetricRing value={68} label="EU AI Act readiness">
          68%
        </MetricRing>
      </div>,
    );

    expect(container.querySelectorAll("[style]")).toHaveLength(0);
    expect(container.querySelector('rect[width="64"]')).not.toBeNull();
    expect(container.querySelector('rect[height="72"]')).not.toBeNull();
    expect(container.querySelector('circle[stroke-dashoffset="32"]')).not.toBeNull();
  });
});
