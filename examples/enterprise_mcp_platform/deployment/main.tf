locals {
  composed_mcp_servers = {
    for service_name, service in var.mcp_servers : service_name => merge(service, {
      environment = merge(
        service.environment,
        {
          ENTRA_TENANT_ID = var.tenant_id
        }
      )
      lanes = {
        for lane_name, lane in service.lanes : lane_name => merge(lane, {
          environment = merge(
            lane.environment,
            lookup(lane.environment, "GRAPH_AUTH_MODE", null) == "obo" ? {
              ENTRA_CLIENT_ID = module.entra.enterprise_mcp_application_client_id
              ENTRA_TENANT_ID = var.tenant_id
            } : {}
          )
        })
      }
    })
  }

  app_only_bindings = {
    for app_name, provider_arn in var.app_only_provider_bindings : app_name => {
      caller_client_id = module.entra.app_only_identities[app_name].caller_client_id
      provider_arn     = provider_arn
      grants           = var.app_only_apps[app_name].grants
    }
  }

  gateway_allowed_audience = [module.entra.enterprise_mcp_application_client_id]

  gateway_allowed_clients = distinct(concat(
    [
      module.entra.claude_code_client_id,
      module.entra.people_assist_client_id,
    ],
    [
      for identity in values(module.entra.app_only_identities) : identity.caller_client_id
    ],
  ))

  app_only_site_grants = {
    for grant in flatten([
      for app_name, app in var.app_only_apps : [
        for site, tools in app.grants : [
          {
            key      = "${app_name}:${site}"
            app_name = app_name
            site     = site
            role     = contains(toset(tools), "sharepoint_upload_file") ? "write" : "read"
          }
        ]
      ]
      ]) : grant.key => {
      client_id = module.entra.app_only_identities[grant.app_name].downstream_client_id
      site      = grant.site
      role      = grant.role
    }
  }
}

module "entra" {
  source = "../identity/entra"

  environment                           = var.environment
  tenant_id                             = var.tenant_id
  enterprise_mcp_audience               = var.enterprise_mcp_audience
  claude_code_redirect_uris             = var.claude_code_redirect_uris
  enable_device_code_flow               = var.enable_device_code_flow
  sharepoint_readers_group_object_id    = var.sharepoint_readers_group_object_id
  sharepoint_publishers_group_object_id = var.sharepoint_publishers_group_object_id
  crm_admins_group_object_id            = var.crm_admins_group_object_id
  create_people_assist_client_secret    = var.create_people_assist_client_secret
  people_assist_secret_display_name     = var.people_assist_secret_display_name
  enable_conditional_access_example     = var.enable_conditional_access_example
  conditional_access_state              = var.conditional_access_state
  internal_network_cidrs                = var.internal_network_cidrs
  break_glass_user_object_ids           = var.break_glass_user_object_ids
  app_only_apps                         = var.app_only_apps
}

module "platform" {
  source = "../infra"

  region                           = var.region
  target_account_id                = var.target_account_id
  environment                      = var.environment
  gateway_name                     = var.gateway_name
  gateway_policy_mode              = var.gateway_policy_mode
  gateway_app_only_ingress_enabled = var.gateway_app_only_ingress_enabled
  entra_discovery_url              = module.entra.enterprise_mcp_discovery_url
  entra_allowed_audience           = local.gateway_allowed_audience
  entra_allowed_clients            = local.gateway_allowed_clients
  entra_tenant_id                  = var.tenant_id
  private_subnet_ids               = var.private_subnet_ids
  runtime_security_group_ids       = var.runtime_security_group_ids
  tags                             = var.tags
  mcp_servers                      = local.composed_mcp_servers
  app_only_bindings                = local.app_only_bindings
}
