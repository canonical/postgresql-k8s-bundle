module "postgresql" {
  source          = "git::https://github.com/canonical/postgresql-k8s-operator//terraform?ref=main"
  juju_model_name = var.model_name
  channel         = var.postgresql_charm_channel
  revision        = coalesce(var.postgresql_charm_revision, local.postgresql_revisions[var.arch])
  config          = var.postgresql_charm_config
  storage_size    = var.postgresql_storage_size
  units           = var.postgresql_charm_units
  constraints     = "arch=${var.arch}"
}

resource "juju_application" "backups_s3_integrator" {
  name  = "backups-s3-integrator"
  model = var.model_name
  trust = true

  charm {
    name     = "s3-integrator"
    channel  = var.s3_integrator_charm_channel
    revision = coalesce(var.s3_integrator_charm_revision, local.s3_integrator_revisions[var.arch])
  }

  config = {
    endpoint     = var.postgresql_backup_endpoint
    bucket       = var.postgresql_backup_bucket_name
    path         = var.model_name
    region       = var.postgresql_backup_region
    s3-uri-style = "path"
  }

  units = 1

  provisioner "local-exec" {
    # There's currently no way to wait for the charm to be idle, hence the wait-for
    # https://github.com/juju/terraform-provider-juju/issues/202
    command = "juju wait-for application ${self.name} --query='name==\"${self.name}\" && status==\"blocked\"'; $([ $(juju version | cut -d. -f1) = '3' ] && echo 'juju run' || echo 'juju run-action') ${self.name}/leader sync-s3-credentials access-key=${var.postgresql_backup_access_key} secret-key=${var.postgresql_backup_secret_key}"
  }
}

resource "juju_application" "pgbouncer" {
  count = var.data_integrator_enabled ? 1 : 0
  name  = "pgbouncer"
  model = var.model_name
  trust = true

  charm {
    name     = "pgbouncer-k8s"
    channel  = var.pgbouncer_charm_channel
    revision = coalesce(var.pgbouncer_charm_revision, local.pgbouncer_revisions[var.arch])
  }
}

resource "juju_application" "data_integrator" {
  count = var.data_integrator_enabled ? 1 : 0
  name  = "data-integrator"
  model = var.model_name

  charm {
    name     = "data-integrator"
    channel  = var.data_integrator_charm_channel
    revision = coalesce(var.data_integrator_charm_revision, local.data_integrator_revisions[var.arch])
  }

  config = {
    database-name = var.data_integrator_database_name
  }

  units = 1
}

resource "juju_application" "certificates" {
  count = var.enable_tls ? 1 : 0
  name  = "certificates"
  model = var.model_name

  charm {
    name     = var.certificates_charm_name
    channel  = var.certificates_charm_channel
    revision = coalesce(var.certificates_charm_revision, local.tls_revisions[var.arch])
  }

  config = var.certificates_charm_config
  units  = 1
}
