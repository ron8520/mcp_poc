environment             = "prod"
tenant_id               = "<tenant-id>"
enterprise_mcp_audience = "api://enterprise-mcp-prod"

sharepoint_readers_group_object_id    = "<prod-sharepoint-readers-group-object-id>"
sharepoint_publishers_group_object_id = "<prod-sharepoint-publishers-group-object-id>"
crm_admins_group_object_id            = "<prod-crm-admins-group-object-id>"

enable_device_code_flow             = false
enable_conditional_access_example   = true
conditional_access_state            = "enabledForReportingButNotEnforced"
internal_network_cidrs              = ["198.51.100.0/24"]
break_glass_user_object_ids         = ["<break-glass-user-object-id>"]
create_people_assist_client_secret  = false
people_assist_secret_display_name   = "people-assist-mcp-client-secret-prod"
