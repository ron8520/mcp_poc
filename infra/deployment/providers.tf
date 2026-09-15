terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.55.0"
    }

    azuread = {
      source  = "hashicorp/azuread"
      version = ">= 3.0.0"
    }

    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7.0"
    }

    random = {
      source  = "hashicorp/random"
      version = ">= 3.6.0"
    }
  }
}

provider "aws" {
  region = var.region
}

provider "azuread" {
  tenant_id = var.tenant_id
}
