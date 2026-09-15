mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}
mock_provider "archive" {}

variables {
  environment                = "nonprod"
  target_account_id          = "111122223333"
  entra_tenant_id            = "11111111-1111-1111-1111-111111111111"
  entra_discovery_url        = "https://login.microsoftonline.com/11111111-1111-1111-1111-111111111111/v2.0/.well-known/openid-configuration"
  entra_allowed_audience     = ["22222222-2222-2222-2222-222222222222"]
  private_subnet_ids         = ["subnet-test"]
  runtime_security_group_ids = ["sg-test"]
  mcp_servers = {
    sharepoint = {
      enabled             = true
      description         = "SharePoint"
      image_uri           = "111122223333.dkr.ecr.ap-southeast-2.amazonaws.com/sharepoint@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      ecr_repository_arns = ["arn:aws:ecr:ap-southeast-2:111122223333:repository/sharepoint"]
      environment         = { GRAPH_DRY_RUN = "false" }
      lanes = {
        delegated = {
          obo_assertion_required = true
          secret_arns            = ["arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:obo"]
          environment            = { GRAPH_AUTH_MODE = "obo", ENTRA_CLIENT_ID = "obo-client" }
        }
        application = {
          secret_arns = ["arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:legacy"]
          environment = {
            GRAPH_AUTH_MODE         = "client_credentials"
            ENTRA_CLIENT_ID         = "legacy-client"
            ENTRA_CLIENT_SECRET_ARN = "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:legacy"
          }
        }
      }
    }
  }
}

run "empty_catalog_keeps_legacy_lanes" {
  command = plan

  assert {
    condition = (
      length(local.cedar_policy_files) == 2 &&
      fileexists("${path.module}/../../../gateway/obo_assertion_interceptor.py")
    )
    error_message = "The relocated module must resolve the existing Cedar policies and interceptor."
  }

  assert {
    condition     = !local.app_only_enabled && length(aws_bedrockagentcore_workload_identity.sharepoint_application) == 0
    error_message = "The default must not provision native app-only identity resources."
  }
  assert {
    condition     = aws_bedrockagentcore_agent_runtime.mcp_server["sharepoint-application"].environment_variables.GRAPH_AUTH_MODE == "client_credentials"
    error_message = "The empty catalog must preserve the fixed application lane."
  }
}

run "native_mapping_is_exact_and_obo_is_unchanged" {
  command = plan

  override_resource {
    target          = aws_bedrockagentcore_workload_identity.sharepoint_application[0]
    override_during = plan
    values = {
      workload_identity_arn = "arn:aws:bedrock-agentcore:ap-southeast-2:111122223333:workload-identity-directory/default/workload-identity/nonprod-sharepoint-application-m2m"
    }
  }

  variables {
    app_only_bindings = {
      app_a = {
        caller_client_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        provider_arn     = "arn:aws:bedrock-agentcore:ap-southeast-2:111122223333:token-vault/default/oauth2credentialprovider/app-a"
        grants           = { site_a = ["sharepoint_list_site_content"], site_b = ["sharepoint_upload_file"] }
      }
      app_b = {
        caller_client_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        provider_arn     = "arn:aws:bedrock-agentcore:ap-southeast-2:111122223333:token-vault/default/oauth2credentialprovider/app-b"
        grants           = { site_b = ["sharepoint_get_file_text"] }
      }
    }
  }

  assert {
    condition = (
      jsondecode(local.app_only_mapping_json).applications["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"].grants.site_a == ["sharepoint_list_site_content"] &&
      jsondecode(local.app_only_mapping_json).applications["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"].grants.site_b == ["sharepoint_upload_file"] &&
      jsondecode(local.app_only_mapping_json).applications["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"].provider_arn == var.app_only_bindings.app_b.provider_arn
    )
    error_message = "Mapping must preserve exact site/tool pairs and per-app providers."
  }
  assert {
    condition = (
      length(local.enabled_mcp_runtime_lanes["sharepoint-application"].secret_arns) == 0 &&
      !contains(keys(local.enabled_mcp_runtime_lanes["sharepoint-application"].environment), "ENTRA_CLIENT_SECRET_ARN") &&
      !contains(keys(local.enabled_mcp_runtime_lanes["sharepoint-application"].environment), "ENTRA_CLIENT_ID")
    )
    error_message = "Native mode must remove the legacy application credential and its IAM access."
  }
  assert {
    condition = (
      local.enabled_mcp_runtime_lanes["sharepoint-delegated"].environment.GRAPH_AUTH_MODE == "obo" &&
      length(local.enabled_mcp_runtime_lanes["sharepoint-delegated"].secret_arns) == 1 &&
      length(aws_iam_role_policy.runtime_app_only_identity) == 1
    )
    error_message = "Native IAM must be separate from the unchanged OBO lane."
  }
  assert {
    condition = (
      aws_bedrockagentcore_agent_runtime.mcp_server["sharepoint-application"].environment_variables.GRAPH_AUTH_MODE == "agentcore_m2m" &&
      contains(aws_bedrockagentcore_agent_runtime.mcp_server["sharepoint-application"].request_header_configuration[0].request_header_allowlist, "x-mcp-caller-assertion") &&
      !contains(aws_bedrockagentcore_agent_runtime.mcp_server["sharepoint-delegated"].request_header_configuration[0].request_header_allowlist, "x-mcp-caller-assertion")
    )
    error_message = "Only the application lane must receive the native mode and caller assertion header."
  }
  assert {
    condition = length(data.aws_iam_policy_document.runtime_app_only_identity[0].statement) == 2 && alltrue([
      for statement in data.aws_iam_policy_document.runtime_app_only_identity[0].statement :
      length(statement.resources) == 5 &&
      contains(statement.resources, var.app_only_bindings.app_a.provider_arn) &&
      contains(statement.resources, var.app_only_bindings.app_b.provider_arn)
      if statement.sid == "GetApprovedApplicationTokens"
    ])
    error_message = "M2M IAM must name the two configured providers plus the exact workload, directory and vault resources."
  }
}

run "ingress_without_bindings_is_rejected" {
  command = plan
  variables {
    gateway_policy_mode              = "ENFORCE"
    gateway_app_only_ingress_enabled = true
  }
  expect_failures = [aws_bedrockagentcore_gateway.this]
}

run "foreign_provider_is_rejected" {
  command = plan
  variables {
    app_only_bindings = {
      app_a = {
        caller_client_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        provider_arn     = "arn:aws:bedrock-agentcore:ap-southeast-2:999999999999:token-vault/default/oauth2credentialprovider/app-a"
        grants           = { site_a = ["sharepoint_list_site_content"] }
      }
    }
  }
  expect_failures = [aws_bedrockagentcore_workload_identity.sharepoint_application[0]]
}

run "shared_provider_is_rejected" {
  command = plan
  variables {
    app_only_bindings = {
      app_a = {
        caller_client_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        provider_arn     = "arn:aws:bedrock-agentcore:ap-southeast-2:111122223333:token-vault/default/oauth2credentialprovider/shared"
        grants           = { site_a = ["sharepoint_list_site_content"] }
      }
      app_b = {
        caller_client_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        provider_arn     = "arn:aws:bedrock-agentcore:ap-southeast-2:111122223333:token-vault/default/oauth2credentialprovider/shared"
        grants           = { site_b = ["sharepoint_get_file_text"] }
      }
    }
  }
  expect_failures = [aws_bedrockagentcore_workload_identity.sharepoint_application[0]]
}

run "bindings_do_not_bypass_enforce_gate" {
  command = plan
  variables {
    gateway_app_only_ingress_enabled = true
    app_only_bindings = {
      app_a = {
        caller_client_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        provider_arn     = "arn:aws:bedrock-agentcore:ap-southeast-2:111122223333:token-vault/default/oauth2credentialprovider/app-a"
        grants           = { site_a = ["sharepoint_list_site_content"] }
      }
    }
  }
  expect_failures = [aws_bedrockagentcore_gateway.this]
}
