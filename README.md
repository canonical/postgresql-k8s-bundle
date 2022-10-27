# postgresql-k8s-bundle

A repo containing Juju bundles for PostgreSQL and PGBouncer on k8s.

Although version numbers are detailed in the bundle.yaml, they're not used by charmhub. Charmhub only makes the most recent versions on a branch available to download, so this charm will only use the most recent release of each charm.

The `tls-certificates-operator` currently uses self-signed certificates, but if security is a concern, replace these certificates as described in the [TLS operator docs](https://charmhub.io/tls-certificates-operator).

## Operators included in this bundle

- [postgresql-k8s](https://charmhub.io/postgresql-k8s)
- [pgbouncer-k8s](https://charmhub.io/pgbouncer-k8s)
- [tls-certificates-operator](https://charmhub.io/tls-certificates-operator)
