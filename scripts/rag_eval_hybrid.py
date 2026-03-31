#!/usr/bin/env python3
"""Offline evaluation: BM25 vs. hybrid retrieval on synthetic compliance queries.

Usage:
    python scripts/rag_eval_hybrid.py
    python scripts/rag_eval_hybrid.py --alpha 0.3
    python scripts/rag_eval_hybrid.py --alphas 0.2,0.3,0.35
    python scripts/rag_eval_hybrid.py --output results.json --csv summary.csv
    python scripts/rag_eval_hybrid.py --evidence-jsonl /path/to/rag_events.jsonl

Reads ground truth from data/eval/ground_truth.yaml (curated synthetic queries, no PII).
Optional ``--evidence-jsonl`` loads metadata-only rows (e.g. ``query_sha256``) for alignment
with production logging — never raw customer text.

Outputs per-query rows, CSV/JSON summary, and ``fusion_winner`` (BM25 vs best hybrid).
No LLM calls.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag.config import RAGConfig
from app.services.rag.corpus import Document
from app.services.rag.hybrid_retriever import HybridRetriever


def load_evidence_sample(path: str | Path, limit: int = 50) -> list[dict[str, Any]]:
    """Load recent RAG evidence rows (JSONL).

    Expects metadata only (e.g. query_sha256), no raw prompts.
    """
    p = Path(path)
    rows: list[dict[str, Any]] = []
    if not p.is_file():
        return rows
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(rows) >= limit:
                break
    return rows


def load_ground_truth(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def build_corpus(gt_data: dict[str, Any]) -> list[Document]:
    docs = []
    for entry in gt_data.get("corpus", []):
        docs.append(
            Document(
                doc_id=entry["doc_id"],
                title=entry["title"],
                content=entry["content"],
                source=entry.get("source", ""),
                section=entry.get("section", ""),
            )
        )
    return docs


def recall_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    retrieved_set = set(retrieved_ids[:k])
    expected_set = set(expected_ids)
    if not expected_set:
        return 0.0
    return len(retrieved_set & expected_set) / len(expected_set)


def precision_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    retrieved_top = retrieved_ids[:k]
    if not retrieved_top:
        return 0.0
    expected_set = set(expected_ids)
    hits = sum(1 for doc_id in retrieved_top if doc_id in expected_set)
    return hits / len(retrieved_top)


def dcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        rel = 1.0 if doc_id in relevant_ids else 0.0
        dcg += rel / math.log2(i + 2)
    return dcg


def ndcg_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    relevant = set(expected_ids)
    actual_dcg = dcg_at_k(retrieved_ids, relevant, k)
    ideal_ids = [d for d in retrieved_ids[:k] if d in relevant]
    ideal_ids += [d for d in expected_ids if d not in set(ideal_ids)]
    ideal_dcg = dcg_at_k(ideal_ids, relevant, k)
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def evaluate_single_query(
    retriever: HybridRetriever,
    query_entry: dict[str, Any],
    mode: str,
    alpha: float,
    k: int,
) -> dict[str, Any]:
    query_text = query_entry["query"]
    expected = query_entry.get("expected_doc_ids", [])
    good = query_entry.get("good_doc_ids", [])
    bad = query_entry.get("bad_doc_ids", [])

    response = retriever.retrieve(query_text, k=k, alpha=alpha, mode=mode)
    retrieved_ids = [r.doc.doc_id for r in response.results]
    bad_set = set(bad)
    bad_in_topk = sum(1 for doc_id in retrieved_ids[:k] if doc_id in bad_set) if bad else None

    return {
        "query_id": query_entry["query_id"],
        "category": query_entry.get("category", ""),
        "mode": mode,
        "alpha": alpha,
        "recall_at_k": round(recall_at_k(retrieved_ids, expected, k), 4),
        "precision_at_k": round(precision_at_k(retrieved_ids, expected, k), 4),
        "ndcg_at_k": round(ndcg_at_k(retrieved_ids, expected, k), 4),
        "recall_good": round(recall_at_k(retrieved_ids, good, k), 4) if good else None,
        "bad_docs_in_topk": bad_in_topk,
        "retrieved_ids": retrieved_ids,
        "confidence_level": response.confidence_level,
        "confidence_score": response.confidence_score,
        "top_score": response.results[0].score if response.results else 0.0,
    }


def run_evaluation(
    gt_path: str | Path,
    alphas: list[float] | None = None,
    k: int = 5,
) -> dict[str, Any]:
    gt_data = load_ground_truth(gt_path)
    corpus = build_corpus(gt_data)
    queries = gt_data.get("queries", [])

    config = RAGConfig(retrieval_mode="bm25")
    retriever = HybridRetriever(corpus, config)

    if alphas is None:
        alphas = RAGConfig().alpha_grid

    all_results: list[dict[str, Any]] = []

    for query_entry in queries:
        bm25_result = evaluate_single_query(retriever, query_entry, "bm25", 0.0, k)
        all_results.append(bm25_result)

    for alpha in alphas:
        if alpha == 0.0:
            continue
        hybrid_config = RAGConfig(retrieval_mode="hybrid", hybrid_alpha=alpha)
        hybrid_retriever = HybridRetriever(corpus, hybrid_config)
        for query_entry in queries:
            hybrid_result = evaluate_single_query(hybrid_retriever, query_entry, "hybrid", alpha, k)
            all_results.append(hybrid_result)

    summary = _aggregate_results(all_results, alphas)
    fusion_winner = _fusion_winner(summary)

    out: dict[str, Any] = {
        "per_query": all_results,
        "summary": summary,
        "fusion_winner": fusion_winner,
        "config": {
            "k": k,
            "alphas": alphas,
            "corpus_size": len(corpus),
            "query_count": len(queries),
        },
    }
    return out


def _fusion_winner(summary: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare BM25-only vs hybrid aggregate rows (Recall+Precision+NDCG composite)."""
    bm25 = next((s for s in summary if s.get("mode") == "bm25"), None)
    hybrids = [s for s in summary if s.get("mode") == "hybrid"]

    def composite(row: dict[str, Any]) -> float:
        return (
            row.get("avg_recall_at_k", 0.0)
            + row.get("avg_precision_at_k", 0.0)
            + row.get("avg_ndcg_at_k", 0.0)
        )

    if not bm25:
        return {"winner": "unknown", "detail": "no_bm25_summary"}
    sb = composite(bm25)
    if not hybrids:
        return {"winner": "bm25", "detail": "no_hybrid_runs", "bm25_composite": round(sb, 4)}
    best_h = max(hybrids, key=composite)
    sh = composite(best_h)
    if sh > sb + 1e-9:
        return {
            "winner": "hybrid",
            "best_alpha": best_h.get("alpha"),
            "best_setting": best_h.get("setting"),
            "bm25_composite": round(sb, 4),
            "hybrid_composite": round(sh, 4),
        }
    if sb > sh + 1e-9:
        return {
            "winner": "bm25",
            "bm25_composite": round(sb, 4),
            "best_hybrid_composite": round(sh, 4),
        }
    return {
        "winner": "tie",
        "bm25_composite": round(sb, 4),
        "hybrid_composite": round(sh, 4),
    }


def _aggregate_results(
    results: list[dict[str, Any]], alphas: list[float] | None
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        key = f"{r['mode']}_alpha{r['alpha']}"
        groups.setdefault(key, []).append(r)

    summary = []
    for key, group in sorted(groups.items()):
        n = len(group)
        avg_recall = sum(r["recall_at_k"] for r in group) / n
        avg_precision = sum(r["precision_at_k"] for r in group) / n
        avg_ndcg = sum(r["ndcg_at_k"] for r in group) / n
        avg_confidence = sum(r["confidence_score"] for r in group) / n

        summary.append(
            {
                "setting": key,
                "mode": group[0]["mode"],
                "alpha": group[0]["alpha"],
                "num_queries": n,
                "avg_recall_at_k": round(avg_recall, 4),
                "avg_precision_at_k": round(avg_precision, 4),
                "avg_ndcg_at_k": round(avg_ndcg, 4),
                "avg_confidence_score": round(avg_confidence, 4),
            }
        )

    return summary


def write_csv(results: dict[str, Any], path: str | Path) -> None:
    summary = results["summary"]
    if not summary:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG hybrid retrieval evaluation")
    parser.add_argument(
        "--gt-path",
        default="data/eval/ground_truth.yaml",
        help="Path to ground truth YAML",
    )
    parser.add_argument("--alpha", type=float, default=None, help="Single alpha to test")
    parser.add_argument("--k", type=int, default=5, help="Top-k for metrics")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    parser.add_argument("--csv", default=None, help="Output CSV summary path")
    parser.add_argument(
        "--alphas",
        default=None,
        help="Comma-separated hybrid alphas (default: RAGConfig alpha_grid)",
    )
    parser.add_argument(
        "--evidence-jsonl",
        default=None,
        help="Optional JSONL of metadata-only RAG events (hashed queries) for alignment checks",
    )
    args = parser.parse_args()

    if args.alpha is not None and args.alphas is not None:
        raise SystemExit("Use either --alpha or --alphas, not both")

    alphas: list[float] | None
    if args.alpha is not None:
        alphas = [args.alpha]
    elif args.alphas is not None:
        alphas = [float(x.strip()) for x in args.alphas.split(",") if x.strip()]
    else:
        alphas = None

    results = run_evaluation(args.gt_path, alphas=alphas, k=args.k)

    if args.evidence_jsonl:
        ev = load_evidence_sample(args.evidence_jsonl)
        modes = sorted({r.get("retrieval_mode") for r in ev if isinstance(r, dict)})
        results["evidence_sample"] = {"count": len(ev), "retrieval_modes": modes}

    print("\n=== Evaluation Summary ===\n")
    for entry in results["summary"]:
        print(
            f"  {entry['setting']:30s}  "
            f"Recall@{args.k}={entry['avg_recall_at_k']:.3f}  "
            f"Prec@{args.k}={entry['avg_precision_at_k']:.3f}  "
            f"NDCG@{args.k}={entry['avg_ndcg_at_k']:.3f}  "
            f"Conf={entry['avg_confidence_score']:.3f}"
        )

    best = max(results["summary"], key=lambda s: s["avg_ndcg_at_k"])
    print(f"\n  Best setting: {best['setting']} (NDCG@{args.k}={best['avg_ndcg_at_k']:.3f})\n")

    fw = results.get("fusion_winner") or {}
    print("  Fusion winner (composite recall+precision+NDCG): ", fw.get("winner"), fw, "\n")

    if args.output:
        serializable = {k: v for k, v in results.items()}
        with open(args.output, "w") as f:
            json.dump(serializable, f, indent=2, default=str)
        print(f"  Results written to {args.output}")

    if args.csv:
        write_csv(results, args.csv)
        print(f"  CSV summary written to {args.csv}")


if __name__ == "__main__":
    main()
