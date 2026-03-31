"""RAG pipeline for ComplianceHub advisor queries.

Supports BM25 in-memory retrieval and optional hybrid (BM25 + dense) mode
with configurable score fusion for EU AI Act / ISO 42001 / NIS2 guidance.
"""
