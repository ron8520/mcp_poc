permit (
    principal is AgentCore::OAuthUser,
    action == AgentCore::Action::"crm-application___crm_update_case_summary",
    resource == AgentCore::Gateway::"__GATEWAY_ARN__"
)
when {
    principal.hasTag("roles") &&
    principal.getTag("roles") like "*\"MCP.CRM.Case.Summary.Update\"*"
};
