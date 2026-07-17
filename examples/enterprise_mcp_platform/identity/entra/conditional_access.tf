resource "azuread_named_location" "internal_networks" {
  count        = var.enable_conditional_access_example ? 1 : 0
  display_name = "enterprise-mcp-internal-networks-${var.environment}"

  ip {
    trusted   = true
    ip_ranges = var.internal_network_cidrs
  }
}

resource "azuread_conditional_access_policy" "enterprise_mcp_internal_network" {
  count        = var.enable_conditional_access_example ? 1 : 0
  display_name = "enterprise-mcp-${var.environment}-block-outside-internal-network"
  state        = var.conditional_access_state

  conditions {
    client_app_types = ["all"]

    applications {
      included_applications = [
        azuread_application.enterprise_mcp_api.client_id
      ]
    }

    users {
      included_users = ["All"]
      excluded_users = var.break_glass_user_object_ids
    }

    locations {
      included_locations = ["All"]
      excluded_locations = [
        azuread_named_location.internal_networks[0].id
      ]
    }
  }

  grant_controls {
    operator          = "OR"
    built_in_controls = ["block"]
  }
}
