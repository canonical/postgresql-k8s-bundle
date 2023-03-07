# Canonical Distribution of PostgreSQL + PgBouncer

[![Update](https://github.com/canonical/postgresql-k8s-bundle/actions/workflows/on_bundle_update_available.yaml/badge.svg?branch=main)](https://github.com/canonical/postgresql-k8s-bundle/actions/workflows/on_bundle_update_available.yaml?query=branch%3Amain)
[![Tests](https://github.com/canonical/postgresql-k8s-bundle/actions/workflows/ci.yaml/badge.svg?branch=main&event=schedule)](https://github.com/canonical/postgresql-k8s-bundle/actions/workflows/ci.yaml?query=branch%3Amain+event%3Aschedule)
[![Release](https://github.com/canonical/postgresql-k8s-bundle/actions/workflows/release.yaml/badge.svg?branch=main&event=push)](https://github.com/canonical/postgresql-k8s-bundle/actions/workflows/release.yaml?query=branch%3Amain+event%3Apush)
[![Charmhub](https://charmhub.io/postgresql-k8s-bundle/badge.svg)](https://charmhub.io/postgresql-k8s-bundle)

Welcome to the Canonical Distribution of PostgreSQL + PgBouncer.

The objective of this page is to provide directions to get up and running with Canonical PostgreSQL charms.

A repo containing infrastructure, configs, and tests for the [PostgreSQL K8s Juju bundle](https://charmhub.io/postgresql-k8s-bundle?channel=edge), containing:
- two [PostgreSQL](https://charmhub.io/postgresql-k8s?channel=edge) nodes (a primary, and a secondary)
- a [PgBouncer](https://charmhub.io/pgbouncer-k8s?channel=edge) proxy
- and a [TLS charm](https://charmhub.io/tls-certificates-operator?channel=edge) to broker certificates between PgBouncer and postgres

These charms are all on `edge` branches, so this bundle should also be considered an edge product until Canonical is publishing to `stable`.

## Installation

[Multipass](https://multipass.run/) is a quick and easy way to launch virtual machines running Ubuntu. It uses "[cloud-init](https://cloud-init.io/)" standard to install and configure all the necessary parts automatically.

Let's install Multipass from [Snap](https://snapcraft.io/multipass) and launch a new VM using "[charm-dev](https://github.com/canonical/multipass-blueprints/blob/main/v1/charm-dev.yaml)" cloud-init config:
```shell
sudo snap install multipass && \
multipass launch --cpus 4 --memory 8G --disk 30G charm-dev # tune CPU/RAM/HDD accordingly to your needs
```
*Note: all 'multipass launch' params are [described here](https://multipass.run/docs/launch-command)*.

Multipass [list of commands](https://multipass.run/docs/multipass-cli-commands) is short and self-explanatory, e.g. show all running VMs:
```shell
multipass list
```

As soon as new VM started, enter inside using:
```shell
multipass shell charm-dev
```
*Note: if at any point you'd like to leave Multipass VM, enter `Ctrl+d` or type `exit`*.

All the parts have been pre-installed inside VM already, like Microk8s and Juju (the file '/var/log/cloud-init.log' contains all low-level installation details). Juju uses models to isolate applications, let's add a new model for our K8s application:
```shell
juju add-model my-postgresql-k8s
```

Finally deploy the bundle:
```shell
juju deploy postgresql-k8s-bundle --trust # --channel edge # Choose a channel: edge, candidate, stable!
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
juju destroy-model my-postgresql-k8s -y --destroy-storage --force
```

To get rid of multipass VM, run:
```shell
multipass delete charm-dev --purge
```

## Bundle Components

- [![PostgreSQL](https://charmhub.io/postgresql-k8s/badge.svg?channel=edge)](https://charmhub.io/postgresql-k8s?channel=edge)  - K8s charm to deploy PostgreSQL.
- [![PgBouncer](https://charmhub.io/pgbouncer-k8s/badge.svg?channel=edge)](https://charmhub.io/pgbouncer-k8s?channel=edge) - K8s charm to deploy PgBouncer.
- [![TLS Certificates](https://charmhub.io/tls-certificates-operator/badge.svg)](https://charmhub.io/tls-certificates-operator) - TLS operator.

Note: The TLS settings in bundles use self-signed-certificates which are not recommended for production clusters, the tls-certificates-operator charm offers a variety of configurations, read more on the TLS charm [here](https://charmhub.io/tls-certificates-operator).

## Troubleshooting

If you have any problems or questions, please feel free to reach out. We'd be more than glad to help!

The fastest way to get our attention is to create a [discourse post](https://discourse.charmhub.io/).
