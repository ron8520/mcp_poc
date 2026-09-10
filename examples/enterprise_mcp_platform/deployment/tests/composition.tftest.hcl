mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }
}

mock_provider "archive" {
  mock_data "archive_file" {
    defaults = {
      output_path         = "gateway-obo-assertion.zip"
      output_base64sha256 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    }
  }
}

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
  mock_resource "azuread_service_principal_delegated_permission_grant" {}
  mock_resource "azuread_application_password" {}
}

variables {
  environment                           = "nonprod"
  tenant_id                             = "11111111-1111-4111-8111-111111111111"
  enterprise_mcp_audience               = "api://enterprise-mcp-nonprod"
  sharepoint_readers_group_object_id    = "88888888-8888-4888-8888-888888888888"
  sharepoint_publishers_group_object_id = "99999999-9999-4999-8999-999999999999"
  crm_admins_group_object_id            = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
  enable_conditional_access_example     = false
  create_people_assist_client_secret    = false

  region                           = "ap-southeast-2"
  target_account_id                = "111122223333"
  gateway_policy_mode              = "LOG_ONLY"
  gateway_app_only_ingress_enabled = false
  private_subnet_ids               = ["subnet-test"]
  runtime_security_group_ids       = ["sg-test"]
  app_only_apps                    = {}
  app_only_provider_bindings       = {}

  mcp_servers = {
    sharepoint = {
      enabled             = true
      description         = "SharePoint MCP"
      image_uri           = "111122223333.dkr.ecr.ap-southeast-2.amazonaws.com/sharepoint@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      ecr_repository_arns = ["arn:aws:ecr:ap-southeast-2:111122223333:repository/sharepoint"]
      environment         = { GRAPH_DRY_RUN = "false" }
      lanes = {
        delegated = {
          image_uri              = "111122223333.dkr.ecr.ap-southeast-2.amazonaws.com/sharepoint@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
          obo_assertion_required = true
          secret_arns            = ["arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:obo"]
          environment = {
            GRAPH_AUTH_MODE             = "obo"
            GRAPH_USER_ASSERTION_HEADER = "x-mcp-user-assertion"
            ENTRA_CLIENT_SECRET_ARN     = "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:obo"
          }
        }
        application = {
          secret_arns = ["arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:application"]
          environment = {
            GRAPH_AUTH_MODE         = "client_credentials"
            ENTRA_CLIENT_ID         = "fixed-application-client"
            ENTRA_CLIENT_SECRET_ARN = "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:application"
          }
        }
      }
    }
  }
}

run "module_wiring_and_lane_image_override" {
  command = plan

  override_resource {
    target          = module.entra.azuread_application.enterprise_mcp_api
    override_during = plan
    values = {
      client_id = "22222222-2222-4222-8222-222222222222"
    }
  }

  override_resource {
    target          = module.entra.azuread_application.claude_code_client
    override_during = plan
    values = {
      client_id = "33333333-3333-4333-8333-333333333333"
    }
  }

  assert {
    condition = (
      output.enterprise_mcp_discovery_url ==
      "https://login.microsoftonline.com/11111111-1111-4111-8111-111111111111/v2.0/.well-known/openid-configuration"
    )
    error_message = "The composition must use the Entra module discovery output."
  }

  assert {
    condition = (
      output.enterprise_mcp_application_client_id ==
      "22222222-2222-4222-8222-222222222222"
    )
    error_message = "The root output must expose the Enterprise MCP API client ID used for the v2 audience."
  }

  assert {
    condition = (
      local.gateway_allowed_audience == [output.enterprise_mcp_application_client_id]
    )
    error_message = "Gateway v2 audience must be the Enterprise MCP API client ID, not its api:// scope prefix."
  }

  assert {
    condition = (
      local.composed_mcp_servers.sharepoint.lanes.delegated.environment.ENTRA_CLIENT_ID ==
      output.enterprise_mcp_application_client_id
    )
    error_message = "The OBO lane must use the Enterprise MCP API client ID from Entra outputs."
  }

  assert {
    condition = (
      local.composed_mcp_servers.sharepoint.lanes.delegated.environment.ENTRA_TENANT_ID ==
      "11111111-1111-4111-8111-111111111111"
    )
    error_message = "The OBO lane must receive the root tenant ID."
  }

  assert {
    condition = (
      local.composed_mcp_servers.sharepoint.lanes.delegated.image_uri ==
      "111122223333.dkr.ecr.ap-southeast-2.amazonaws.com/sharepoint@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    error_message = "A lane image_uri override must replace the service image URI."
  }

  assert {
    condition = (
      local.composed_mcp_servers.sharepoint.lanes.application.image_uri == null
    )
    error_message = "A lane without image_uri must leave the service-level image available for module defaulting."
  }
}

run "app_only_site_write_subsumes_read" {
  command = plan

  variables {
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

  assert {
    condition = (
      local.app_only_site_grants["finance_reader:site_a"].role == "read" &&
      local.app_only_site_grants["finance_publisher:site_a"].role == "write" &&
      length(local.app_only_site_grants) == 2
    )
    error_message = "Each app/site pair must receive one native site role, with write subsuming read."
  }
}
