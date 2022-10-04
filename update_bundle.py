#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import requests
import yaml
import sys

from pathlib import Path

logger = logging.getLogger(__name__)


def fetch_revision(charm, charm_channel):
    """Returns revision number for charm in channel."""
    charm_info = requests.get(
        f"https://api.snapcraft.io/v2/charms/info/{charm}?fields=channel-map"
    ).json()
    for channel in charm_info["channel-map"]:
        if channel["channel"]["risk"] == charm_channel:
            return channel["revision"]["revision"]
    raise ValueError("Revision not found.")

def update_bundle(bundle_path):
    """Updates a bundle's revision number."""
    bundle_data = yaml.safe_load(Path(bundle_path).read_text())
    for app in bundle_data["applications"]:
        bundle_data["applications"][app]["revision"] = fetch_revision(
            app, bundle_data["applications"][app]["channel"]
        )

    with open(bundle_path, 'w') as bundle:
        yaml.dump(bundle_data, bundle)
        bundle.close()


if __name__ == '__main__':
    update_bundle(sys.argv[1])
