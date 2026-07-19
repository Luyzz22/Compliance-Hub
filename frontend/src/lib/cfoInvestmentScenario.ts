import type {
  EnterpriseInvestmentInitiativeDto,
  InvestmentDecisionDto,
} from "@/lib/api";

export type CfoScenarioId =
  | "balanced"
  | "capital_discipline"
  | "risk_containment"
  | "acceleration";

export type CfoScenario = {
  id: CfoScenarioId;
  label: string;
  description: string;
  weights: {
    strategicValue: number;
    riskReduction: number;
    executionConfidence: number;
    capitalEfficiency: number;
  };
};

export type ScenarioRankedInitiative = EnterpriseInvestmentInitiativeDto & {
  scenario_rank: number;
  scenario_score: number;
  scenario_decision: InvestmentDecisionDto;
};

export const CFO_SCENARIOS: readonly CfoScenario[] = [
  {
    id: "balanced",
    label: "Ausgewogen",
    description: "Baseline für Wert, Risiko, Ausführung und Kapitaleffizienz.",
    weights: {
      strategicValue: 30,
      riskReduction: 30,
      executionConfidence: 25,
      capitalEfficiency: 15,
    },
  },
  {
    id: "capital_discipline",
    label: "Kapitaldisziplin",
    description: "Bevorzugt fokussierte Vorhaben mit hoher relativer Kapitaleffizienz.",
    weights: {
      strategicValue: 20,
      riskReduction: 20,
      executionConfidence: 20,
      capitalEfficiency: 40,
    },
  },
  {
    id: "risk_containment",
    label: "Risikobegrenzung",
    description: "Priorisiert die stärkste Compliance- und Risikowirkung.",
    weights: {
      strategicValue: 20,
      riskReduction: 45,
      executionConfidence: 20,
      capitalEfficiency: 15,
    },
  },
  {
    id: "acceleration",
    label: "Beschleunigung",
    description: "Gewichtet strategischen Wert und sichere Lieferfähigkeit höher.",
    weights: {
      strategicValue: 45,
      riskReduction: 20,
      executionConfidence: 25,
      capitalEfficiency: 10,
    },
  },
] as const;

export function getCfoScenario(scenarioId: CfoScenarioId): CfoScenario {
  return CFO_SCENARIOS.find((scenario) => scenario.id === scenarioId) ?? CFO_SCENARIOS[0];
}

export function rankInvestmentInitiatives(
  initiatives: EnterpriseInvestmentInitiativeDto[],
  scenarioId: CfoScenarioId,
): ScenarioRankedInitiative[] {
  const scenario = getCfoScenario(scenarioId);
  const ranked = initiatives.map((initiative) => {
    const scenarioScore = clamp(
      Math.round(
        (initiative.strategic_value_score * scenario.weights.strategicValue +
          initiative.risk_reduction_score * scenario.weights.riskReduction +
          initiative.execution_confidence_score * scenario.weights.executionConfidence +
          initiative.capital_efficiency_score * scenario.weights.capitalEfficiency) /
          100,
      ),
    );
    return {
      ...initiative,
      scenario_rank: 1,
      scenario_score: scenarioScore,
      scenario_decision: scenarioDecision(initiative, scenarioScore),
    };
  });

  ranked.sort(
    (left, right) =>
      right.scenario_score - left.scenario_score ||
      left.blocker_score - right.blocker_score ||
      left.initiative_id.localeCompare(right.initiative_id),
  );

  return ranked.map((initiative, index) => ({
    ...initiative,
    scenario_rank: index + 1,
  }));
}

function scenarioDecision(
  initiative: EnterpriseInvestmentInitiativeDto,
  scenarioScore: number,
): InvestmentDecisionDto {
  if (initiative.recommended_decision === "hold" || initiative.blocker_score >= 70) {
    return "hold";
  }
  if (initiative.execution_confidence_score < 55) {
    return "validate";
  }
  if (
    scenarioScore >= 72 &&
    initiative.blocker_score <= 35 &&
    initiative.investment_envelope_band !== "large"
  ) {
    return "fund_now";
  }
  if (scenarioScore >= 60) {
    return "sequence";
  }
  return "validate";
}

function clamp(value: number): number {
  return Math.max(0, Math.min(100, value));
}
