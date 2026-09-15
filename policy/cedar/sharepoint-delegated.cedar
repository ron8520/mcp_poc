// Delegated permission calls use Graph OBO. SharePoint enforces the signed-in
// user's native site and item permissions.

permit (
    principal is AgentCore::OAuthUser,
    action in [
        AgentCore::Action::"sharepoint-delegated___sharepoint_list_site_content",
        AgentCore::Action::"sharepoint-delegated___sharepoint_get_file_text"
    ],
    resource == AgentCore::Gateway::"__GATEWAY_ARN__"
)
when {
    principal.hasTag("scp") &&
    (
        principal.getTag("scp") == "mcp.invoke" ||
        principal.getTag("scp") like "mcp.invoke *" ||
        principal.getTag("scp") like "* mcp.invoke" ||
        principal.getTag("scp") like "* mcp.invoke *"
    ) &&
    principal.hasTag("roles") &&
    principal.getTag("roles") like "*\"MCP.SharePoint.Delegated.Read\"*"
};

permit (
    principal is AgentCore::OAuthUser,
    action == AgentCore::Action::"sharepoint-delegated___sharepoint_upload_file",
    resource == AgentCore::Gateway::"__GATEWAY_ARN__"
)
when {
    principal.hasTag("scp") &&
    (
        principal.getTag("scp") == "mcp.invoke" ||
        principal.getTag("scp") like "mcp.invoke *" ||
        principal.getTag("scp") like "* mcp.invoke" ||
        principal.getTag("scp") like "* mcp.invoke *"
    ) &&
    principal.hasTag("roles") &&
    principal.getTag("roles") like "*\"MCP.SharePoint.Delegated.Upload\"*"
};
