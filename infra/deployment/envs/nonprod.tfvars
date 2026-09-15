environment             = "nonprod"
tenant_id               = "<tenant-id>"
enterprise_mcp_audience = "api://enterprise-mcp-nonprod"

sharepoint_readers_group_object_id    = "<nonprod-sharepoint-readers-group-object-id>"
sharepoint_publishers_group_object_id = "<nonprod-sharepoint-publishers-group-object-id>"
crm_admins_group_object_id            = "<nonprod-crm-admins-group-object-id>"

enable_device_code_flow            = false
enable_conditional_access_example  = true
conditional_access_state           = "enabledForReportingButNotEnforced"
internal_network_cidrs             = ["203.0.113.0/24"]
break_glass_user_object_ids        = ["<break-glass-user-object-id>"]
create_people_assist_client_secret = false
people_assist_secret_display_name  = "people-assist-mcp-client-secret-nonprod"

region = "ap-southeast-2"

target_account_id = "111122223333"

gateway_policy_mode              = "LOG_ONLY"
gateway_app_only_ingress_enabled = false

private_subnet_ids         = ["subnet-nonprod-runtime-a", "subnet-nonprod-runtime-b"]
runtime_security_group_ids = ["sg-nonprod-runtime-egress"]

# Caller IDs, Gateway audience, and discovery URL are composed from module outputs.
app_only_apps              = {}
app_only_provider_bindings = {}

mcp_servers = {
  sharepoint = {
    enabled             = true
    description         = "SharePoint MCP server"
    image_uri           = "111122223333.dkr.ecr.ap-southeast-2.amazonaws.com/internal/sharepoint-mcp:nonprod"
    ecr_repository_arns = ["arn:aws:ecr:ap-southeast-2:111122223333:repository/internal/sharepoint-mcp"]
    environment = {
      GRAPH_DRY_RUN    = "false"
      MCP_SERVER_NAME  = "sharepoint-mcp"
      MCP_SERVER_OWNER = "enterprise-mcp-platform"
    }
    lanes = {
      delegated = {
        description            = "SharePoint delegated-permission lane"
        obo_assertion_required = true
        secret_arns = [
          "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:enterprise-mcp/sharepoint-obo-nonprod"
        ]
        environment = {
          GRAPH_AUTH_MODE             = "obo"
          GRAPH_USER_ASSERTION_HEADER = "x-mcp-user-assertion"
          ENTRA_CLIENT_SECRET_ARN     = "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:enterprise-mcp/sharepoint-obo-nonprod"
        }
      }
      application = {
        description = "SharePoint application-permission lane (fixed MSAL client; credential method pending)"
        secret_arns = [
          "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:enterprise-mcp/sharepoint-application-nonprod"
        ]
        environment = {
          GRAPH_AUTH_MODE         = "client_credentials"
          ENTRA_CLIENT_ID         = "<sharepoint-application-nonprod-client-id>"
          ENTRA_CLIENT_SECRET_ARN = "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:enterprise-mcp/sharepoint-application-nonprod"
        }
      }
    }
  }

}
