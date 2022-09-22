#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

def pytest_addoption(parser):
    """Defines pytest parsers."""
    parser.addoption("--bundle", action="store", help="run specific bundle")


def pytest_generate_tests(metafunc):
    """Processes pytest parsers."""
    bundle = metafunc.config.option.bundle
    if 'bundle' in metafunc.fixturenames and bundle is not None:
        metafunc.parametrize("bundle", [bundle])
