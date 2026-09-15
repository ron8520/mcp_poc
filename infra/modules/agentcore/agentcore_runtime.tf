resource "aws_bedrockagentcore_agent_runtime" "mcp_server" {
  for_each = local.enabled_mcp_runtime_lanes

  agent_runtime_name = replace("${var.environment}-${each.key}", "-", "_")
  description        = each.value.description
  role_arn           = aws_iam_role.runtime[each.key].arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = each.value.image_uri
    }
  }

  environment_variables = merge(each.value.environment,
    each.key == local.app_only_target && local.app_only_enabled ? {
      GRAPH_AUTH_MODE         = "agentcore_m2m"
      APP_ONLY_MAPPING_JSON   = local.app_only_mapping_json
      MCP_ENVIRONMENT         = var.environment
      AGENTCORE_WORKLOAD_NAME = aws_bedrockagentcore_workload_identity.sharepoint_application[0].name
    } : {}
  )

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
    request_header_allowlist = concat(
      local.base_request_headers,
      each.value.obo_assertion_required ? [local.obo_assertion_header] : [],
      each.key == local.app_only_target && local.app_only_enabled ? [local.app_only_header] : []
    )
  }

  tags = local.tags

  depends_on = [
    aws_iam_role_policy.runtime,
    aws_iam_role_policy.runtime_app_only_identity
  ]
}
