# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from charms.pgbouncer_k8s.v0 import pgb
from lightkube import AsyncClient
from lightkube.resources.core_v1 import Pod
from pytest_operator.plugin import OpsTest
from tenacity import Retrying, stop_after_attempt, wait_fixed

from constants import PG, PGB

from ..helpers.helpers import (
    deploy_postgres_k8s_bundle,
    get_app_relation_databag,
    get_backend_relation,
    get_backend_user_pass,
    get_connecting_relations,
    get_leader,
    scale_application,
    wait_for_relation_joined_between,
)
from ..helpers.postgresql_helpers import (
    check_database_creation,
    get_unit_address,
    query_unit_address,
)

logger = logging.getLogger(__name__)

FINOS_WALTZ = "finos-waltz"


@pytest.mark.group(1)
async def test_none():
    pass


@pytest.mark.unstable
@pytest.mark.group(1)
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


@pytest.mark.unstable
@pytest.mark.group(1)
async def test_discover_dbs(ops_test: OpsTest):
    """Check that proxy discovers new members when scaling up postgres charm.

    Since there's only one readonly endpoint, we can only really test this by querying whether the
    endpoint exists or not depending on the number of postgres replicas.
    """
    await scale_application(ops_test, PG, 1)
    pgb_unit = f"{PGB}/0"
    backend_relation = get_backend_relation(ops_test)
    for attempt in Retrying(stop=stop_after_attempt(10), wait=wait_fixed(3), reraise=True):
        with attempt:
            backend_databag = await get_app_relation_databag(
                ops_test, pgb_unit, backend_relation.id
            )
            assert not backend_databag.get("read-only-endpoints", None)

    await ops_test.model.wait_for_idle()
    await scale_application(ops_test, PG, 3)
    for attempt in Retrying(stop=stop_after_attempt(10), wait=wait_fixed(3), reraise=True):
        with attempt:
            updated_backend_databag = await get_app_relation_databag(
                ops_test, pgb_unit, backend_relation.id
            )
            assert updated_backend_databag.get(
                "read-only-endpoints", None
            ), f"read-only-endpoints not populated in updated backend databag - {updated_backend_databag}"


@pytest.mark.unstable
@pytest.mark.group(1)
async def test_kill_pg_primary(ops_test: OpsTest):
    """Kill postgres primary, check that all proxy instances switched traffic for a new primary."""
    # get connection info
    finos_unit_name = f"{FINOS_WALTZ}/0"
    finos_relation = get_connecting_relations(ops_test, PGB, FINOS_WALTZ)[0]
    finos_databag = await get_app_relation_databag(ops_test, f"{FINOS_WALTZ}/0", finos_relation.id)
    connstr = finos_databag.get("master", None)
    assert connstr, f"databag incorrectly populated, \n {finos_databag}"

    pgb_unit = await get_leader(ops_test, PGB)
    pgb_unit_address = await get_unit_address(ops_test, pgb_unit)
    conn_dict = pgb.parse_kv_string_to_dict(connstr)
    conn_dict["host"] = pgb_unit_address
    connstr = pgb.parse_dict_to_kv_string(conn_dict)

    # Get postgres primary through action. Note that postgres primary != postgres leader.
    unit_name = ops_test.model.applications[PG].units[0].name
    action = await ops_test.model.units.get(unit_name).run_action("get-primary")
    action = await action.wait()
    primary = action.results.get("primary", None)
    assert (
        primary
    ), f"failed to get postgresql primary through action, action output: \n{action.results}"
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
    connstr = finos_databag.get("master", None)
    assert connstr, f"databag incorrectly populated: \n{finos_databag}"
    pgb_unit = await get_leader(ops_test, PGB)
    pgb_unit_address = await get_unit_address(ops_test, pgb_unit)
    conn_dict = pgb.parse_kv_string_to_dict(connstr)
    conn_dict["host"] = pgb_unit_address
    connstr = pgb.parse_dict_to_kv_string(conn_dict)
    new_primary_address = await query_unit_address(connstr)
    assert new_primary_address != old_primary_address
