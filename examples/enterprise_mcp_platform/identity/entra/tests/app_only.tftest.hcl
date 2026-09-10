mock_provider "random" {
  mock_resource "random_uuid" {
    defaults = {
      result = "44444444-4444-4444-8444-444444444444"
    }
  }
}

mock_provider "azuread" {
  mock_data "azuread_service_principal" {
    defaults = {
      client_id    = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
      object_id    = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
      app_role_ids = { "Sites.Selected" = "cccccccc-cccc-4ccc-8ccc-cccccccccccc" }
    }
  }

  mock_resource "azuread_application" {
    defaults = {
      client_id = "55555555-5555-4555-8555-555555555555"
      id        = "66666666-6666-4666-8666-666666666666"
    }
  }

  mock_resource "azuread_service_principal" {
    defaults = {
      object_id = "77777777-7777-4777-8777-777777777777"
    }
  }

  mock_resource "azuread_app_role_assignment" {}
  mock_resource "azuread_application_password" {}
  mock_resource "azuread_service_principal_delegated_permission_grant" {}
}

variables {
  environment                           = "nonprod"
  tenant_id                             = "11111111-1111-4111-8111-111111111111"
  enterprise_mcp_audience               = "api://enterprise-mcp-nonprod"
  sharepoint_readers_group_object_id    = "88888888-8888-4888-8888-888888888888"
  sharepoint_publishers_group_object_id = "99999999-9999-4999-8999-999999999999"
  crm_admins_group_object_id            = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  create_people_assist_client_secret    = false

  app_only_apps = {
    finance_reader = {
      owner = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
      grants = {
        site_a = [
          "sharepoint_list_site_content",
          "sharepoint_get_file_text",
        ]
      }
    }

    finance_publisher = {
      owner = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
      grants = {
        site_a = [
          "sharepoint_list_site_content",
          "sharepoint_upload_file",
        ]
      }
    }
  }
}

run "catalog_creates_separate_caller_and_downstream_apps" {
  command = plan

  assert {
    condition = (
      toset(keys(azuread_application.app_only_caller)) ==
      toset(["finance_reader", "finance_publisher"])
    )
    error_message = "The catalog must create one distinct MCP caller application per approved app."
  }

  assert {
    condition = (
      toset(keys(azuread_application.app_only_downstream)) ==
      toset(["finance_reader", "finance_publisher"])
    )
    error_message = "The catalog must create one distinct downstream Graph application per approved app."
  }
}

run "caller_roles_are_separate_from_graph_sites_selected_consent" {
  command = apply

  assert {
    condition = (
      length(azuread_app_role_assignment.app_only_caller_roles) == 3 &&
      toset(keys(local.app_only_role_assignments)) == toset([
        "finance_reader-read",
        "finance_publisher-read",
        "finance_publisher-upload",
      ])
    )
    error_message = "MCP caller assignments must use only the Enterprise MCP application roles."
  }

  assert {
    condition = alltrue([
      for application in values(azuread_application.app_only_caller) : (
        length(application.required_resource_access) == 1 &&
        one(application.required_resource_access).resource_app_id == azuread_application.enterprise_mcp_api.client_id &&
        alltrue([
          for access in one(application.required_resource_access).resource_access :
          access.type == "Role" && contains([
            local.app_only_role_ids.read,
            local.app_only_role_ids.upload,
          ], access.id)
        ])
      )
    ])
    error_message = "Caller applications must request the Enterprise MCP app roles, not Graph permissions."
  }

  assert {
    condition = alltrue([
      for application in values(azuread_application.app_only_downstream) : (
        length(application.required_resource_access) == 1 &&
        one(application.required_resource_access).resource_app_id == data.azuread_service_principal.microsoft_graph[0].client_id &&
        length(one(application.required_resource_access).resource_access) == 1 &&
        one(one(application.required_resource_access).resource_access).id == data.azuread_service_principal.microsoft_graph[0].app_role_ids["Sites.Selected"] &&
        one(one(application.required_resource_access).resource_access).type == "Role"
      )
    ])
    error_message = "Downstream applications must request only Microsoft Graph Sites.Selected application permission."
  }

  assert {
    condition = (
      length(azuread_app_role_assignment.app_only_sites_selected_consent) == 2
    )
    error_message = "Each downstream service principal must receive Graph Sites.Selected consent separately from MCP caller roles."
  }
}

run "catalog_does_not_create_client_secrets" {
  command = apply

  assert {
    condition = (
      length(azuread_application_password.people_assist_client) == 0 &&
      output.people_assist_client_secret == null
    )
    error_message = "The app-only catalog test must not create or expose a client secret."
  }
}
