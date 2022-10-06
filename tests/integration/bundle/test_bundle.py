# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from lightkube import AsyncClient
from lightkube.resources.core_v1 import Pod
from pytest_operator.plugin import OpsTest

from constants import PG, PGB
from tests.integration.helpers.helpers import (
    deploy_postgres_k8s_bundle,
    get_app_relation_databag,
    get_backend_relation,
    get_cfg,
    get_connecting_relations,
    scale_application,
    wait_for_relation_joined_between,
)
from tests.integration.helpers.postgresql_helpers import (
    execute_query_on_unit,
    get_unit_address
)

logger = logging.getLogger(__name__)

FINOS_WALTZ = "finos-waltz"


@pytest.mark.bundle
@pytest.mark.abort_on_fail
async def test_setup(ops_test: OpsTest):
    """Deploy bundle and set up finos-waltz for testing.

    We're adding an application to ensure that related applications stay online during service
    interruptions.
    """
    async with ops_test.fast_forward():
        await asyncio.gather(
            deploy_postgres_k8s_bundle(ops_test, scale_pgbouncer=3),
            ops_test.model.deploy("finos-waltz-k8s", application_name=FINOS_WALTZ, channel="edge"),
        )
        await ops_test.model.add_relation(f"{PGB}:db", f"{FINOS_WALTZ}:db")
        wait_for_relation_joined_between(ops_test, PGB, FINOS_WALTZ)
        await ops_test.model.wait_for_idle(
            apps=[PG, PGB, FINOS_WALTZ], status="active", timeout=600
        )


@pytest.mark.bundle
async def test_discover_dbs(ops_test: OpsTest):
    """Check that proxy discovers new members when scaling up postgres charm."""
    pgb_unit = f"{PGB}/0"
    backend_relation = get_backend_relation(ops_test)
    backend_databag = await get_app_relation_databag(ops_test, pgb_unit, backend_relation.id)
    assert backend_databag.get("read-only-endpoints") is None

    await scale_application(ops_test, PG, 3)

    updated_backend_databag = await get_app_relation_databag(
        ops_test, pgb_unit, backend_relation.id
    )
    assert updated_backend_databag.get("read-only-endpoints") is not None


@pytest.mark.bundle
async def test_kill_pg_primary(ops_test: OpsTest):
    """Kill postgres primary, check that all proxy instances switched traffic for a new primary."""
    # get connection info
    backend_relation = get_backend_relation(ops_test)
    backend_databag = await get_app_relation_databag(ops_test, f"{PGB}/0", backend_relation.id)
    pgpass = backend_databag.get("password")
    user = backend_databag.get("username")
    host = backend_databag.get("endpoints")
    dbname = backend_databag.get("database")
    assert None not in [pgpass, user, host, dbname], "databag incorrectly populated"

    # Get postgres primary through action
    unit_name = ops_test.model.applications[PG].units[0].name
    action = await ops_test.model.units.get(unit_name).run_action("get-primary")
    action = await action.wait()
    primary = action.results["primary"]
    old_primary_address = await query_unit_address(ops_test, primary, user, pgpass, dbname)

    async with ops_test.fast_forward():
        # Delete the primary pod.
        model = ops_test.model.info
        client = AsyncClient(namespace=model.name)
        await client.delete(Pod, name=primary.replace("/", "-"))
        logger.info(f"deleted pod {primary}")
        await ops_test.model.wait_for_idle(
            apps=[PG, PGB, FINOS_WALTZ], status="active", timeout=600
        )

    # Get postgres primary through action
    unit_name = ops_test.model.applications[PG].units[0].name
    action = await ops_test.model.units.get(unit_name).run_action("get-primary")
    action = await action.wait()
    primary = action.results["primary"]
    new_primary_address = await query_unit_address(ops_test, primary, user, pgpass, dbname)
    assert new_primary_address != old_primary_address


@pytest.mark.bundle
async def test_read_distribution(ops_test: OpsTest):
    """Check that read instance changed during reconnection to proxy.

    Each new read connection should connect to a new readonly node.
    """
    unit_name = f"{FINOS_WALTZ}/0"
    finos_relation = get_connecting_relations(ops_test, PGB, FINOS_WALTZ)[0]
    finos_databag = await get_app_relation_databag(ops_test, unit_name, finos_relation.id)
    pgpass = finos_databag.get("password")
    user = finos_databag.get("user")
    host = finos_databag.get("host")
    dbname = finos_databag.get("database")
    assert None not in [pgpass, user, host, dbname], "databag incorrectly populated"
    dbname = f"{dbname}_standby"

    pgb_unit = ops_test.model.applications[PGB].units[0]
    first_ip = await query_unit_address(ops_test, pgb_unit.name, user, pgpass, dbname)
    second_ip = await query_unit_address(ops_test, pgb_unit.name, user, pgpass, dbname)
    assert first_ip != second_ip


async def query_unit_address(ops_test, unit_name, username, password, dbname):
    query = "SELECT reset_val FROM pg_settings WHERE name='listen_addresses';"
    rtn, address, err = await execute_query_on_unit(
        unit_address=await get_unit_address(ops_test, unit_name),
        user=username,
        password=password,
        query=query,
        database=dbname,
    )
    assert rtn == 0, f"failed to run admin command {query}, {err}"
    return address
