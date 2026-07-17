output "gateway_id" {
  value = aws_bedrockagentcore_gateway.this.gateway_id
}

output "gateway_url" {
  value = aws_bedrockagentcore_gateway.this.gateway_url
}

output "gateway_role_arn" {
  value = aws_iam_role.gateway.arn
}

output "runtime_arns" {
  value = {
    for name, runtime in aws_bedrockagentcore_agent_runtime.mcp_server : name => runtime.agent_runtime_arn
  }
}
