variable "create_model" {
  description = "Model creation convenience flag"
  type        = bool
  default     = false
}

variable "model_name" {
  description = "Juju model name for deployment"
  type        = string
}

variable "arch" {
  description = "Deployment architecture"
  type        = string
  default     = "amd64"

  validation {
    condition     = var.arch == "amd64" || var.arch == "arm64"
    error_message = "Architecture must be either amd64 or arm64"
  }
}

variable "postgresql_charm_channel" {
  description = "Postgresql charm channel"
  type        = string
  default     = "14/stable"
}


variable "postgresql_charm_units" {
  description = "Postgresql charm units number"
  type        = number
  default     = 3
}

variable "postgresql_backup_endpoint" {
  description = "Postgresql backup bucket endpoint"
  type        = string
}

variable "postgresql_backup_bucket_name" {
  description = "Postgresql backup bucket name"
  type        = string
}

variable "postgresql_backup_region" {
  description = "Postgresql backup bucket region"
  type        = string
}

variable "postgresql_backup_access_key" {
  description = "Postgresql backup bucket access key"
  type        = string
}

variable "postgresql_backup_secret_key" {
  description = "Postgresql backup bucket secret key"
  type        = string
  sensitive   = true
}

variable "postgresql_storage_size" {
  description = "Postgresql storage size"
  type        = string
  default     = "10G"
}

variable "postgresql_charm_config" {
  description = "Postgresql charm configuration"
  type        = map(string)
  default     = {}
}

variable "pgbouncer_charm_channel" {
  description = "Postgresql router charm channel"
  type        = string
  default     = "1/stable"
}


variable "data_integrator_enabled" {
  description = "Enable data integrator for external connectivity"
  type        = bool
  default     = false
}

variable "data_integrator_charm_channel" {
  description = "Data integrator charm channel"
  type        = string
  default     = "latest/stable"
}


variable "data_integrator_database_name" {
  description = "Data integrator database name"
  type        = string
  default     = ""
  validation {
    condition     = var.data_integrator_enabled == false || var.data_integrator_database_name != ""
    error_message = "data_integrator_database_name must be set if data_integrator_enabled is true."
  }
}

variable "enable_tls" {
  description = "Enable/enforce TLS through self-signed certificates"
  type        = bool
  default     = true
}

variable "s3_integrator_charm_channel" {
  description = "S3 integrator charm channel"
  type        = string
  default     = "latest/stable"
}

variable "certificates_charm_channel" {
  description = "Certificates Operator charm channel"
  type        = string
  default     = "latest/stable"
}

variable "postgresql_charm_revision" {
  description = "Postgresql charm revision override"
  type        = number
  default     = null
}

variable "pgbouncer_charm_revision" {
  description = "Pgbouncer charm revision override"
  type        = number
  default     = null
}

variable "s3_integrator_charm_revision" {
  description = "s3_integrator charm revision override"
  type        = number
  default     = null
}

variable "certificates_charm_revision" {
  description = "Certificates charm revision override"
  type        = number
  default     = null
}

variable "certificates_charm_name" {
  description = "Certificates charm name"
  type        = string
  default     = "self-signed-certificates"
}

variable "certificates_charm_config" {
  description = "Certificates charm configuration"
  type        = map(string)
  default     = { ca-common-name = "Postgresql CA" }
}

variable "data_integrator_charm_revision" {
  description = "data-integrator charm revision override"
  type        = number
  default     = null
}

