# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging
from pathlib import Path

import yaml
from pytest_operator.plugin import OpsTest

from constants import PG, PGB, TLS_APP_NAME

from ..helpers.helpers import (
    deploy_postgres_k8s_bundle,
    get_backend_relation,
    get_backend_user_pass,
)
from ..helpers.postgresql_helpers import (
    enable_connections_logging,
    get_postgres_primary,
    run_command_on_unit,
)

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
MATTERMOST = "mattermost-k8s"
TLS = "tls-certificates-operator"
RELATION = "backend-database"


async def test_tls_encrypted_connection_to_postgres(ops_test: OpsTest):
    # Relate PgBouncer to PostgreSQL.
    await asyncio.gather(
        deploy_postgres_k8s_bundle(ops_test),
        ops_test.model.deploy(MATTERMOST, application_name=MATTERMOST),
    )

    # Enable additional logs on the PostgreSQL instance to check TLS
    # being used in a later step.
    await enable_connections_logging(ops_test, f"{PG}/0")

    # Relate finos to PgBouncer to open a connection between PgBouncer and PostgreSQL.
    await ops_test.model.add_relation(f"{PGB}:db", f"{MATTERMOST}:db")
    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(
            apps=[PG, PGB, MATTERMOST, TLS_APP_NAME], status="active", timeout=600
        )

    # Check the logs to ensure TLS is being used by PgBouncer.
    postgresql_primary_unit = await get_postgres_primary(ops_test)
    logs = await run_command_on_unit(
        ops_test, postgresql_primary_unit, "/charm/bin/pebble logs -n=all"
    )
    username, _ = await get_backend_user_pass(ops_test, get_backend_relation(ops_test))
    assert (
        f"connection authorized: user={username} database=mattermost SSL enabled" in logs
    ), "TLS is not being used on connections to PostgreSQL"
