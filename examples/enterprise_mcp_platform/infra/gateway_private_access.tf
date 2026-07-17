data "aws_iam_policy_document" "gateway_endpoint" {
  statement {
    sid    = "AllowEnterpriseMcpGatewayInvoke"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:InvokeGateway"
    ]
    resources = [
      aws_bedrockagentcore_gateway.this.gateway_arn
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }
}

resource "aws_vpc_endpoint" "gateway" {
  vpc_id              = var.client_vpc_id
  service_name        = "com.amazonaws.${var.region}.bedrock-agentcore.gateway"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.gateway_endpoint_subnet_ids
  security_group_ids  = var.gateway_endpoint_security_group_ids
  private_dns_enabled = true
  policy              = data.aws_iam_policy_document.gateway_endpoint.json
  tags                = local.tags
}
