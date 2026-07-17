data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

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
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:bedrock-agentcore:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"]
    }
  }
}

resource "aws_iam_role" "runtime" {
  for_each = local.enabled_mcp_servers

  name               = "agentcore_${var.environment}-${each.key}_runtime"
  assume_role_policy = data.aws_iam_policy_document.agentcore_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "runtime_ecr_pull" {
  for_each = local.enabled_mcp_servers

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

data "aws_iam_policy_document" "runtime_observability" {
  statement {
    sid    = "CloudWatchLogGroups"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:DescribeLogGroups"
    ]
    resources = [
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:*"
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
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock-agentcore/runtimes/*",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
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
  for_each = local.enabled_mcp_servers

  source_policy_documents = [
    data.aws_iam_policy_document.runtime_ecr_pull[each.key].json,
    data.aws_iam_policy_document.runtime_observability.json
  ]
}

resource "aws_iam_role_policy" "runtime" {
  for_each = local.enabled_mcp_servers

  role   = aws_iam_role.runtime[each.key].id
  policy = data.aws_iam_policy_document.runtime[each.key].json
}

resource "aws_iam_role" "gateway" {
  name               = "agentcore_${local.gateway_name}"
  assume_role_policy = data.aws_iam_policy_document.agentcore_assume_role.json
  tags               = local.tags
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
