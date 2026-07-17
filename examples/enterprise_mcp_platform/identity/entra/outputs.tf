output "enterprise_mcp_application_client_id" {
  value = azuread_application.enterprise_mcp_api.client_id
}

output "enterprise_mcp_audience" {
  value = var.enterprise_mcp_audience
}

output "enterprise_mcp_discovery_url" {
  value = "https://login.microsoftonline.com/${var.tenant_id}/v2.0/.well-known/openid-configuration"
}

output "claude_code_client_id" {
  value = azuread_application.claude_code_client.client_id
}

output "people_assist_client_id" {
  value = azuread_application.people_assist_client.client_id
}

output "people_assist_client_secret" {
  value     = var.create_people_assist_client_secret ? azuread_application_password.people_assist_client[0].value : null
  sensitive = true
}
