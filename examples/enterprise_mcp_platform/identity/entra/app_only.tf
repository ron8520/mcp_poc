locals {
  app_only_read_tools = toset([
    "sharepoint_list_site_content",
    "sharepoint_get_file_text",
  ])

  app_only_upload_tools = toset([
    "sharepoint_upload_file",
  ])

  app_only_catalog = {
    for app_name, app in var.app_only_apps : app_name => {
      owner  = app.owner
      grants = app.grants
      tools = toset(flatten([
        for site_tools in values(app.grants) : [
          for tool_name in site_tools : tool_name
        ]
      ]))
    }
  }

  app_only_role_keys = {
    for app_name, app in local.app_only_catalog : app_name => toset(concat(
      length(setintersection(app.tools, local.app_only_read_tools)) > 0 ? ["read"] : [],
      length(setintersection(app.tools, local.app_only_upload_tools)) > 0 ? ["upload"] : [],
    ))
  }

  app_only_role_ids = {
    read   = random_uuid.role_people_assist_read.result
    upload = random_uuid.role_sharepoint_automation_write.result
  }

  app_only_role_assignments = {
    for assignment in flatten([
      for app_name, roles in local.app_only_role_keys : [
        for role in roles : {
          key      = "${app_name}-${role}"
          app_name = app_name
          role     = role
        }
      ]
    ]) : assignment.key => assignment
  }
}

data "azuread_service_principal" "microsoft_graph" {
  count = length(var.app_only_apps) > 0 ? 1 : 0
  # Resolve Graph by its application ID, not a mutable display name.
  client_id = "00000003-0000-0000-c000-000000000000"
}

resource "azuread_application" "app_only_caller" {
  for_each = local.app_only_catalog

  display_name     = "enterprise-mcp-${each.key}-caller-${var.environment}"
  sign_in_audience = "AzureADMyOrg"
  owners           = [each.value.owner]

  dynamic "required_resource_access" {
    for_each = length(local.app_only_role_keys[each.key]) > 0 ? [true] : []

    content {
      resource_app_id = azuread_application.enterprise_mcp_api.client_id

      dynamic "resource_access" {
        for_each = local.app_only_role_keys[each.key]

        content {
          id   = local.app_only_role_ids[resource_access.value]
          type = "Role"
        }
      }
    }
  }
}

resource "azuread_service_principal" "app_only_caller" {
  for_each = azuread_application.app_only_caller

  client_id                    = each.value.client_id
  app_role_assignment_required = true
}

resource "azuread_app_role_assignment" "app_only_caller_roles" {
  for_each = local.app_only_role_assignments

  app_role_id         = local.app_only_role_ids[each.value.role]
  principal_object_id = azuread_service_principal.app_only_caller[each.value.app_name].object_id
  resource_object_id  = azuread_service_principal.enterprise_mcp_api.object_id
}

resource "azuread_application" "app_only_downstream" {
  for_each = local.app_only_catalog

  display_name     = "enterprise-mcp-${each.key}-sharepoint-${var.environment}"
  sign_in_audience = "AzureADMyOrg"
  owners           = [each.value.owner]

  required_resource_access {
    resource_app_id = data.azuread_service_principal.microsoft_graph[0].client_id

    resource_access {
      id   = data.azuread_service_principal.microsoft_graph[0].app_role_ids["Sites.Selected"]
      type = "Role"
    }
  }
}

resource "azuread_service_principal" "app_only_downstream" {
  for_each = azuread_application.app_only_downstream

  client_id                    = each.value.client_id
  app_role_assignment_required = true
}

resource "azuread_app_role_assignment" "app_only_sites_selected_consent" {
  for_each = azuread_service_principal.app_only_downstream

  app_role_id         = data.azuread_service_principal.microsoft_graph[0].app_role_ids["Sites.Selected"]
  principal_object_id = each.value.object_id
  resource_object_id  = data.azuread_service_principal.microsoft_graph[0].object_id
}
