locals {
  gateway_obo_interceptor_name = "agentcore-${var.environment}-mcp-obo-assertion"
}

data "archive_file" "gateway_obo_assertion" {
  type        = "zip"
  source_file = "${path.module}/../gateway/obo_assertion_interceptor.py"
  output_path = "${path.module}/.terraform/gateway-obo-assertion.zip"
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "gateway_obo_interceptor" {
  name               = local.gateway_obo_interceptor_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

resource "aws_cloudwatch_log_group" "gateway_obo_interceptor" {
  name              = "/aws/lambda/${local.gateway_obo_interceptor_name}"
  retention_in_days = 30
  tags              = local.tags
}

data "aws_iam_policy_document" "gateway_obo_interceptor_logs" {
  statement {
    sid    = "WriteFunctionLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.gateway_obo_interceptor.arn}:*"]
  }
}

resource "aws_iam_role_policy" "gateway_obo_interceptor_logs" {
  role   = aws_iam_role.gateway_obo_interceptor.id
  policy = data.aws_iam_policy_document.gateway_obo_interceptor_logs.json
}

resource "aws_lambda_function" "gateway_obo_assertion" {
  function_name = local.gateway_obo_interceptor_name
  description   = "Copies a Gateway-validated delegated token to the SharePoint OBO lane"
  role          = aws_iam_role.gateway_obo_interceptor.arn
  runtime       = "python3.12"
  handler       = "obo_assertion_interceptor.lambda_handler"
  filename      = data.archive_file.gateway_obo_assertion.output_path

  source_code_hash = data.archive_file.gateway_obo_assertion.output_base64sha256
  memory_size      = 128
  timeout          = 5

  tags = local.tags

  depends_on = [
    aws_iam_role_policy.gateway_obo_interceptor_logs
  ]
}

data "aws_iam_policy_document" "gateway_interceptor" {
  statement {
    sid       = "InvokeOboAssertionInterceptor"
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.gateway_obo_assertion.arn]
  }
}

resource "aws_iam_role_policy" "gateway_interceptor" {
  role   = aws_iam_role.gateway.id
  policy = data.aws_iam_policy_document.gateway_interceptor.json
}
