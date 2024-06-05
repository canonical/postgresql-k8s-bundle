# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from pytest_operator.plugin import OpsTest
from tenacity import RetryError, Retrying, stop_after_delay, wait_fixed

from constants import BACKEND_RELATION_NAME, PG, PGB

from ..helpers.helpers import (
    deploy_postgres_k8s_bundle,
    get_app_relation_databag,
    get_backend_relation,
    get_backend_user_pass,
    get_cfg,
    get_userlist,
    scale_application,
    wait_for_relation_joined_between,
    wait_for_relation_removed_between,
)
from ..helpers.postgresql_helpers import check_database_users_existence

logger = logging.getLogger(__name__)


@pytest.mark.group(1)
async def test_none():
    pass


@pytest.mark.unstable
@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_deploy_bundle(ops_test: OpsTest):
    """Test that the pgbouncer and postgres charms can relate to one another."""
    # Build, deploy, and relate charms.
    async with ops_test.fast_forward():
        await deploy_postgres_k8s_bundle(ops_test)
        cfg = await get_cfg(ops_test, f"{PGB}/0")
        logging.info(cfg.render())
        backend_relation = get_backend_relation(ops_test)
        pgb_user, pgb_password = await get_backend_user_pass(ops_test, backend_relation)
        assert cfg["pgbouncer"]["auth_query"]

        await check_database_users_existence(ops_test, [pgb_user], [], pgb_user, pgb_password)

        # Remove relation but keep pg application because we're going to need it for future tests.
        await ops_test.model.applications[PG].remove_relation(
            f"{PGB}:{BACKEND_RELATION_NAME}", f"{PG}:database"
        )
        pgb_unit = ops_test.model.applications[PGB].units[0]
        logging.info(await get_app_relation_databag(ops_test, pgb_unit.name, backend_relation.id))
        wait_for_relation_removed_between(ops_test, PG, PGB)
        await asyncio.gather(
            ops_test.model.wait_for_idle(apps=[PG], status="active", timeout=600),
            ops_test.model.wait_for_idle(apps=[PGB], status="blocked", timeout=600),
        )

        # Wait for pgbouncer charm to update its config files.
        try:
            for attempt in Retrying(stop=stop_after_delay(3 * 60), wait=wait_fixed(3)):
                with attempt:
                    cfg = await get_cfg(ops_test, f"{PGB}/0")
                    if "auth_query" not in cfg["pgbouncer"].keys():
                        break
        except RetryError:
            assert False, "pgbouncer config files failed to update in 3 minutes"

        cfg = await get_cfg(ops_test, f"{PGB}/0")
        logging.info(cfg.render())


@pytest.mark.unstable
@pytest.mark.group(1)
async def test_pgbouncer_stable_when_deleting_postgres(ops_test: OpsTest):
    async with ops_test.fast_forward():
        relation = await ops_test.model.add_relation(
            f"{PGB}:{BACKEND_RELATION_NAME}", f"{PG}:database"
        )
        wait_for_relation_joined_between(ops_test, PG, PGB)
        await asyncio.gather(
            ops_test.model.wait_for_idle(
                apps=[PGB], status="active", timeout=600, wait_for_exact_units=1
            ),
            ops_test.model.wait_for_idle(
                apps=[PG], status="active", timeout=600, wait_for_exact_units=2
            ),
        )

        await scale_application(ops_test, PGB, 3)
        await asyncio.gather(
            ops_test.model.wait_for_idle(
                apps=[PGB], status="active", timeout=600, wait_for_exact_units=3
            ),
            ops_test.model.wait_for_idle(
                apps=[PG], status="active", timeout=600, wait_for_exact_units=2
            ),
        )

        username = f"relation_id_{relation.id}"
        leader_cfg = await get_cfg(ops_test, f"{PGB}/0")
        leader_userlist = await get_userlist(ops_test, f"{PGB}/0")

        assert username in leader_userlist

        for unit_id in [1, 2]:
            unit_name = f"{PGB}/{unit_id}"
            cfg = await get_cfg(ops_test, unit_name)
            userlist = await get_userlist(ops_test, unit_name)
            assert username in userlist

            assert cfg == leader_cfg
            assert userlist == leader_userlist

        # TODO test deleting leader

        await scale_application(ops_test, PGB, 1)
        await asyncio.gather(
            ops_test.model.wait_for_idle(
                apps=[PGB], status="active", timeout=600, wait_for_exact_units=1
            ),
            ops_test.model.wait_for_idle(
                apps=[PG], status="active", timeout=600, wait_for_exact_units=2
            ),
        )
