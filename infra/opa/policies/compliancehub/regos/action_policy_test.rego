# OPA unit tests: `opa test infra/opa/policies/compliancehub/regos/`

package compliancehub_test

import data.compliancehub

test_tenant_admin_board_report_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "tenant_admin",
		"action": "generate_board_report",
		"risk_score": 0.5,
	}
}

test_advisor_board_report_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "advisor",
		"action": "generate_board_report",
		"risk_score": 0.5,
	}
}

test_tenant_user_readiness_explain_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "tenant_user",
		"action": "call_llm_explain_readiness",
		"risk_score": 0.2,
	}
}

test_tenant_admin_langgraph_oami_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "tenant_admin",
		"action": "call_langgraph_oami_explain",
		"risk_score": 0.4,
	}
}

test_tenant_admin_start_board_report_workflow_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "tenant_admin",
		"action": "start_board_report_workflow",
		"risk_score": 0.5,
	}
}

test_advisor_start_board_report_workflow_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "advisor",
		"action": "start_board_report_workflow",
		"risk_score": 0.5,
	}
}

test_advisor_tenant_report_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "advisor",
		"action": "advisor_tenant_report",
		"risk_score": 0.5,
	}
}

test_auto_delete_data_denied {
	not compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "tenant_admin",
		"action": "auto_delete_data",
		"risk_score": 0.1,
	}
}

test_high_risk_score_denied {
	not compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "tenant_admin",
		"action": "generate_board_report",
		"risk_score": 0.85,
	}
}

test_viewer_readiness_denied {
	not compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "viewer",
		"action": "call_llm_explain_readiness",
		"risk_score": 0.1,
	}
}
