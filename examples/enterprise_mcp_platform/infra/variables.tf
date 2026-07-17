variable "region" {
  type    = string
  default = "us-west-2"
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

variable "client_vpc_id" {
  type        = string
  description = "VPC used by Lambda and private developer access."
}

variable "gateway_endpoint_subnet_ids" {
  type        = list(string)
  description = "Subnets for the AgentCore Gateway interface endpoint."
}

variable "gateway_endpoint_security_group_ids" {
  type        = list(string)
  description = "Security groups for the Gateway interface endpoint."
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
  }))
  description = "MCP server runtimes to deploy and register as Gateway targets."
}
