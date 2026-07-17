locals {
  enabled_mcp_servers = {
    for name, config in var.mcp_servers : name => config
    if config.enabled
  }

  gateway_name = "${var.environment}-${var.gateway_name}"

  tags = merge(
    {
      application = "enterprise-mcp"
      environment = var.environment
      managed_by  = "terraform"
    },
    var.tags
  )

  trusted_request_headers = [
    "x-correlation-id",
    "x-mcp-subject",
    "x-mcp-client-id",
    "x-mcp-groups",
    "x-mcp-app-roles"
  ]
}
