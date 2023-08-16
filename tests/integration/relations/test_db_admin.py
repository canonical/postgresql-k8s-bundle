# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging
import subprocess

from pytest_operator.plugin import OpsTest

from constants import DB_ADMIN_RELATION_NAME, PG, PGB

from ..helpers.helpers import (
    deploy_postgres_k8s_bundle,
    get_backend_relation,
    get_backend_user_pass,
    get_legacy_relation_username,
    wait_for_relation_joined_between,
)
from ..helpers.postgresql_helpers import (
    check_database_creation,
    check_database_users_existence,
    get_unit_address,
)

logger = logging.getLogger(__name__)

FIRST_DISCOURSE_APP_NAME = "discourse-k8s"
SECOND_DISCOURSE_APP_NAME = "discourse-charmers-discourse-k8s"
REDIS_APP_NAME = "redis-k8s"


async def test_create_db_admin_legacy_relation(ops_test: OpsTest):
    # Build, deploy, and relate charms.
    async with ops_test.fast_forward():
        subprocess.check_call(
            f"juju deploy --model {ops_test.model.info.name} postgresql-k8s --channel 14/edge/test --trust -n 2 --series=jammy".split()
        )
        await asyncio.gather(
            deploy_postgres_k8s_bundle(ops_test),
            ops_test.model.deploy(
                FIRST_DISCOURSE_APP_NAME, application_name=FIRST_DISCOURSE_APP_NAME
            ),
            ops_test.model.deploy(REDIS_APP_NAME, application_name=REDIS_APP_NAME),
        )

        # update pgbouncer port because discourse only likes 5432
        await ops_test.model.applications[PGB].set_config({"listen_port": "5432"})

        await ops_test.model.wait_for_idle(
            apps=[PG, PGB, REDIS_APP_NAME], status="active", timeout=600
        )

        backend_relation = get_backend_relation(ops_test)
        pgb_user, pgb_password = await get_backend_user_pass(ops_test, backend_relation)
        await check_database_users_existence(
            ops_test,
            [pgb_user],
            [],
            admin=True,
            pg_user=pgb_user,
            pg_user_password=pgb_password,
        )

        # Discourse waits for relations.
        await ops_test.model.wait_for_idle(
            apps=[FIRST_DISCOURSE_APP_NAME], status="waiting", timeout=1000
        )

        # Add both relations to Discourse (PostgreSQL and Redis) and wait for it to be ready.
        await ops_test.model.add_relation(
            f"{PGB}:{DB_ADMIN_RELATION_NAME}",
            FIRST_DISCOURSE_APP_NAME,
        )
        wait_for_relation_joined_between(ops_test, PGB, FIRST_DISCOURSE_APP_NAME)
        await ops_test.model.add_relation(
            REDIS_APP_NAME,
            FIRST_DISCOURSE_APP_NAME,
        )
        wait_for_relation_joined_between(ops_test, REDIS_APP_NAME, FIRST_DISCOURSE_APP_NAME)

        # Discourse requests extensions through relation, so check that the PostgreSQL charm
        # becomes blocked.
        await ops_test.model.block_until(
            lambda: ops_test.model.units[f"{PGB}/0"].workload_status == "blocked", timeout=60
        )
        assert (
            ops_test.model.units[f"{PGB}/0"].workload_status_message
            == "bad relation request - remote app requested extensions, which are unsupported. Please remove this relation."
        )

        # Destroy the relation to remove the blocked status.
        await ops_test.model.applications[PGB].destroy_relation(
            f"{PGB}:db-admin", FIRST_DISCOURSE_APP_NAME
        )

        # Test the second Discourse charm.

        # Get the Redis instance IP address.
        redis_host = await get_unit_address(ops_test, f"{REDIS_APP_NAME}/0")

        # Deploy Discourse and wait for it to be blocked waiting for database relation.
        await ops_test.model.deploy(
            SECOND_DISCOURSE_APP_NAME,
            application_name=SECOND_DISCOURSE_APP_NAME,
            config={
                "redis_host": redis_host,
                "developer_emails": "user@foo.internal",
                "external_hostname": "foo.internal",
                "smtp_address": "127.0.0.1",
                "smtp_domain": "foo.internal",
            },
        )
        # Discourse becomes blocked waiting for PostgreSQL relation.
        await ops_test.model.wait_for_idle(
            apps=[SECOND_DISCOURSE_APP_NAME], status="blocked", timeout=600
        )

        # Relate PostgreSQL and Discourse, waiting for Discourse to be ready.
        second_discourse_relation = await ops_test.model.add_relation(
            f"{PGB}:{DB_ADMIN_RELATION_NAME}",
            SECOND_DISCOURSE_APP_NAME,
        )
        wait_for_relation_joined_between(ops_test, PGB, SECOND_DISCOURSE_APP_NAME)
        await ops_test.model.wait_for_idle(
            apps=[PG, PGB, SECOND_DISCOURSE_APP_NAME, REDIS_APP_NAME],
            status="active",
            timeout=2000,  # Discourse takes a longer time to become active (a lot of setup).
        )

        # Check for the correct databases and users creation.
        await check_database_creation(
            ops_test, "discourse-charmers-discourse-k8s", user=pgb_user, password=pgb_password
        )

        second_discourse_users = [
            get_legacy_relation_username(ops_test, second_discourse_relation.id)
        ]
        await check_database_creation(
            ops_test, "discourse-charmers-discourse-k8s", user=pgb_user, password=pgb_password
        )
        await check_database_users_existence(
            ops_test,
            second_discourse_users,
            [],
            admin=True,
            pg_user=pgb_user,
            pg_user_password=pgb_password,
        )
