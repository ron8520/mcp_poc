resource "random_uuid" "mcp_invoke_scope" {}
resource "random_uuid" "role_sharepoint_read" {}
resource "random_uuid" "role_sharepoint_publish" {}
resource "random_uuid" "role_crm_admin" {}
resource "random_uuid" "role_people_assist_read" {}
resource "random_uuid" "role_sharepoint_automation_write" {}

resource "azuread_application" "enterprise_mcp_api" {
  display_name     = "enterprise-mcp-api-${var.environment}"
  sign_in_audience = "AzureADMyOrg"
  identifier_uris  = [var.enterprise_mcp_audience]

  optional_claims {
    access_token {
      name = "idtyp"
    }
  }

  api {
    requested_access_token_version = 2

    oauth2_permission_scope {
      id                         = random_uuid.mcp_invoke_scope.result
      value                      = "mcp.invoke"
      type                       = "Admin"
      enabled                    = true
      admin_consent_display_name = "Invoke Enterprise MCP"
      admin_consent_description  = "Allows approved MCP clients to invoke Enterprise MCP Gateway."
    }
  }

  app_role {
    id                   = random_uuid.role_sharepoint_read.result
    value                = "MCP.SharePoint.Delegated.Read"
    display_name         = "MCP SharePoint Delegated Read"
    description          = "Can use SharePoint read tools; native SharePoint permissions still apply."
    allowed_member_types = ["User"]
    enabled              = true
  }

  app_role {
    id                   = random_uuid.role_sharepoint_publish.result
    value                = "MCP.SharePoint.Delegated.Upload"
    display_name         = "MCP SharePoint Delegated Upload"
    description          = "Can upload a file to SharePoint; native SharePoint permissions still apply."
    allowed_member_types = ["User"]
    enabled              = true
  }

  app_role {
    id                   = random_uuid.role_crm_admin.result
    value                = "MCP.CRM.Admin"
    display_name         = "MCP CRM Admin"
    description          = "Can call approved CRM MCP tools."
    allowed_member_types = ["User"]
    enabled              = true
  }

  app_role {
    id                   = random_uuid.role_people_assist_read.result
    value                = "MCP.SharePoint.Application.Read"
    display_name         = "MCP SharePoint Application Read"
    description          = "Allows an approved application identity to use SharePoint read tools; Sites.Selected still applies."
    allowed_member_types = ["Application"]
    enabled              = true
  }

  app_role {
    id                   = random_uuid.role_sharepoint_automation_write.result
    value                = "MCP.SharePoint.Application.Upload"
    display_name         = "MCP SharePoint Application Upload"
    description          = "Allows an approved application identity to upload a file to SharePoint; Sites.Selected still applies."
    allowed_member_types = ["Application"]
    enabled              = true
  }
}

resource "azuread_service_principal" "enterprise_mcp_api" {
  client_id                    = azuread_application.enterprise_mcp_api.client_id
  app_role_assignment_required = true
}

resource "azuread_application" "claude_code_client" {
  display_name                   = "claude-code-mcp-client-${var.environment}"
  sign_in_audience               = "AzureADMyOrg"
  fallback_public_client_enabled = var.enable_device_code_flow

  public_client {
    redirect_uris = var.claude_code_redirect_uris
  }

  required_resource_access {
    resource_app_id = azuread_application.enterprise_mcp_api.client_id

    resource_access {
      id   = random_uuid.mcp_invoke_scope.result
      type = "Scope"
    }
  }
}

resource "azuread_service_principal" "claude_code_client" {
  client_id                    = azuread_application.claude_code_client.client_id
  app_role_assignment_required = true
}

resource "azuread_service_principal_delegated_permission_grant" "claude_code_mcp_invoke" {
  service_principal_object_id          = azuread_service_principal.claude_code_client.object_id
  resource_service_principal_object_id = azuread_service_principal.enterprise_mcp_api.object_id
  claim_values                         = ["mcp.invoke"]
}

resource "azuread_application" "people_assist_client" {
  display_name     = "people-assist-mcp-client-${var.environment}"
  sign_in_audience = "AzureADMyOrg"

  required_resource_access {
    resource_app_id = azuread_application.enterprise_mcp_api.client_id

    resource_access {
      id   = random_uuid.role_people_assist_read.result
      type = "Role"
    }
  }
}

resource "azuread_service_principal" "people_assist_client" {
  client_id = azuread_application.people_assist_client.client_id
}

resource "azuread_app_role_assignment" "sharepoint_readers" {
  app_role_id         = random_uuid.role_sharepoint_read.result
  principal_object_id = var.sharepoint_readers_group_object_id
  resource_object_id  = azuread_service_principal.enterprise_mcp_api.object_id
}

resource "azuread_app_role_assignment" "sharepoint_publishers" {
  app_role_id         = random_uuid.role_sharepoint_publish.result
  principal_object_id = var.sharepoint_publishers_group_object_id
  resource_object_id  = azuread_service_principal.enterprise_mcp_api.object_id
}

resource "azuread_app_role_assignment" "crm_admins" {
  app_role_id         = random_uuid.role_crm_admin.result
  principal_object_id = var.crm_admins_group_object_id
  resource_object_id  = azuread_service_principal.enterprise_mcp_api.object_id
}

resource "azuread_app_role_assignment" "people_assist_read" {
  app_role_id         = random_uuid.role_people_assist_read.result
  principal_object_id = azuread_service_principal.people_assist_client.object_id
  resource_object_id  = azuread_service_principal.enterprise_mcp_api.object_id
}

resource "azuread_application_password" "people_assist_client" {
  count          = var.create_people_assist_client_secret ? 1 : 0
  application_id = azuread_application.people_assist_client.id
  display_name   = var.people_assist_secret_display_name
}
