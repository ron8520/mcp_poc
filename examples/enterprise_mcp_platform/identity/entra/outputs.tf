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

output "app_only_identities" {
  value = {
    for app_name in keys(var.app_only_apps) : app_name => {
      caller_client_id                       = azuread_application.app_only_caller[app_name].client_id
      caller_service_principal_object_id     = azuread_service_principal.app_only_caller[app_name].object_id
      downstream_client_id                   = azuread_application.app_only_downstream[app_name].client_id
      downstream_service_principal_object_id = azuread_service_principal.app_only_downstream[app_name].object_id
    }
  }
}

output "app_only_mcp_role_ids" {
  value = {
    read   = random_uuid.role_people_assist_read.result
    upload = random_uuid.role_sharepoint_automation_write.result
  }
}
