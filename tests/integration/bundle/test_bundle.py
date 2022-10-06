# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import logging

import pytest
from pytest_operator.plugin import OpsTest

from constants import PGB
from tests.integration.helpers.helpers import (
    deploy_postgres_k8s_bundle,
    get_app_relation_databag,
    get_connecting_relations,
)
from tests.integration.helpers.postgresql_helpers import execute_query_on_unit

logger = logging.getLogger(__name__)

FINOS_WALTZ = "finos-waltz"


@pytest.mark.bundle
@pytest.mark.abort_on_fail
async def test_setup(ops_test: OpsTest):
    """Deploy bundle and set up finos-waltz for testing.
    We're adding an application to ensure that related applications stay online during service
    interruptions.
    """
    await deploy_postgres_k8s_bundle(ops_test, scale_pgbouncer=3, scale_postgres=3)
    await ops_test.model.deploy("finos-waltz-k8s", application_name=FINOS_WALTZ, channel="edge"),


@pytest.mark.bundle
async def test_kill_pg_primary(ops_test: OpsTest):
    """Kill postgres primary, check that all proxy instances switched traffic for a new primary."""


@pytest.mark.bundle
async def test_discover_dbs(ops_test: OpsTest):
    """Check that proxy discovers new members when scaling up postgres charm."""


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
    port = finos_databag.get("port")
    dbname = f"{finos_databag.get('database')}_standby"
    assert None not in [pgpass, user, host, port, dbname], "databag incorrectly populated"

    user_command = "SELECT reset_val FROM pg_settings WHERE name='listen_addresses';"

    pgb_unit = ops_test.model.applications[PGB].units[0]
    # get first ip
    rtn, first_ip, err = await execute_query_on_unit(
        unit_address=pgb_unit.public_address,
        user=user,
        password=pgpass,
        query=user_command,
        database=dbname,
    )
    assert rtn == 0, f"failed to run admin command {user_command}, {err}"

    # get second IP
    rtn, second_ip, err = await execute_query_on_unit(
        unit_address=pgb_unit.public_address,
        user=user,
        password=pgpass,
        query=user_command,
        database=dbname,
    )
    assert rtn == 0, f"failed to run admin command {user_command}, {err}"

    assert first_ip != second_ip
