# Inactive handoff example. `owner` is an Entra owner object GUID. Keep
# app_only_provider_bindings empty until each external AgentCore OAuth2 provider
# is registered and its ARN is approved.
app_only_apps = {
  finance_reader = {
    owner = "<owner-object-id>"
    grants = {
      "<sharepoint-site-id>" = [
        "sharepoint_list_site_content",
        "sharepoint_get_file_text",
      ]
    }
  }

  finance_publisher = {
    owner = "<owner-object-id>"
    grants = {
      "<sharepoint-site-id>" = [
        "sharepoint_list_site_content",
        "sharepoint_upload_file",
      ]
    }
  }
}

app_only_provider_bindings = {}
