/**
 * API- und UI-gleiche Level-Werte für Governance Maturity (Readiness, GAI, OAMI).
 * Backend: readiness basic|managed|embedded; GAI/OAMI low|medium|high.
 */

export const READINESS_LEVEL_API_VALUES = ["basic", "managed", "embedded"] as const;
export type ReadinessLevel = (typeof READINESS_LEVEL_API_VALUES)[number];

export const INDEX_LEVEL_API_VALUES = ["low", "medium", "high"] as const;
export type IndexLevel = (typeof INDEX_LEVEL_API_VALUES)[number];

/** Governance-Aktivitätsindex (GAI) – gleiche Skala wie OAMI. */
export type ActivityLevel = IndexLevel;

/** Operativer KI-Monitoring-Index (OAMI) – gleiche Skala wie GAI. */
export type MonitoringLevel = IndexLevel;
