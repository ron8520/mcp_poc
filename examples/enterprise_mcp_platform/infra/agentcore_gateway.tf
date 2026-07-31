resource "aws_bedrockagentcore_policy_engine" "this" {
  name        = replace(local.gateway_name, "-", "_")
  description = "Policy engine for ${local.gateway_name}"
  tags        = local.tags
}

resource "aws_bedrockagentcore_gateway" "this" {
  name        = local.gateway_name
  description = "Enterprise AgentCore Gateway for ${var.environment} internal MCP servers"
  role_arn    = aws_iam_role.gateway.arn

  authorizer_type = "CUSTOM_JWT"
  authorizer_configuration {
    custom_jwt_authorizer {
      discovery_url    = var.entra_discovery_url
      allowed_audience = var.entra_allowed_audience
      allowed_clients  = var.entra_allowed_clients
      allowed_scopes   = var.gateway_app_only_ingress_enabled ? null : ["mcp.invoke"]
    }
  }

  protocol_type = "MCP"

  interceptor_configuration {
    interception_points = ["REQUEST"]

    interceptor {
      lambda {
        arn = aws_lambda_function.gateway_obo_assertion.arn
      }
    }

    input_configuration {
      pass_request_headers = true
    }
  }

  policy_engine_configuration {
    arn  = aws_bedrockagentcore_policy_engine.this.policy_engine_arn
    mode = var.gateway_policy_mode
  }

  protocol_configuration {
    mcp {
      instructions       = "Enterprise AgentCore Gateway for MCP"
      search_type        = "SEMANTIC"
      supported_versions = ["2025-03-26", "2025-06-18"]
    }
  }

  tags = local.tags

  lifecycle {
    precondition {
      condition     = !var.gateway_app_only_ingress_enabled || var.gateway_policy_mode == "ENFORCE"
      error_message = "App-only Gateway ingress can be enabled only when Cedar is in ENFORCE mode."
    }
  }

  depends_on = [
    aws_iam_role_policy.gateway_interceptor,
    aws_iam_role_policy.gateway_policy_engine
  ]
}

resource "aws_bedrockagentcore_gateway_target" "runtime_mcp" {
  for_each = local.enabled_mcp_runtime_lanes

  name               = each.key
  gateway_identifier = aws_bedrockagentcore_gateway.this.gateway_id
  description        = each.value.description

  credential_provider_configuration {
    gateway_iam_role {
      service = "bedrock-agentcore"
      region  = var.region
    }
  }

  target_configuration {
    mcp {
      mcp_server {
        endpoint = "https://bedrock-agentcore.${var.region}.amazonaws.com/runtimes/${urlencode(aws_bedrockagentcore_agent_runtime.mcp_server[each.key].agent_runtime_arn)}/invocations?qualifier=DEFAULT"
      }
    }
  }

  metadata_configuration {
    allowed_request_headers = concat(
      local.base_request_headers,
      each.value.obo_assertion_required ? [local.obo_assertion_header] : []
    )
  }

  depends_on = [
    aws_iam_role_policy.gateway_invoke_runtimes
  ]
}

resource "aws_bedrockagentcore_policy" "cedar" {
  for_each = local.cedar_policy_files

  name             = replace(trimsuffix(each.value, ".cedar"), "-", "_")
  policy_engine_id = aws_bedrockagentcore_policy_engine.this.policy_engine_id
  description      = "Direct Cedar policy from ${each.value}"
  validation_mode  = "FAIL_ON_ANY_FINDINGS"

  definition {
    cedar {
      statement = replace(
        file("${path.module}/../policy/cedar/${each.value}"),
        "__GATEWAY_ARN__",
        aws_bedrockagentcore_gateway.this.gateway_arn
      )
    }
  }

  depends_on = [
    aws_bedrockagentcore_gateway_target.runtime_mcp
  ]
}

data "aws_iam_policy_document" "runtime_only_from_gateway" {
  for_each = local.enabled_mcp_runtime_lanes

  statement {
    sid    = "AllowOnlyGatewayRole"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:InvokeAgentRuntime"
    ]
    resources = [
      aws_bedrockagentcore_agent_runtime.mcp_server[each.key].agent_runtime_arn
    ]

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.gateway.arn]
    }
  }
}

resource "aws_bedrockagentcore_resource_policy" "runtime_only_from_gateway" {
  for_each = local.enabled_mcp_runtime_lanes

  resource_arn = aws_bedrockagentcore_agent_runtime.mcp_server[each.key].agent_runtime_arn
  policy       = data.aws_iam_policy_document.runtime_only_from_gateway[each.key].json
}
