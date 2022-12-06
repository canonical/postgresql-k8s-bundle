# Canonical Distribution of PostgreSQL + PgBouncer

[![None](https://charmhub.io/postgresql-k8s-bundle/badge.svg)](https://charmhub.io/postgresql-k8s-bundle)

Welcome to the Canonical Distribution of PostgreSQL + PgBouncer.

The objective of this page is to provide directions to get up and running with Canonical PostgreSQL charms.

A repo containing infrastructure, configs, and tests for the [PostgreSQL K8s Juju bundle](https://charmhub.io/postgresql-k8s-bundle?channel=edge), containing: 
- two [PostgreSQL](https://charmhub.io/postgresql-k8s?channel=edge) nodes (a primary, and a secondary)
- a [PgBouncer](https://charmhub.io/pgbouncer-k8s?channel=edge) proxy
- and a [TLS charm](https://charmhub.io/tls-certificates-operator?channel=edge) to broker certificates between PgBouncer and postgres

These charms are all on `edge` branches, so this bundle should also be considered an edge product until Canonical is publishing to `stable`.

## Installation

To get started, please take Ubuntu 22.04 LTS and install the
necessary components. Juju, MicroK8s (with add-ons as listed below):

```shell
sudo snap refresh
sudo snap install juju --classic
sudo snap install microk8s --classic
sudo snap install jhack # nice to have it nearby
sudo microk8s enable dns storage ha-cluster ingress hostpath-storage
sudo usermod -a -G microk8s $(whoami) && newgrp microk8s
```

To follow, please bootstrap the juju controller with microk8s using:

```shell
juju bootstrap microk8s my-microk8s
```

Finally add a juju model and deploy the bundle:

```shell
juju add-model my-postgresql-k8s
juju deploy postgresql-k8s-bundle --trust # --channel edge # Choose a channel!
juju status # you are ready!
juju status --watch 1s --storage --relations # watch all the information
```

Feel free to increase DEBUG verbosity for troubleshooting:

```shell
juju model-config 'logging-config=<root>=INFO;unit=DEBUG'
juju debug-log # show all logs together
juju debug-log --include postgresql-k8s/0 --replay --tail # to check specific unit
```

To destroy the complete Juju model with all newly deployed charms and data:

```shell
juju destroy-model my-postgresql-k8s -y --destroy-storage --force && \
juju add-model my-postgresql-k8s && juju status
```

## Bundle Components

[![PostgreSQL](https://charmhub.io/postgresql-k8s/badge.svg?channel=edge)](https://charmhub.io/postgresql-k8s?channel=edge) [![PgBouncer](https://charmhub.io/pgbouncer-k8s/badge.svg?channel=edge)](https://charmhub.io/pgbouncer-k8s?channel=edge) [![TLS Certificates](https://charmhub.io/tls-certificates-operator/badge.svg?channel=edge)](https://charmhub.io/tls-certificates-operator?channel=edge)

- [postgresql-k8s](https://charmhub.io/postgresql-k8s?channel=edge): a K8s charm to deploy PostgreSQL.
- [pgbouncer-k8s](https://charmhub.io/pgbouncer-k8s?channel=edge): a K8s charm to deploy PgBouncer.
- [tls-certificates-operator](https://charmhub.io/tls-certificates-operator?channel=edge): TLS operator.

Note: The TLS settings in bundles use self-signed-certificates which are not recommended for production clusters, the tls-certificates-operator charm offers a variety of configurations, read more on the TLS charm [here](https://charmhub.io/tls-certificates-operator).

## Troubleshooting

If you have any problems or questions, please feel free to reach out. We'd be more than glad to help!

The fastest way to get our attention is to create a [discourse post](https://discourse.charmhub.io/).