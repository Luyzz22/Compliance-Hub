"""Heuristic confidence for regulatory RAG (BM25 or hybrid combined scores; advisory, not legal certainty)."""

from __future__ import annotations

from typing import Literal

ConfidenceLevel = Literal["high", "medium", "low"]


def compute_confidence_level(
    scores: list[float],
    *,
    min_score_for_answer: float,
    high_score_min: float,
    score_gap_min: float,
) -> tuple[ConfidenceLevel, str | None]:
    """
    Derive a coarse confidence label from retrieval scores.

    - ``high``: strong top score and clear separation from the runner-up.
    - ``medium``: usable hit but ambiguous ranking or moderate scores.
    - ``low``: weak or no evidence; caller may skip LLM or attach ``notes_de``.
    """
    if not scores:
        return "low", (
            "Keine ausreichenden Treffer in der Wissensbasis. "
            "Bitte inhaltlich durch eine Fachperson prüfen lassen."
        )
    s_desc = sorted(scores, reverse=True)
    best = s_desc[0]
    second = s_desc[1] if len(s_desc) > 1 else 0.0
    if best < min_score_for_answer:
        return "low", (
            "Für diese Frage liegen uns in der EU-AI-Act/NIS2-Wissensbasis aktuell keine "
            "eindeutigen Textstellen vor. Bitte ziehen Sie bei Bedarf eine menschliche "
            "Fachexpertin bzw. einen Fachexperten hinzu."
        )
    if best >= high_score_min and (len(s_desc) == 1 or (best - second) >= score_gap_min):
        return "high", None
    return "medium", (
        "Mehrere mögliche Textstellen oder mittlere Treffersicherheit — bitte Fundstellen "
        "sorgfältig gegenprüfen."
    )
