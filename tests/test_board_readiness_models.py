"""Sanity checks for board readiness DTOs (Wave 34)."""

from __future__ import annotations

from app.board_readiness_models import (
    BoardAttentionItem,
    BoardReadinessPillarBlock,
    BoardReadinessPillarKey,
    BoardReadinessSubIndicator,
    BoardReadinessTraffic,
)


def test_board_readiness_pillar_roundtrip() -> None:
    b = BoardReadinessPillarBlock(
        pillar=BoardReadinessPillarKey.eu_ai_act,
        title_de="EU AI Act",
        summary_de="Test",
        status=BoardReadinessTraffic.amber,
        indicators=[
            BoardReadinessSubIndicator(
                key="k",
                label_de="L",
                value_percent=50.0,
                value_count=1,
                value_denominator=2,
                status=BoardReadinessTraffic.amber,
                source_api_paths=["/api/v1/example"],
            ),
        ],
    )
    assert b.pillar == BoardReadinessPillarKey.eu_ai_act
    assert b.indicators[0].value_percent == 50.0


def test_board_attention_item() -> None:
    a = BoardAttentionItem(
        id="x",
        severity=BoardReadinessTraffic.red,
        tenant_id="t1",
        subject_type="ai_system",
        subject_id="s1",
        missing_artefact_de="Fehlt",
        deep_links={"workspace_path": "/tenant/ai-systems/s1"},
    )
    assert a.deep_links["workspace_path"].endswith("s1")
