variable "environment" {
  type        = string
  description = "Environment name."

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
  description = "Application ID URI for the Enterprise MCP API."
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
  description = "Example only. Prefer the approved enterprise secret process for production."
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
  description = "Approved autonomous app catalog keyed by logical name and mapped to SharePoint tools per site."

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
