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

output "runtime_lanes" {
  value = {
    for name, lane in local.enabled_mcp_runtime_lanes : name => {
      service_name = lane.service_name
      lane_name    = lane.lane_name
      runtime_arn  = aws_bedrockagentcore_agent_runtime.mcp_server[name].agent_runtime_arn
      target_id    = aws_bedrockagentcore_gateway_target.runtime_mcp[name].target_id
    }
  }
}

output "cedar_policy_arns" {
  value = {
    for name, policy in aws_bedrockagentcore_policy.cedar : name => policy.policy_arn
  }
}
