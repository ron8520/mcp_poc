data "aws_iam_policy_document" "agentcore_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.target_account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:bedrock-agentcore:${var.region}:${var.target_account_id}:*"]
    }
  }
}

resource "aws_iam_role" "runtime" {
  for_each = local.enabled_mcp_runtime_lanes

  name               = "agentcore_${var.environment}-${each.key}_runtime"
  assume_role_policy = data.aws_iam_policy_document.agentcore_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "runtime_ecr_pull" {
  for_each = local.enabled_mcp_runtime_lanes

  statement {
    sid       = "EcrAuth"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "EcrPullImage"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer"
    ]
    resources = each.value.ecr_repository_arns
  }
}

data "aws_iam_policy_document" "runtime_secrets" {
  for_each = {
    for name, lane in local.enabled_mcp_runtime_lanes : name => lane
    if length(lane.secret_arns) > 0
  }

  statement {
    sid       = "ReadDownstreamIdentitySecret"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = each.value.secret_arns
  }

  dynamic "statement" {
    for_each = length(each.value.secret_kms_key_arns) > 0 ? [1] : []

    content {
      sid       = "DecryptDownstreamIdentitySecret"
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = each.value.secret_kms_key_arns

      condition {
        test     = "StringEquals"
        variable = "kms:ViaService"
        values   = ["secretsmanager.${var.region}.amazonaws.com"]
      }
    }
  }
}

data "aws_iam_policy_document" "runtime_observability" {
  statement {
    sid    = "CloudWatchLogGroups"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:DescribeLogGroups"
    ]
    resources = [
      "arn:aws:logs:${var.region}:${var.target_account_id}:log-group:*"
    ]
  }

  statement {
    sid    = "CloudWatchRuntimeStreams"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:${var.region}:${var.target_account_id}:log-group:/aws/bedrock-agentcore/runtimes/*",
      "arn:aws:logs:${var.region}:${var.target_account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
    ]
  }

  statement {
    sid    = "XRayTelemetry"
    effect = "Allow"
    actions = [
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets",
      "xray:PutTelemetryRecords",
      "xray:PutTraceSegments"
    ]
    resources = ["*"]
  }

  statement {
    sid       = "AgentCoreMetrics"
    effect    = "Allow"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["bedrock-agentcore"]
    }
  }
}

data "aws_iam_policy_document" "runtime" {
  for_each = local.enabled_mcp_runtime_lanes

  source_policy_documents = concat(
    [
      data.aws_iam_policy_document.runtime_ecr_pull[each.key].json,
      data.aws_iam_policy_document.runtime_observability.json
    ],
    length(each.value.secret_arns) > 0 ? [
      data.aws_iam_policy_document.runtime_secrets[each.key].json
    ] : []
  )
}

resource "aws_iam_role_policy" "runtime" {
  for_each = local.enabled_mcp_runtime_lanes

  role   = aws_iam_role.runtime[each.key].id
  policy = data.aws_iam_policy_document.runtime[each.key].json
}

resource "aws_iam_role" "gateway" {
  name               = "agentcore_${local.gateway_name}"
  assume_role_policy = data.aws_iam_policy_document.agentcore_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "gateway_policy_engine" {
  statement {
    sid       = "GetPolicyEngine"
    effect    = "Allow"
    actions   = ["bedrock-agentcore:GetPolicyEngine"]
    resources = [aws_bedrockagentcore_policy_engine.this.policy_engine_arn]
  }

  statement {
    sid    = "AuthorizeGatewayActions"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:AuthorizeAction",
      "bedrock-agentcore:PartiallyAuthorizeActions"
    ]
    resources = [
      aws_bedrockagentcore_policy_engine.this.policy_engine_arn,
      replace(
        aws_bedrockagentcore_policy_engine.this.policy_engine_arn,
        "policy-engine/${aws_bedrockagentcore_policy_engine.this.policy_engine_id}",
        "gateway/*"
      )
    ]
  }
}

resource "aws_iam_role_policy" "gateway_policy_engine" {
  role   = aws_iam_role.gateway.id
  policy = data.aws_iam_policy_document.gateway_policy_engine.json
}

data "aws_iam_policy_document" "gateway_invoke_runtimes" {
  statement {
    sid    = "InvokeRuntimeTargets"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:InvokeAgentRuntime"
    ]
    resources = [
      for runtime in aws_bedrockagentcore_agent_runtime.mcp_server : runtime.agent_runtime_arn
    ]
  }
}

resource "aws_iam_role_policy" "gateway_invoke_runtimes" {
  role   = aws_iam_role.gateway.id
  policy = data.aws_iam_policy_document.gateway_invoke_runtimes.json
}
