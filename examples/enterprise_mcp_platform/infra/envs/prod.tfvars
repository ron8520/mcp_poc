environment = "prod"
region      = "us-west-2"

gateway_policy_mode = "LOG_ONLY"

entra_discovery_url    = "https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration"
entra_allowed_audience = ["api://enterprise-mcp-prod"]
entra_allowed_clients = [
  "<claude-code-prod-entra-client-id>",
  "<people-assist-prod-entra-client-id>"
]

private_subnet_ids                  = ["subnet-prod-runtime-a", "subnet-prod-runtime-b"]
runtime_security_group_ids          = ["sg-prod-runtime-egress"]
client_vpc_id                       = "vpc-prod-client-network"
gateway_endpoint_subnet_ids         = ["subnet-prod-endpoint-a", "subnet-prod-endpoint-b"]
gateway_endpoint_security_group_ids = ["sg-prod-agentcore-gateway-endpoint"]

mcp_servers = {
  sharepoint-mcp = {
    enabled             = true
    description         = "SharePoint MCP server"
    image_uri           = "111122223333.dkr.ecr.us-west-2.amazonaws.com/internal/sharepoint-mcp:prod"
    ecr_repository_arns = ["arn:aws:ecr:us-west-2:111122223333:repository/internal/sharepoint-mcp"]
    environment = {
      GRAPH_DRY_RUN    = "false"
      MCP_POLICY_PATH  = "/app/policy/generated/tool_allowlist.json"
      MCP_SERVER_NAME  = "sharepoint-mcp"
      MCP_SERVER_OWNER = "enterprise-mcp-platform"
    }
  }
}
