variable "aws_region" {
  default = "ap-south-1"
}

variable "cluster_name" {
  default = "taskboard-eks"
}

variable "cluster_version" {
  default = "1.36"
}

variable "environment" {
  default = "dev"
}

variable "github_repo" {
  description = "owner/repo allowed to deploy via GitHub Actions OIDC"
  default     = "Frosty-90@206500401/devops-project@1421742018"
}
