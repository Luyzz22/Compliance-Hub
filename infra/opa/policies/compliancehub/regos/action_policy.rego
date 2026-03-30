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
