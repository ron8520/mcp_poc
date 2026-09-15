output "enterprise_mcp_application_client_id" {
  value = module.entra.enterprise_mcp_application_client_id
}

output "enterprise_mcp_audience" {
  value = module.entra.enterprise_mcp_audience
}

output "enterprise_mcp_discovery_url" {
  value = module.entra.enterprise_mcp_discovery_url
}

output "gateway_id" {
  value = module.platform.gateway_id
}

output "gateway_url" {
  value = module.platform.gateway_url
}

output "runtime_arns" {
  value = module.platform.runtime_arns
}

output "app_only_identities" {
  value = module.entra.app_only_identities
}

output "app_only_mcp_role_ids" {
  value = module.entra.app_only_mcp_role_ids
}

output "app_only_site_grants" {
  value = local.app_only_site_grants
}
