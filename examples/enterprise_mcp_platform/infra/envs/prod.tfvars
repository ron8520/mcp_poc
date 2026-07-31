environment = "prod"
region      = "ap-southeast-2"

target_account_id = "111122223333"

gateway_policy_mode = "LOG_ONLY"
# Keep false while LOG_ONLY. Set this to true only in the same reviewed change
# that promotes gateway_policy_mode to ENFORCE.
gateway_app_only_ingress_enabled = false

entra_discovery_url    = "https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration"
entra_allowed_audience = ["api://enterprise-mcp-prod"]
entra_allowed_clients = [
  "<claude-code-prod-entra-client-id>",
  "<people-assist-prod-entra-client-id>"
]

private_subnet_ids         = ["subnet-prod-runtime-a", "subnet-prod-runtime-b"]
runtime_security_group_ids = ["sg-prod-runtime-egress"]

mcp_servers = {
  sharepoint = {
    enabled             = true
    description         = "SharePoint MCP server"
    image_uri           = "111122223333.dkr.ecr.ap-southeast-2.amazonaws.com/internal/sharepoint-mcp:prod"
    ecr_repository_arns = ["arn:aws:ecr:ap-southeast-2:111122223333:repository/internal/sharepoint-mcp"]
    environment = {
      GRAPH_DRY_RUN    = "false"
      ENTRA_TENANT_ID  = "<tenant-id>"
      MCP_SERVER_NAME  = "sharepoint-mcp"
      MCP_SERVER_OWNER = "enterprise-mcp-platform"
    }
    lanes = {
      delegated = {
        description            = "SharePoint delegated-permission lane"
        obo_assertion_required = true
        secret_arns = [
          "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:enterprise-mcp/sharepoint-obo-prod"
        ]
        environment = {
          GRAPH_AUTH_MODE             = "obo"
          GRAPH_USER_ASSERTION_HEADER = "x-mcp-user-assertion"
          ENTRA_CLIENT_ID             = "<enterprise-mcp-api-prod-client-id>"
          ENTRA_CLIENT_SECRET_ARN     = "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:enterprise-mcp/sharepoint-obo-prod"
        }
      }
      application = {
        description = "SharePoint application-permission lane"
        secret_arns = [
          "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:enterprise-mcp/sharepoint-application-prod"
        ]
        environment = {
          GRAPH_AUTH_MODE         = "client_credentials"
          ENTRA_CLIENT_ID         = "<sharepoint-application-prod-client-id>"
          ENTRA_CLIENT_SECRET_ARN = "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:enterprise-mcp/sharepoint-application-prod"
        }
      }
    }
  }

  crm = {
    enabled             = false
    description         = "CRM MCP server"
    image_uri           = "111122223333.dkr.ecr.ap-southeast-2.amazonaws.com/internal/crm-mcp:prod"
    ecr_repository_arns = ["arn:aws:ecr:ap-southeast-2:111122223333:repository/internal/crm-mcp"]
    environment = {
      MCP_SERVER_NAME  = "crm-mcp"
      MCP_SERVER_OWNER = "crm-platform"
    }
    lanes = {
      application = {
        description = "CRM application identity lane"
        environment = {
          CRM_AUTH_MODE = "client_credentials"
        }
      }
    }
  }
}
