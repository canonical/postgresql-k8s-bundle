# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import itertools
import logging

import psycopg2
import pytest
from charms.pgbouncer_k8s.v0 import pgb
from lightkube import AsyncClient
from lightkube.resources.core_v1 import Pod
from pytest_operator.plugin import OpsTest

from constants import PG, PGB
from tests.integration.helpers.helpers import (
    deploy_postgres_k8s_bundle,
    get_app_relation_databag,
    get_backend_relation,
    get_backend_user_pass,
    get_connecting_relations,
    scale_application,
    wait_for_relation_joined_between,
)
from tests.integration.helpers.postgresql_helpers import (
    check_database_creation,
    get_unit_address,
    run_query,
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
            deploy_postgres_k8s_bundle(ops_test),
            ops_test.model.deploy("finos-waltz-k8s", application_name=FINOS_WALTZ, channel="edge"),
        )
        await ops_test.model.wait_for_idle(apps=[PG, PGB, FINOS_WALTZ], timeout=600)
        await ops_test.model.add_relation(f"{PGB}:db", f"{FINOS_WALTZ}:db")
        wait_for_relation_joined_between(ops_test, PGB, FINOS_WALTZ)
        await ops_test.model.wait_for_idle(
            apps=[PG, PGB, FINOS_WALTZ], status="active", timeout=600
        )
        backend_relation = get_backend_relation(ops_test)
        pgb_user, pgb_password = await get_backend_user_pass(ops_test, backend_relation)
        await check_database_creation(ops_test, "waltz", pgb_user, pgb_password)


@pytest.mark.bundle
async def test_discover_dbs(ops_test: OpsTest):
    """Check that proxy discovers new members when scaling up postgres charm.

    Since there's only one readonly endpoint, we can only really test this by querying whether the
    endpoint exists or not depending on the number of postgres replicas.
    """
    pgb_unit = f"{PGB}/0"
    backend_relation = get_backend_relation(ops_test)
    backend_databag = await get_app_relation_databag(ops_test, pgb_unit, backend_relation.id)
    assert backend_databag.get("read-only-endpoints") is None

    await asyncio.gather(
        scale_application(ops_test, PG, 3),
        scale_application(ops_test, PGB, 3),
    )

    updated_backend_databag = await get_app_relation_databag(
        ops_test, pgb_unit, backend_relation.id
    )
    assert updated_backend_databag.get("read-only-endpoints") is not None


@pytest.mark.bundle
async def test_kill_pg_primary(ops_test: OpsTest):
    """Kill postgres primary, check that all proxy instances switched traffic for a new primary."""
    # get connection info
    finos_unit_name = f"{FINOS_WALTZ}/0"
    finos_relation = get_connecting_relations(ops_test, PGB, FINOS_WALTZ)[0]
    finos_databag = await get_app_relation_databag(ops_test, finos_unit_name, finos_relation.id)
    connstr = finos_databag.get("standbys")
    assert connstr is not None, "databag incorrectly populated"

    # Get postgres primary through action
    unit_name = ops_test.model.applications[PG].units[0].name
    action = await ops_test.model.units.get(unit_name).run_action("get-primary")
    action = await action.wait()
    primary = action.results["primary"]
    old_primary_address = await query_unit_address(connstr)

    async with ops_test.fast_forward():
        # Delete the primary pod.
        model = ops_test.model.info
        client = AsyncClient(namespace=model.name)
        await client.delete(Pod, name=primary.replace("/", "-"))
        logger.info(f"deleted pod {primary}")
        await ops_test.model.wait_for_idle(
            apps=[PG, PGB, FINOS_WALTZ], status="active", timeout=600
        )

    # get new address
    finos_databag = await get_app_relation_databag(ops_test, finos_unit_name, finos_relation.id)
    connstr = finos_databag.get("standbys")
    assert connstr is not None, "databag incorrectly populated"
    new_primary_address = await query_unit_address(connstr)
    assert new_primary_address != old_primary_address


@pytest.mark.bundle
async def test_read_distribution(ops_test: OpsTest):
    """Check that read instance changed during reconnection to proxy.

    Each new read connection should connect to a new readonly node.
    """
    finos_relation = get_connecting_relations(ops_test, PGB, FINOS_WALTZ)[0]
    finos_databag = await get_app_relation_databag(ops_test, f"{FINOS_WALTZ}/0", finos_relation.id)
    connstr = finos_databag.get("standbys")
    assert connstr is not None, f"databag incorrectly populated: \n{finos_databag}"

    pgb_unit = f"{PGB}/0"
    pgb_unit_address = await get_unit_address(ops_test, pgb_unit)
    conn_dict = pgb.parse_kv_string_to_dict(connstr)
    conn_dict["host"] = pgb_unit_address
    connstr = pgb.parse_dict_to_kv_string(conn_dict)

    first_ip = await query_unit_address(connstr)
    second_ip = await query_unit_address(connstr)
    assert first_ip != second_ip


async def query_unit_address(connstr):
    address_query = "SELECT inet_server_addr();"
    connstr += " connect_timeout=10"
    return await run_query(connstr, address_query)


async def query_unit_name(connstr):
    """Returns the unit name if this function is not a leader, or nothing if it is."""
    primary_query = "SELECT reset_val FROM pg_settings WHERE name='primary_slot_name';"
    connstr += " connect_timeout=10"
    return await run_query(connstr, primary_query)
