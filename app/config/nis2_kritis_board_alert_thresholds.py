"""Nachvollziehbare Schwellen für NIS2-/KRITIS-KPI-basierte Board-Alerts."""

from __future__ import annotations

# Mittelwert je KPI-Typ (0–100) über alle gespeicherten Werte des Tenants
NIS2_KRITIS_INCIDENT_MATURITY_MEAN_ALERT_PCT = 50
NIS2_KRITIS_SUPPLIER_COVERAGE_MEAN_ALERT_PCT = 50

# Voller KPI-Datensatz je System (alle drei Typen) – Ratio 0–1 aus Board-KPIs
NIS2_KRITIS_FULL_COVERAGE_RATIO_ALERT = 0.5

# OT/IT-Segmentierung: High-Risk-/Fokus-Systeme unter diesem Wert zählen für „viele“-Alert
NIS2_KRITIS_OT_IT_ALERT_THRESHOLD_PCT = 60
NIS2_KRITIS_OT_IT_ALERT_MIN_AFFECTED_SYSTEMS = 2
