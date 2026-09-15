locals {
  app_only_enabled = length(var.app_only_bindings) > 0

  enabled_mcp_runtime_lanes = merge(
    {},
    [
      for service_name, service in var.mcp_servers : {
        for lane_name, lane in service.lanes :
        "${service_name}-${lane_name}" => {
          service_name        = service_name
          lane_name           = lane_name
          description         = coalesce(lane.description, "${service.description} (${lane_name} lane)")
          image_uri           = coalesce(lane.image_uri, service.image_uri)
          ecr_repository_arns = service.ecr_repository_arns
          secret_arns = (
            local.app_only_enabled && service_name == "sharepoint" && lane_name == "application"
          ) ? [] : lane.secret_arns
          secret_kms_key_arns = (
            local.app_only_enabled && service_name == "sharepoint" && lane_name == "application"
          ) ? [] : lane.secret_kms_key_arns
          obo_assertion_required = lane.obo_assertion_required
          environment = {
            for key, value in merge(
              service.environment,
              lane.environment,
              {
                MCP_SERVICE_NAME   = service_name
                MCP_EXECUTION_LANE = lane_name
              }
            ) : key => value
            if !(
              local.app_only_enabled &&
              service_name == "sharepoint" &&
              lane_name == "application" &&
              contains(["ENTRA_CLIENT_ID", "ENTRA_CLIENT_SECRET_ARN"], key)
            )
          }
        }
        if service.enabled && lane.enabled
      }
    ]...
  )

  gateway_name = "${var.environment}-${var.gateway_name}"

  tags = merge(
    {
      application = "enterprise-mcp"
      environment = var.environment
      managed_by  = "terraform"
    },
    var.tags
  )

  base_request_headers = [
    "x-correlation-id",
  ]

  obo_assertion_header = "x-mcp-user-assertion"

  cedar_policy_files = fileset("${path.module}/../../../policy/cedar", "*.cedar")
}
