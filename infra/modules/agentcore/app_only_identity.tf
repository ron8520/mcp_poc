locals {
  app_only_target = "sharepoint-application"
  app_only_header = "x-mcp-caller-assertion"

  app_only_mapping_json = local.app_only_enabled ? jsonencode({
    schema_version = 1
    environment    = var.environment
    tenant_id      = var.entra_tenant_id
    audience       = one(var.entra_allowed_audience)
    target_name    = local.app_only_target
    applications = {
      for binding in values(var.app_only_bindings) : binding.caller_client_id => {
        provider_arn = binding.provider_arn
        grants       = binding.grants
      }
    }
  }) : ""

  identity_directory_arn = "arn:aws:bedrock-agentcore:${var.region}:${var.target_account_id}:workload-identity-directory/default"
  token_vault_arn        = "arn:aws:bedrock-agentcore:${var.region}:${var.target_account_id}:token-vault/default"
}

resource "aws_bedrockagentcore_workload_identity" "sharepoint_application" {
  count = local.app_only_enabled ? 1 : 0
  name  = "${var.environment}-sharepoint-application-m2m"

  lifecycle {
    precondition {
      condition     = contains(keys(local.enabled_mcp_runtime_lanes), local.app_only_target) && var.entra_tenant_id != null
      error_message = "App-only bindings require an enabled SharePoint application lane and an Entra tenant ID."
    }
    precondition {
      condition     = length(local.app_only_mapping_json) <= 5000
      error_message = "APP_ONLY_MAPPING_JSON exceeds the Runtime environment value limit; reduce this PoC mapping before deployment."
    }
    precondition {
      condition     = length(distinct([for binding in values(var.app_only_bindings) : binding.provider_arn])) == length(var.app_only_bindings)
      error_message = "Each app-only caller must have its own downstream OAuth2 provider."
    }
    precondition {
      condition = alltrue([
        for binding in values(var.app_only_bindings) :
        can(regex("^arn:aws:bedrock-agentcore:${var.region}:${var.target_account_id}:token-vault/default/oauth2-?credential-?provider/[A-Za-z0-9._-]+$", binding.provider_arn))
      ])
      error_message = "Each provider must be an explicit OAuth2 provider ARN in this deployment account and region."
    }
  }
}

data "aws_iam_policy_document" "runtime_app_only_identity" {
  count = local.app_only_enabled ? 1 : 0

  statement {
    sid     = "GetApplicationWorkloadToken"
    effect  = "Allow"
    actions = ["bedrock-agentcore:GetWorkloadAccessToken"]
    resources = [
      local.identity_directory_arn,
      aws_bedrockagentcore_workload_identity.sharepoint_application[0].workload_identity_arn
    ]
  }

  statement {
    sid     = "GetApprovedApplicationTokens"
    effect  = "Allow"
    actions = ["bedrock-agentcore:GetResourceOauth2Token"]
    resources = concat([
      local.identity_directory_arn,
      aws_bedrockagentcore_workload_identity.sharepoint_application[0].workload_identity_arn,
      local.token_vault_arn
    ], distinct([for binding in values(var.app_only_bindings) : binding.provider_arn]))
  }
}

resource "aws_iam_role_policy" "runtime_app_only_identity" {
  count = local.app_only_enabled ? 1 : 0

  name   = "approved-app-only-providers"
  role   = aws_iam_role.runtime[local.app_only_target].id
  policy = data.aws_iam_policy_document.runtime_app_only_identity[0].json
}
