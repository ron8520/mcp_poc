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
  description = "AWS account that owns the AgentCore deployment. Supplied by the central platform/TFE configuration."

  validation {
    condition     = can(regex("^[0-9]{12}$", var.target_account_id))
    error_message = "target_account_id must be a 12-digit AWS account ID."
  }
}

variable "environment" {
  type        = string
  description = "Environment name controlled by the selected tfvars file."

  validation {
    condition     = contains(["nonprod", "prod"], var.environment)
    error_message = "environment must be nonprod or prod."
  }
}

variable "gateway_name" {
  type        = string
  default     = "enterprise-mcp-gateway"
  description = "Base Gateway name. The environment prefix is added by this Terraform root."
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
  description = "Remove the transitional delegated-scope gate only after Cedar is ENFORCE."
}

variable "entra_discovery_url" {
  type        = string
  description = "Entra OIDC discovery URL ending with .well-known/openid-configuration."
}

variable "entra_allowed_audience" {
  type        = list(string)
  default     = ["api://enterprise-mcp-nonprod"]
  description = "Allowed Entra audience values for Gateway CUSTOM_JWT validation."
}

variable "entra_allowed_clients" {
  type        = list(string)
  default     = []
  description = "Entra application client IDs allowed to call the Gateway."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnets for AgentCore Runtime VPC mode."
}

variable "runtime_security_group_ids" {
  type        = list(string)
  description = "Security groups for Runtime ENIs."
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
      environment            = optional(map(string), {})
      secret_arns            = optional(list(string), [])
      secret_kms_key_arns    = optional(list(string), [])
      obo_assertion_required = optional(bool, false)
    }))
  }))
  description = "MCP services and the identity-specific Runtime lanes built from each service image."

  validation {
    condition = alltrue([
      for server in values(var.mcp_servers) : length(server.lanes) > 0
    ])
    error_message = "Every MCP service must define at least one Runtime lane."
  }
}
