// Application permission calls use a dedicated Graph application identity.
// SharePoint site access is enforced by explicit Sites.Selected grants.

permit (
    principal is AgentCore::OAuthUser,
    action in [
        AgentCore::Action::"sharepoint-application___sharepoint_list_site_content",
        AgentCore::Action::"sharepoint-application___sharepoint_get_file_text"
    ],
    resource == AgentCore::Gateway::"__GATEWAY_ARN__"
)
when {
    principal.hasTag("roles") &&
    principal.getTag("roles") like "*\"MCP.SharePoint.Application.Read\"*"
};

permit (
    principal is AgentCore::OAuthUser,
    action == AgentCore::Action::"sharepoint-application___sharepoint_upload_file",
    resource == AgentCore::Gateway::"__GATEWAY_ARN__"
)
when {
    principal.hasTag("roles") &&
    principal.getTag("roles") like "*\"MCP.SharePoint.Application.Upload\"*"
};
