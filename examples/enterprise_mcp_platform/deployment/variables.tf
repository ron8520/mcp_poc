variable "environment" {
  type        = string
  description = "Environment name controlled by the selected tfvars file."

  validation {
    condition     = contains(["nonprod", "prod"], var.environment)
    error_message = "environment must be nonprod or prod."
  }
}

variable "tenant_id" {
  type        = string
  description = "Microsoft Entra tenant ID."
}

variable "enterprise_mcp_audience" {
  type        = string
  description = "Application ID URI (scope prefix) for the Enterprise MCP API."
}

variable "claude_code_redirect_uris" {
  type        = list(string)
  default     = ["http://localhost"]
  description = "Redirect URIs for the Claude Code public client/token helper."
}

variable "enable_device_code_flow" {
  type        = bool
  default     = false
  description = "Enable only if the approved Claude Code token helper uses device-code flow."
}

variable "sharepoint_readers_group_object_id" {
  type        = string
  description = "Group assigned MCP.SharePoint.Delegated.Read on the Enterprise MCP API."
}

variable "sharepoint_publishers_group_object_id" {
  type        = string
  description = "Group assigned MCP.SharePoint.Delegated.Upload on the Enterprise MCP API."
}

variable "crm_admins_group_object_id" {
  type        = string
  description = "Group assigned MCP.CRM.Admin on the Enterprise MCP API."
}

variable "create_people_assist_client_secret" {
  type        = bool
  default     = false
  description = "Existing example switch; keep false unless the approved secret process allows Terraform state storage."
}

variable "people_assist_secret_display_name" {
  type        = string
  default     = "people-assist-mcp-client-secret"
  description = "Display name for the optional People Assist client secret."
}

variable "enable_conditional_access_example" {
  type        = bool
  default     = false
  description = "Creates a report-only Conditional Access policy example for the Enterprise MCP API."
}

variable "conditional_access_state" {
  type        = string
  default     = "enabledForReportingButNotEnforced"
  description = "Use report-only until identity/security teams approve enforcement."

  validation {
    condition = contains(
      ["enabled", "disabled", "enabledForReportingButNotEnforced"],
      var.conditional_access_state
    )
    error_message = "conditional_access_state must be enabled, disabled, or enabledForReportingButNotEnforced."
  }
}

variable "internal_network_cidrs" {
  type        = list(string)
  default     = []
  description = "Trusted corporate egress CIDRs for the optional Conditional Access example."
}

variable "break_glass_user_object_ids" {
  type        = list(string)
  default     = []
  description = "Emergency access users excluded from the optional Conditional Access example."
}

variable "app_only_apps" {
  type = map(object({
    owner  = string
    grants = map(set(string))
  }))
  default     = {}
  description = "Approved autonomous app catalog passed to the Entra identity module."

  validation {
    condition = alltrue([
      for app in values(var.app_only_apps) : (
        length(app.grants) > 0 && alltrue([
          for tools in values(app.grants) : length(tools) > 0 && alltrue([
            for tool_name in tools : contains([
              "sharepoint_list_site_content",
              "sharepoint_get_file_text",
              "sharepoint_upload_file",
            ], tool_name)
          ])
        ])
      )
    ])
    error_message = "app_only_apps must define at least one non-empty site grant per app and may contain only the approved SharePoint tool names."
  }
}

variable "app_only_provider_bindings" {
  type        = map(string)
  default     = {}
  description = "Explicit logical app to pre-registered AgentCore OAuth provider ARN bindings."
}

variable "region" {
  type    = string
  default = "ap-southeast-2"

  validation {
    condition     = var.region == "ap-southeast-2"
    error_message = "region must be ap-southeast-2 (Sydney); enable another region only after AgentCore Gateway/Runtime endpoint and VPC support is validated."
  }
}

variable "target_account_id" {
  type        = string
  description = "AWS account that owns the AgentCore deployment. Supplied by central platform/TFE configuration."

  validation {
    condition     = can(regex("^[0-9]{12}$", var.target_account_id))
    error_message = "target_account_id must be a 12-digit AWS account ID."
  }
}

variable "gateway_name" {
  type        = string
  default     = "enterprise-mcp-gateway"
  description = "Base Gateway name. The environment prefix is added by the platform module."
}

variable "gateway_policy_mode" {
  type        = string
  default     = "LOG_ONLY"
  description = "Use LOG_ONLY until Gateway Cedar policies are validated."

  validation {
    condition     = contains(["LOG_ONLY", "ENFORCE"], var.gateway_policy_mode)
    error_message = "gateway_policy_mode must be LOG_ONLY or ENFORCE."
  }
}

variable "gateway_app_only_ingress_enabled" {
  type        = bool
  default     = false
  description = "Keep false until app-only caller context and Cedar behavior are validated in non-production."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Existing private subnets for AgentCore Runtime VPC mode."
}

variable "runtime_security_group_ids" {
  type        = list(string)
  description = "Existing security groups for Runtime ENIs."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Additional tags merged with standard environment tags."
}

variable "mcp_servers" {
  type = map(object({
    enabled             = bool
    description         = string
    image_uri           = string
    ecr_repository_arns = list(string)
    environment         = optional(map(string), {})
    lanes = map(object({
      enabled                = optional(bool, true)
      description            = optional(string)
      image_uri              = optional(string)
      environment            = optional(map(string), {})
      secret_arns            = optional(list(string), [])
      secret_kms_key_arns    = optional(list(string), [])
      obo_assertion_required = optional(bool, false)
    }))
  }))
  description = "MCP services and identity-specific Runtime lanes passed to the platform module."

  validation {
    condition = alltrue([
      for server in values(var.mcp_servers) : length(server.lanes) > 0
    ])
    error_message = "Every MCP service must define at least one Runtime lane."
  }
}
