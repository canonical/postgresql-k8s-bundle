locals {
  postgresql_revisions = {
    amd64 = 381, # renovate tag
    arm64 = 382
  }
  s3_integrator_revisions = {
    amd64 = 31,
    arm64 = 32
  }
  data_integrator_revisions = {
    amd64 = 41,
    arm64 = 40
  }
  pgbouncer_revisions = {
    amd64 = 269,
    arm64 = 268
  }
  tls_revisions = {
    amd64 = 155,
    arm64 = 201
  }
}
