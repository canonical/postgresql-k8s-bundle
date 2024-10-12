resource "juju_integration" "s3_integrator_postgresql" {
  model = var.model_name

  application {
    name = juju_application.backups_s3_integrator.name
  }

  application {
    name     = module.postgresql.application_name
    endpoint = module.postgresql.requires.s3_parameters
  }
}

resource "juju_integration" "postgresql_self_signed_certificates" {
  count = var.enable_tls ? 1 : 0
  model = var.model_name

  application {
    name     = module.postgresql.application_name
    endpoint = module.postgresql.requires.certificates
  }
  application {
    name = juju_application.self_signed_certificates[0].name
  }
}

resource "juju_integration" "postgresql_pgbouncer" {
  count = var.data_integrator_enabled ? 1 : 0
  model = var.model_name

  application {
    name     = module.postgresql.application_name
    endpoint = module.postgresql.provides.database
  }
  application {
    name     = juju_application.pgbouncer[0].name
    endpoint = "backend-database"
  }
}

resource "juju_integration" "pgbouncer_data_integrator" {
  count = var.data_integrator_enabled ? 1 : 0
  model = var.model_name

  application {
    name     = juju_application.pgbouncer[0].name
    endpoint = "database"
  }
  application {
    name     = juju_application.data_integrator[0].name
    endpoint = "postgresql"
  }
}
