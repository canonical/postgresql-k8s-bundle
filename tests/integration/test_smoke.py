# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import time

import pytest
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

TEST_APP_NAME = "postgresql-test-app"
ACTIVE_APPS = [
    "pgbouncer-k8s",
    "postgresql-k8s",
    TEST_APP_NAME,
    "self-signed-certificates",
    "sysbench",
]
BLOCKED_APPS = [
    "data-integrator",
    "grafana-agent-k8s",
    "s3-integrator",
]


@pytest.mark.group(1)
@pytest.mark.abort_on_fail
async def test_setup(ops_test: OpsTest):
    async with ops_test.fast_forward():
        await ops_test.model.deploy("./releases/latest/postgresql-k8s-bundle.yaml", trust=True)
        await ops_test.model.applications["postgresql-k8s"].set_config({"profile": "testing"})
        await ops_test.model.wait_for_idle(
            apps=ACTIVE_APPS,
            status="active",
            timeout=3000,
        )
        await ops_test.model.wait_for_idle(
            apps=BLOCKED_APPS,
            status="blocked",
            timeout=100,
        )

    logger.info("Test continuous writes")
    await (
        await ops_test.model.applications[TEST_APP_NAME]
        .units[0]
        .run_action("start-continuous-writes")
    ).wait()

    time.sleep(10)

    results = await (
        await ops_test.model.applications[TEST_APP_NAME]
        .units[0]
        .run_action("stop-continuous-writes")
    ).wait()

    writes = int(results.results["writes"])
    assert writes > 0
    client_relation = None
    for rel in ops_test.model.applications[TEST_APP_NAME].relations:
        for endpoint in rel.endpoints:
            if endpoint.name == "first-database" and endpoint.application_name == TEST_APP_NAME:
                client_relation = rel
                break
        if client_relation:
            break

    params = {
        "dbname": f"{TEST_APP_NAME.replace('-', '_')}_first_database",
        "query": "SELECT COUNT(number), MAX(number) FROM continuous_writes;",
        "relation-id": client_relation.id,
        "relation-name": "first-database",
        "readonly": False,
    }
    results = await (
        await ops_test.model.applications[TEST_APP_NAME].units[0].run_action("run-sql", **params)
    ).wait()
    count, maximum = results.results["results"].strip("[]").split(", ")
    count = int(count)
    maximum = int(maximum)

    assert writes == count == maximum
