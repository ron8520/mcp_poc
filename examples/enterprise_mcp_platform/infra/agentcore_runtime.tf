resource "aws_bedrockagentcore_agent_runtime" "mcp_server" {
  for_each = local.enabled_mcp_servers

  agent_runtime_name = replace("${var.environment}-${each.key}", "-", "_")
  description        = each.value.description
  role_arn           = aws_iam_role.runtime[each.key].arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = each.value.image_uri
    }
  }

  environment_variables = each.value.environment

  network_configuration {
    network_mode = "VPC"

    network_mode_config {
      subnets         = var.private_subnet_ids
      security_groups = var.runtime_security_group_ids
    }
  }

  protocol_configuration {
    server_protocol = "MCP"
  }

  request_header_configuration {
    request_header_allowlist = local.trusted_request_headers
  }

  tags = local.tags

  depends_on = [
    aws_iam_role_policy.runtime
  ]
}
