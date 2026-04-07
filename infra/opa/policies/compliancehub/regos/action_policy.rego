# ComplianceHub Wave 1 — action allow/deny (OPA).
# Compatible with common OPA 0.5x/1.x bundles.
# Query: POST /v1/data/compliancehub/allow_action  body: {"input": {...}}

package compliancehub

default allow_action = false

# Global denylist (mirror in policy docs): auto_delete_data, auto_approve_dsar

denylisted {
	input.action == "auto_delete_data"
}

denylisted {
	input.action == "auto_approve_dsar"
}

allow_action {
	not denylisted
	input.risk_score < 0.8
	input.user_role == "advisor"
	input.action == "generate_board_report"
}

allow_action {
	not denylisted
	input.risk_score < 0.8
	input.user_role == "advisor"
	input.action == "advisor_tenant_report"
}

allow_action {
	not denylisted
	input.risk_score < 0.8
	input.user_role == "tenant_admin"
	input.action == "generate_board_report"
}

allow_action {
	not denylisted
	input.risk_score < 0.8
	input.user_role == "tenant_user"
	input.action == "call_llm_explain_readiness"
}

allow_action {
	not denylisted
	input.risk_score < 0.8
	input.user_role == "tenant_admin"
	input.action == "call_langgraph_oami_explain"
}

allow_action {
	not denylisted
	input.risk_score < 0.8
	input.user_role == "tenant_admin"
	input.action == "start_board_report_workflow"
}

allow_action {
	not denylisted
	input.risk_score < 0.8
	input.user_role == "advisor"
	input.action == "start_board_report_workflow"
}

allow_action {
	not denylisted
	input.risk_score < 0.8
	input.user_role == "advisor"
	input.action == "advisor_rag_eu_ai_act_nis2_query"
}

allow_action {
	not denylisted
	input.risk_score < 0.85
	input.user_role == "compliance_officer"
	input.action == "view_ai_evidence"
}

allow_action {
	not denylisted
	input.risk_score < 0.85
	input.user_role == "auditor"
	input.action == "view_ai_evidence"
}

allow_action {
	not denylisted
	input.risk_score < 0.85
	input.user_role == "tenant_admin"
	input.action == "view_ai_evidence"
}

# ── Enterprise RBAC roles ──────────────────────────────────────────────

# CISO — all compliance_officer + board reporting
allow_action {
	not denylisted
	input.user_role == "ciso"
	input.action == "generate_board_report"
}

allow_action {
	not denylisted
	input.user_role == "ciso"
	input.action == "manage_incidents"
}

# Board member — restricted to board views
allow_action {
	not denylisted
	input.user_role == "board_member"
	input.action == "view_board_report"
}

# Editor — editing AI systems and compliance data
allow_action {
	not denylisted
	input.user_role == "editor"
	input.action == "edit_ai_system"
}

allow_action {
	not denylisted
	input.user_role == "editor"
	input.action == "edit_compliance_status"
}

# Contributor — read access to most data
allow_action {
	not denylisted
	input.user_role == "contributor"
	input.action == "view_ai_systems"
}

allow_action {
	not denylisted
	input.user_role == "contributor"
	input.action == "view_risk_register"
}

# Super Admin — all actions
allow_action {
	not denylisted
	input.user_role == "super_admin"
}
