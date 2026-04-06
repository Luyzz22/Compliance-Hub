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

test_advisor_rag_eu_ai_act_nis2_query_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "advisor",
		"action": "advisor_rag_eu_ai_act_nis2_query",
		"risk_score": 0.5,
	}
}

test_compliance_officer_view_ai_evidence_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "compliance_officer",
		"action": "view_ai_evidence",
		"risk_score": 0.3,
	}
}

test_auditor_view_ai_evidence_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "auditor",
		"action": "view_ai_evidence",
		"risk_score": 0.3,
	}
}

test_tenant_admin_view_ai_evidence_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "tenant_admin",
		"action": "view_ai_evidence",
		"risk_score": 0.3,
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

# ── Enterprise RBAC role tests ─────────────────────────────────────────

test_ciso_generate_board_report_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "ciso",
		"action": "generate_board_report",
		"risk_score": 0.5,
	}
}

test_ciso_manage_incidents_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "ciso",
		"action": "manage_incidents",
		"risk_score": 0.5,
	}
}

test_board_member_view_board_report_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "board_member",
		"action": "view_board_report",
		"risk_score": 0.3,
	}
}

test_board_member_edit_denied {
	not compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "board_member",
		"action": "edit_ai_system",
		"risk_score": 0.3,
	}
}

test_editor_edit_ai_system_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "editor",
		"action": "edit_ai_system",
		"risk_score": 0.3,
	}
}

test_editor_edit_compliance_status_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "editor",
		"action": "edit_compliance_status",
		"risk_score": 0.3,
	}
}

test_contributor_view_ai_systems_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "contributor",
		"action": "view_ai_systems",
		"risk_score": 0.3,
	}
}

test_contributor_view_risk_register_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "contributor",
		"action": "view_risk_register",
		"risk_score": 0.3,
	}
}

test_super_admin_any_action_allowed {
	compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "super_admin",
		"action": "some_arbitrary_action",
		"risk_score": 0.9,
	}
}

test_super_admin_denied_on_denylist {
	not compliancehub.allow_action with input as {
		"tenant_id": "t1",
		"user_role": "super_admin",
		"action": "auto_delete_data",
		"risk_score": 0.1,
	}
}
