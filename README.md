# postgresql-k8s-bundle

A repo containing infrastructure, YAML, and tests for the [postgres k8s juju bundle](https://charmhub.io/postgresql-k8s-bundle), containing: 
- two [postgres](https://charmhub.io/postgresql-k8s?channel=edge) nodes (a primary, and a secondary), 
- a [pgbouncer](https://charmhub.io/pgbouncer-k8s?channel=edge) proxy, 
- and a [TLS charm](https://charmhub.io/tls-certificates-operator?channel=edge) to broker certificates between pgbouncer and postgres. 

These charms are all on edge branches, so this bundle should also be considered an edge product until we're publishing to `stable`.

Although version numbers are detailed in the bundle.yaml, they're not used by charmhub. Charmhub only makes the most recent versions on a branch available to download, so this charm will only use the most recent release of each charm.

The `tls-certificates-operator` currently uses self-signed certificates, but if security is a concern, replace these certificates as described in the [TLS operator docs](https://charmhub.io/tls-certificates-operator).

## Deployment
```bash
juju deploy postgresql-k8s-bundle --channel=edge --trust
```

## Operators included in this bundle

- [postgresql-k8s](https://charmhub.io/postgresql-k8s)
- [pgbouncer-k8s](https://charmhub.io/pgbouncer-k8s)
- [tls-certificates-operator](https://charmhub.io/tls-certificates-operator)
